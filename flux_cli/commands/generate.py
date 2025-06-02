"""Image generation command implementation."""

import logging
import random
from pathlib import Path
from typing import Optional, Union

import click
import yaml
from rich.console import Console
from rich.prompt import Prompt, IntPrompt, Confirm

from ..api.client import FluxAPIClient, FluxAPIError
from ..api.models import GenerationRequest, FluxModel, OutputFormat
from ..utils.storage import StorageManager
from ..utils.progress import ProgressTracker

logger = logging.getLogger(__name__)


def load_user_config() -> dict:
    """Load user configuration from config.yaml.
    
    Returns:
        Configuration dictionary
    """
    config_path = Path("config.yaml")
    if not config_path.exists():
        logger.debug("No user config found, using defaults")
        return {}
    
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load config: {e}")
        return {}


@click.command()
@click.option(
    "--prompt", "-p",
    help="Text prompt for image generation"
)
@click.option(
    "--model", "-m",
    type=click.Choice([m.value for m in FluxModel]),
    help="Model to use for generation"
)
@click.option(
    "--seed", "-s",
    type=int,
    help="Seed for reproducible generation"
)
@click.option(
    "--aspect-ratio", "-a",
    help="Aspect ratio (e.g., 16:9, 1:1, 9:16)"
)
@click.option(
    "--input-image", "-i",
    type=click.Path(exists=True, path_type=Path),
    help="Input image for image-to-image generation"
)
@click.option(
    "--output-format", "-f",
    type=click.Choice(["png", "jpeg"]),
    help="Output image format"
)
@click.option(
    "--safety", "-t",
    type=click.IntRange(0, 6),
    help="Safety tolerance level (0=strictest, 6=least strict)"
)
@click.option(
    "--upsampling/--no-upsampling",
    default=None,
    help="Enable/disable prompt upsampling"
)
@click.option(
    "--interactive", "-I",
    is_flag=True,
    help="Interactive mode with prompts"
)
def generate(
    prompt: Optional[str],
    model: Optional[str],
    seed: Optional[int],
    aspect_ratio: Optional[str],
    input_image: Optional[Path],
    output_format: Optional[str],
    safety: Optional[int],
    upsampling: Optional[bool],
    interactive: bool
):
    """Generate an image using Flux API.
    
    Examples:
        flux generate --prompt "A beautiful sunset"
        flux generate -I  # Interactive mode
        flux generate -p "Cat in space" -m flux-kontext-max --seed 42
    """
    logger.info("Starting image generation command")
    
    console = Console()
    config = load_user_config()
    defaults = config.get("defaults", {})
    
    # Interactive mode
    if interactive or not prompt:
        console.print("[bold cyan]Flux Image Generation[/bold cyan]")
        console.print()
        
        if not prompt:
            prompt = Prompt.ask("Enter your prompt")
        
        if not model:
            model = Prompt.ask(
                "Select model",
                choices=[m.value for m in FluxModel],
                default=defaults.get("model", FluxModel.KONTEXT_PRO.value)
            )
        
        if seed is None:
            use_specific = Confirm.ask("Use a specific seed for reproducibility?", default=False)
            if use_specific:
                seed_input = Prompt.ask("Enter seed value (or 'random')", default="random")
                if seed_input.lower() == "random":
                    seed = None  # Will be generated later
                else:
                    try:
                        seed = int(seed_input)
                    except ValueError:
                        console.print("[red]Invalid seed value, using random[/red]")
                        seed = None
        
        if not aspect_ratio:
            aspect_ratio = Prompt.ask(
                "Aspect ratio",
                default=defaults.get("aspect_ratio", "1:1")
            )
        
        if not output_format:
            output_format = Prompt.ask(
                "Output format",
                choices=["png", "jpeg"],
                default=defaults.get("output_format", "png")
            )
        
        if safety is None:
            safety = IntPrompt.ask(
                "Safety tolerance (0=strictest, 6=least strict)",
                default=defaults.get("safety_tolerance", 2)
            )
        
        if upsampling is None:
            upsampling = Confirm.ask(
                "Enable prompt upsampling?",
                default=defaults.get("prompt_upsampling", False)
            )
        
        if not input_image and Confirm.ask("Use an input image?", default=False):
            input_path = Prompt.ask("Input image path")
            input_image = Path(input_path)
            if not input_image.exists():
                console.print(f"[red]Error: Image not found: {input_image}[/red]")
                return
    
    # Apply defaults for non-interactive mode
    model = model or defaults.get("model", FluxModel.KONTEXT_PRO.value)
    
    # Handle seed with special 'random' support
    if seed is None:
        config_seed = defaults.get("seed")
        if config_seed == "random" or config_seed is None:
            # Generate random seed
            seed = random.randint(0, 2**32 - 1)
            logger.debug(f"Generated random seed: {seed}")
        else:
            seed = config_seed
    
    aspect_ratio = aspect_ratio or defaults.get("aspect_ratio", "1:1")
    output_format = output_format or defaults.get("output_format", "png")
    safety = safety if safety is not None else defaults.get("safety_tolerance", 2)
    upsampling = upsampling if upsampling is not None else defaults.get("prompt_upsampling", False)
    
    # Initialize components
    try:
        client = FluxAPIClient()
        storage = StorageManager()
        progress = ProgressTracker(style=config.get("display", {}).get("progress_style", "rich"))
        
        # Prepare request
        request = GenerationRequest(
            prompt=prompt,
            model=FluxModel(model),
            seed=seed,
            aspect_ratio=aspect_ratio,
            output_format=OutputFormat(output_format),
            safety_tolerance=safety,
            prompt_upsampling=upsampling
        )
        
        # Show seed being used
        console.print(f"[dim]Using seed: {seed}[/dim]")
        
        # Handle input image
        if input_image:
            console.print(f"[yellow]Encoding input image: {input_image}[/yellow]")
            request.input_image = client.encode_image(input_image)
        
        # Generate output path
        output_path = storage.get_output_path(model, output_format)
        
        # Execute generation
        try:
            with progress.track_generation(f"Generating: {prompt[:50]}...") as tracker:
                result = client.generate_and_download(
                    request=request,
                    output_path=output_path,
                    progress_callback=tracker.update,
                    use_queue=True  # Enable recovery queue
                )
        except Exception as e:
            # Check if we saved to queue
            if hasattr(e, '__cause__') or 'queue' in str(e).lower():
                console.print("\n[yellow]Generation saved to recovery queue.[/yellow]")
                console.print("[dim]Use 'flux recover --list' to see pending generations[/dim]")
            # Re-raise but ensure spinner is stopped
            raise
        
        # Save metadata
        metadata_path = storage.save_metadata(result)
        
        # Display result
        progress.display_result(result.to_dict())
        
        # Show file location instead of preview
        if result.status.value == "success":
            console.print(f"\n[green bold]✓ Generation Complete![/green bold]")
            console.print(f"\n[cyan]Image location:[/cyan]")
            console.print(f"  [white]{output_path}[/white]")
            
            # Show as file:// link for easy clicking in some terminals
            file_url = f"file://{output_path.absolute()}"
            console.print(f"\n[cyan]Click to open:[/cyan]")
            console.print(f"  [blue underline]{file_url}[/blue underline]")
            
            console.print(f"\n[dim]Metadata: {metadata_path}[/dim]")
        
    except FluxAPIError as e:
        # Clean up the error message
        error_msg = str(e)
        
        # Extract specific error details
        if "402" in error_msg and "Insufficient credits" in error_msg:
            console.print("\n[red bold]❌ Error: Insufficient API Credits[/red bold]")
            console.print("[red]Your account doesn't have enough credits to generate images.[/red]")
            console.print("\n[yellow]To fix this:[/yellow]")
            console.print("  • Check your account balance at https://api.us1.bfl.ai")
            console.print("  • Add credits to your account")
            console.print("  • Try using a different API key\n")
        elif "401" in error_msg:
            console.print("\n[red bold]❌ Error: Invalid API Key[/red bold]")
            console.print("[red]The API key provided is not valid.[/red]")
            console.print("\n[yellow]To fix this:[/yellow]")
            console.print("  • Check your .env file has the correct FLUX_API_KEY")
            console.print("  • Ensure there are no extra spaces or quotes")
            console.print("  • Get your API key from https://api.us1.bfl.ai\n")
        elif "422" in error_msg:
            console.print("\n[red bold]❌ Error: Invalid Request[/red bold]")
            console.print(f"[red]{error_msg}[/red]")
            console.print("\n[yellow]Common issues:[/yellow]")
            console.print("  • Aspect ratio must be between 21:9 and 9:21")
            console.print("  • Safety tolerance must be 0-6")
            console.print("  • Check your input parameters\n")
        elif "429" in error_msg:
            console.print("\n[red bold]❌ Error: Rate Limit Exceeded[/red bold]")
            console.print("[red]Too many requests. Please wait before trying again.[/red]")
            console.print("\n[yellow]The API has rate limits to prevent abuse.[/yellow]\n")
        else:
            console.print(f"\n[red bold]❌ API Error[/red bold]")
            console.print(f"[red]{error_msg}[/red]\n")
        
        logger.error(f"API error: {e}")
        raise SystemExit(1)
    
    except ValueError as e:
        # Handle enum conversion errors
        if "is not a valid" in str(e):
            console.print(f"\n[red bold]❌ API Response Error[/red bold]")
            console.print(f"[red]Received unexpected response format from the API.[/red]")
            console.print(f"[dim]Error: {e}[/dim]")
            console.print("\n[yellow]This might be a temporary API issue. Try again in a moment.[/yellow]\n")
        else:
            console.print(f"\n[red bold]❌ Value Error[/red bold]")
            console.print(f"[red]{e}[/red]\n")
        logger.error(f"Value error: {e}", exc_info=True)
        raise SystemExit(1)
    
    except Exception as e:
        console.print(f"\n[red bold]❌ Unexpected Error[/red bold]")
        console.print(f"[red]{e}[/red]")
        console.print("\n[dim]Check flux_cli.log for more details[/dim]\n")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise SystemExit(1)