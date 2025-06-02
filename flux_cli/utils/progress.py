"""Progress tracking utilities for CLI operations."""

import logging
import time
from typing import Optional, Callable

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ..api.models import GenerationStatus

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Progress tracking for generation operations.
    
    Attributes:
        console: Rich console for output
        style: Progress display style (rich/simple/quiet)
    """
    
    def __init__(self, style: str = "rich"):
        """Initialize progress tracker.
        
        Args:
            style: Display style (rich/simple/quiet)
        """
        self.style = style
        self.console = Console()
        logger.debug(f"Initialized progress tracker with style: {style}")
    
    def track_generation(
        self,
        operation: str,
        callback: Optional[Callable] = None
    ) -> "GenerationProgress":
        """Create a generation progress tracker.
        
        Args:
            operation: Description of operation
            callback: Optional callback for updates
            
        Returns:
            GenerationProgress context manager
        """
        return GenerationProgress(
            operation=operation,
            style=self.style,
            console=self.console,
            callback=callback
        )
    
    def display_result(self, result: dict) -> None:
        """Display generation result.
        
        Args:
            result: Generation result dictionary
        """
        if self.style == "quiet":
            return
        
        if self.style == "simple":
            status = result.get("status", "unknown")
            if status == "success":
                print(f"✓ Generated: {result.get('response', {}).get('file_path', 'unknown')}")
            else:
                print(f"✗ Failed: {result.get('error', {}).get('message', 'unknown error')}")
        else:
            # Rich display
            table = Table(title="Generation Result")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("ID", result.get("id", ""))
            table.add_row("Status", result.get("status", ""))
            table.add_row("Model", result.get("model", ""))
            
            if result.get("status") == "success":
                response = result.get("response", {})
                table.add_row("File", response.get("file_path", ""))
                table.add_row("Generation Time", f"{response.get('generation_time', 0):.1f}s")
                table.add_row("Dimensions", str(response.get("dimensions", "")))
            else:
                error = result.get("error", {})
                table.add_row("Error Type", error.get("type", ""))
                table.add_row("Error Message", error.get("message", ""))
            
            self.console.print(table)


class GenerationProgress:
    """Context manager for tracking generation progress.
    
    Attributes:
        operation: Description of operation
        style: Display style
        console: Rich console
        callback: Optional progress callback
    """
    
    def __init__(
        self,
        operation: str,
        style: str = "rich",
        console: Optional[Console] = None,
        callback: Optional[Callable] = None
    ):
        """Initialize generation progress.
        
        Args:
            operation: Operation description
            style: Display style
            console: Rich console instance
            callback: Progress callback
        """
        self.operation = operation
        self.style = style
        self.console = console or Console()
        self.callback = callback
        self.progress = None
        self.task_id = None
        self.start_time = None
        
        # Status messages
        self.status_messages = {
            GenerationStatus.PENDING: "Pending...",
            GenerationStatus.QUEUED: "Waiting in queue...",
            GenerationStatus.PROCESSING: "Processing image...",
            GenerationStatus.READY: "Ready! Downloading...",
            GenerationStatus.SUCCESS: "Complete!",
            GenerationStatus.FAILED: "Failed",
            GenerationStatus.TIMEOUT: "Timed out"
        }
    
    def __enter__(self):
        """Start progress tracking."""
        logger.debug(f"Starting progress tracking for: {self.operation}")
        self.start_time = time.time()
        
        if self.style == "quiet":
            return self
        
        if self.style == "simple":
            print(f"Starting: {self.operation}")
        else:
            # Rich progress
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TextColumn("[progress.percentage]{task.fields[status]}"),
                TimeElapsedColumn(),
                console=self.console
            )
            self.progress.start()
            self.task_id = self.progress.add_task(
                self.operation,
                status="Initializing..."
            )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop progress tracking."""
        elapsed = time.time() - self.start_time
        logger.debug(f"Finished progress tracking after {elapsed:.1f}s")
        
        if self.style == "quiet":
            return
        
        if self.style == "simple":
            if exc_type:
                print(f"\nFailed after {elapsed:.1f}s")
            else:
                print(f"Completed in {elapsed:.1f}s")
        else:
            # Rich progress - ensure we stop and clear the line
            if self.progress:
                self.progress.stop()
                # Clear the progress line if there was an error
                if exc_type:
                    self.console.print("\r" + " " * 80 + "\r", end="")
    
    def update(self, status: GenerationStatus, attempts: int = 0):
        """Update progress status.
        
        Args:
            status: Current generation status
            attempts: Number of polling attempts
        """
        logger.debug(f"Progress update: {status.value} (attempt {attempts})")
        
        if self.callback:
            self.callback(status, attempts)
        
        if self.style == "quiet":
            return
        
        status_msg = self.status_messages.get(status, status.value)
        
        if self.style == "simple":
            print(f"  {status_msg} (attempt {attempts})")
        else:
            # Rich progress
            if self.progress and self.task_id is not None:
                self.progress.update(
                    self.task_id,
                    status=f"{status_msg} (attempt {attempts})"
                )


class BatchProgress:
    """Progress tracking for batch operations.
    
    Attributes:
        total: Total number of items
        style: Display style
        console: Rich console
    """
    
    def __init__(self, total: int, style: str = "rich"):
        """Initialize batch progress.
        
        Args:
            total: Total number of items
            style: Display style
        """
        self.total = total
        self.style = style
        self.console = Console()
        self.completed = 0
        self.failed = 0
        self.progress = None
        self.task_id = None
        
        logger.debug(f"Initialized batch progress for {total} items")
    
    def __enter__(self):
        """Start batch progress tracking."""
        if self.style == "quiet":
            return self
        
        if self.style == "simple":
            print(f"Processing {self.total} items...")
        else:
            # Rich progress
            self.progress = Progress(console=self.console)
            self.progress.start()
            self.task_id = self.progress.add_task(
                "Batch processing",
                total=self.total
            )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop batch progress tracking."""
        if self.style == "quiet":
            return
        
        if self.style == "simple":
            print(f"Completed: {self.completed}/{self.total} ({self.failed} failed)")
        else:
            # Rich progress
            if self.progress:
                self.progress.stop()
                
                # Show summary
                table = Table(title="Batch Processing Summary")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="white")
                
                table.add_row("Total", str(self.total))
                table.add_row("Successful", str(self.completed))
                table.add_row("Failed", str(self.failed))
                table.add_row("Success Rate", f"{(self.completed/self.total)*100:.1f}%")
                
                self.console.print(table)
    
    def update(self, success: bool = True):
        """Update batch progress.
        
        Args:
            success: Whether the item succeeded
        """
        if success:
            self.completed += 1
        else:
            self.failed += 1
        
        if self.style == "quiet":
            return
        
        if self.style == "simple":
            status = "✓" if success else "✗"
            print(f"  {status} Item {self.completed + self.failed}/{self.total}")
        else:
            # Rich progress
            if self.progress and self.task_id is not None:
                self.progress.advance(self.task_id)