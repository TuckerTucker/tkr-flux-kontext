"""Queue management for tracking generation requests."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4

from ..api.models import GenerationStatus

logger = logging.getLogger(__name__)


class GenerationQueue:
    """Manages a local queue of generation requests.
    
    Saves generation info immediately after API request to enable recovery
    if the script crashes during polling or download.
    
    Attributes:
        queue_dir: Directory for queue files
        queue_file: Path to the main queue file
    """
    
    def __init__(self, data_dir: Path = Path("./data")):
        """Initialize generation queue.
        
        Args:
            data_dir: Base data directory
        """
        self.queue_dir = data_dir / "queue"
        self.queue_file = self.queue_dir / "active_generations.json"
        
        # Create queue directory
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Initialized queue at: {self.queue_dir}")
    
    def add_generation(
        self,
        generation_id: str,
        polling_url: str,
        request: Dict[str, Any],
        model: str
    ) -> Dict[str, Any]:
        """Add a new generation to the queue.
        
        Args:
            generation_id: Generation ID from API
            polling_url: URL or ID for polling
            request: Original request parameters
            model: Model name
            
        Returns:
            Queue entry dictionary
        """
        entry = {
            "id": generation_id,
            "queue_id": str(uuid4()),
            "polling_url": polling_url,
            "status": GenerationStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "model": model,
            "request": request,
            "attempts": 0,
            "result": None,
            "error": None
        }
        
        # Load existing queue
        queue = self._load_queue()
        
        # Add new entry
        queue[generation_id] = entry
        
        # Save updated queue
        self._save_queue(queue)
        
        logger.info(f"Added generation {generation_id} to queue")
        return entry
    
    def update_status(
        self,
        generation_id: str,
        status: GenerationStatus,
        attempts: int = 0,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Update the status of a queued generation.
        
        Args:
            generation_id: Generation ID
            status: New status
            attempts: Number of polling attempts
            result: Result data if completed
            error: Error message if failed
        """
        queue = self._load_queue()
        
        if generation_id not in queue:
            logger.warning(f"Generation {generation_id} not found in queue")
            return
        
        entry = queue[generation_id]
        entry["status"] = status.value
        entry["updated_at"] = datetime.now().isoformat()
        entry["attempts"] = attempts
        
        if result:
            entry["result"] = result
        if error:
            entry["error"] = error
        
        self._save_queue(queue)
        logger.debug(f"Updated {generation_id} status to {status.value}")
    
    def get_generation(self, generation_id: str) -> Optional[Dict[str, Any]]:
        """Get a generation entry by ID.
        
        Args:
            generation_id: Generation ID
            
        Returns:
            Queue entry or None if not found
        """
        queue = self._load_queue()
        return queue.get(generation_id)
    
    def get_pending(self) -> List[Dict[str, Any]]:
        """Get all pending generations.
        
        Returns:
            List of pending generation entries
        """
        queue = self._load_queue()
        pending = [
            entry for entry in queue.values()
            if entry["status"] in [
                GenerationStatus.PENDING.value,
                GenerationStatus.QUEUED.value,
                GenerationStatus.PROCESSING.value,
                GenerationStatus.READY.value
            ]
        ]
        
        # Sort by creation time (oldest first)
        pending.sort(key=lambda x: x["created_at"])
        
        logger.info(f"Found {len(pending)} pending generations")
        return pending
    
    def remove_generation(self, generation_id: str) -> None:
        """Remove a generation from the queue.
        
        Args:
            generation_id: Generation ID to remove
        """
        queue = self._load_queue()
        
        if generation_id in queue:
            del queue[generation_id]
            self._save_queue(queue)
            logger.info(f"Removed {generation_id} from queue")
    
    def cleanup_completed(self, older_than_hours: int = 0) -> int:
        """Remove completed generations older than specified hours.
        
        Args:
            older_than_hours: Remove entries older than this many hours (0 = remove all completed)
            
        Returns:
            Number of entries removed
        """
        queue = self._load_queue()
        
        to_remove = []
        for gen_id, entry in queue.items():
            if entry["status"] in [GenerationStatus.SUCCESS.value, GenerationStatus.FAILED.value]:
                if older_than_hours == 0:
                    # Remove all completed entries
                    to_remove.append(gen_id)
                else:
                    # Remove only old entries
                    cutoff = datetime.now().timestamp() - (older_than_hours * 3600)
                    updated = datetime.fromisoformat(entry["updated_at"]).timestamp()
                    if updated < cutoff:
                        to_remove.append(gen_id)
        
        for gen_id in to_remove:
            del queue[gen_id]
        
        if to_remove:
            self._save_queue(queue)
            logger.info(f"Cleaned up {len(to_remove)} completed queue entries")
        
        return len(to_remove)
    
    def _load_queue(self) -> Dict[str, Dict[str, Any]]:
        """Load the queue from file.
        
        Returns:
            Queue dictionary (generation_id -> entry)
        """
        if not self.queue_file.exists():
            return {}
        
        try:
            with open(self.queue_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error("Corrupted queue file, starting fresh")
            return {}
    
    def _save_queue(self, queue: Dict[str, Dict[str, Any]]) -> None:
        """Save the queue to file.
        
        Args:
            queue: Queue dictionary to save
        """
        with open(self.queue_file, "w") as f:
            json.dump(queue, f, indent=2)
    
    def export_entry(self, generation_id: str, output_path: Path) -> None:
        """Export a queue entry to a separate file.
        
        Args:
            generation_id: Generation ID
            output_path: Path to save the entry
        """
        entry = self.get_generation(generation_id)
        if entry:
            with open(output_path, "w") as f:
                json.dump(entry, f, indent=2)
            logger.info(f"Exported {generation_id} to {output_path}")