"""Recovery command to resume pending generations."""

import logging
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ..api.client import FluxAPIClient
from ..utils.queue import GenerationQueue
from ..utils.storage import StorageManager
from ..utils.progress import ProgressTracker

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--list", "-l",
    is_flag=True,
    help="List all pending generations"
)
@click.option(
    "--resume", "-r",
    help="Resume a specific generation by ID"
)
@click.option(
    "--resume-all", "-a",
    is_flag=True,
    help="Resume all pending generations"
)
@click.option(
    "--clean", "-c",
    is_flag=True,
    help="Clean up all completed entries"
)
@click.option(
    "--clean-old", 
    type=int,
    help="Clean up completed entries older than N hours"
)
def recover(list: bool, resume: str, resume_all: bool, clean: bool, clean_old: int):
    """Recover and resume pending image generations.
    
    This command helps recover from crashes by resuming generations
    that were started but not completed.
    
    Examples:
        flux recover --list
        flux recover --resume be11d443-b64b-4c67-b66b-3a50b5ecfc18
        flux recover --resume-all
    """
    console = Console()
    queue = GenerationQueue()
    
    if clean or clean_old is not None:
        # Clean up completed entries
        if clean:
            # Clean all completed entries
            removed = queue.cleanup_completed(older_than_hours=0)
            console.print(f"[green]Cleaned up {removed} completed queue entries[/green]")
        else:
            # Clean old entries
            removed = queue.cleanup_completed(older_than_hours=clean_old)
            console.print(f"[green]Cleaned up {removed} completed entries older than {clean_old} hours[/green]")
        return
    
    if list:
        # List pending generations
        pending = queue.get_pending()
        
        if not pending:
            console.print("[yellow]No pending generations found[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Pending Generations ({len(pending)} total)")
        table.add_column("ID", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="white")
        table.add_column("Prompt", style="white", max_width=50)
        table.add_column("Attempts", style="dim")
        
        for entry in pending:
            prompt = entry["request"].get("prompt", "")[:50]
            if len(entry["request"].get("prompt", "")) > 50:
                prompt += "..."
            
            table.add_row(
                entry["id"],
                entry["status"],
                entry["created_at"].split("T")[0] + " " + entry["created_at"].split("T")[1][:8],
                prompt,
                str(entry["attempts"])
            )
        
        console.print(table)
        console.print("\n[dim]Use --resume <ID> to resume a specific generation[/dim]")
        return
    
    # Determine which generations to resume
    if resume:
        # Resume specific generation
        entry = queue.get_generation(resume)
        if not entry:
            console.print(f"[red]Generation {resume} not found[/red]")
            return
        entries_to_resume = [entry]
    elif resume_all:
        # Resume all pending
        entries_to_resume = queue.get_pending()
        if not entries_to_resume:
            console.print("[yellow]No pending generations to resume[/yellow]")
            return
    else:
        # Show help if no action specified
        console.print("[yellow]Specify --list, --resume <ID>, or --resume-all[/yellow]")
        return
    
    # Resume generations
    console.print(f"[cyan]Resuming {len(entries_to_resume)} generation(s)...[/cyan]\n")
    
    client = FluxAPIClient()
    storage = StorageManager()
    progress = ProgressTracker()
    
    success_count = 0
    fail_count = 0
    
    for entry in entries_to_resume:
        generation_id = entry["id"]
        console.print(f"[bold]Resuming {generation_id}[/bold]")
        
        try:
            # Determine output path
            model = entry["model"]
            output_format = entry["request"].get("output_format", "png")
            output_path = storage.get_output_path(model, output_format)
            
            # Resume polling
            with progress.track_generation(f"Resuming: {entry['request']['prompt'][:50]}...") as tracker:
                # Start from where we left off
                def update_with_offset(status, attempts):
                    total_attempts = entry["attempts"] + attempts
                    tracker.update(status, total_attempts)
                    queue.update_status(generation_id, status, total_attempts)
                
                # Poll for result
                status, image_url = client.poll_result(
                    entry["polling_url"],
                    callback=update_with_offset
                )
                
                if image_url:
                    # Download image
                    file_size = client.download_image(image_url, output_path)
                    
                    # Update queue
                    queue.update_status(
                        generation_id,
                        status,
                        result={
                            "image_url": image_url,
                            "file_path": str(output_path),
                            "file_size": file_size
                        }
                    )
                    
                    # Save metadata
                    from ..api.models import GenerationResult, GenerationStatus
                    result = GenerationResult(
                        id=generation_id,
                        status=GenerationStatus.SUCCESS,
                        model=model,
                        request=entry["request"],
                        file_path=str(output_path),
                        file_size=file_size
                    )
                    storage.save_metadata(result)
                    
                    # Remove from queue after successful recovery
                    queue.remove_generation(generation_id)
                    
                    console.print(f"[green]✓ Recovered: {output_path}[/green]\n")
                    success_count += 1
                else:
                    console.print(f"[red]✗ No image URL returned[/red]\n")
                    fail_count += 1
                    
        except Exception as e:
            console.print(f"[red]✗ Failed: {e}[/red]\n")
            queue.update_status(generation_id, GenerationStatus.FAILED, error=str(e))
            fail_count += 1
            logger.error(f"Failed to recover {generation_id}: {e}")
    
    # Summary
    console.print(f"\n[bold]Recovery Summary:[/bold]")
    console.print(f"  [green]Successful: {success_count}[/green]")
    console.print(f"  [red]Failed: {fail_count}[/red]")