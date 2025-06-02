"""Storage utilities for managing images and metadata."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4

from ..api.models import GenerationResult

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages file storage and metadata for generated images.
    
    Attributes:
        data_dir: Base data directory
        source_dir: Directory for source images
        generated_dir: Directory for generated images
        history_file: Path to generation history log
    """
    
    def __init__(self, data_dir: Path = Path("./data")):
        """Initialize storage manager.
        
        Args:
            data_dir: Base data directory
        """
        logger.info(f"Initializing storage manager with data dir: {data_dir}")
        
        self.data_dir = Path(data_dir)
        self.source_dir = self.data_dir / "source_images"
        self.generated_dir = self.data_dir / "generated"
        self.history_dir = self.data_dir / "history"
        self.history_file = self.history_dir / "generation_log.json"
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create required directories if they don't exist."""
        logger.debug("Creating storage directories")
        
        for directory in [self.source_dir, self.generated_dir, self.history_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def get_output_path(
        self,
        model: str,
        output_format: str,
        timestamp: Optional[datetime] = None
    ) -> Path:
        """Generate output path for new image.
        
        Args:
            model: Model name
            output_format: Image format (png/jpeg)
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Path for output file
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create date-based subdirectory
        date_dir = self.generated_dir / timestamp.strftime("%Y/%m/%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        model_short = model.replace("flux-", "").replace("-", "_")
        uuid_short = str(uuid4())[:8]
        filename = timestamp.strftime(f"%Y%m%d_%H%M%S_{model_short}_{uuid_short}.{output_format}")
        
        logger.debug(f"Generated output path: {date_dir / filename}")
        return date_dir / filename
    
    def save_metadata(self, result: GenerationResult) -> Path:
        """Save generation metadata alongside image.
        
        Args:
            result: Generation result to save
            
        Returns:
            Path to metadata file
        """
        if not result.file_path:
            raise ValueError("No file path in result")
        
        image_path = Path(result.file_path)
        metadata_path = image_path.with_suffix(".json")
        
        logger.info(f"Saving metadata to: {metadata_path}")
        
        metadata = result.to_dict()
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Also append to history log
        self._append_to_history(metadata)
        
        return metadata_path
    
    def _append_to_history(self, metadata: Dict[str, Any]) -> None:
        """Append generation to history log.
        
        Args:
            metadata: Generation metadata
        """
        logger.debug("Appending to generation history")
        
        # Read existing history
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Invalid history file, starting fresh")
                history = []
        
        # Append new entry
        history.append(metadata)
        
        # Write back
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)
        
        logger.debug(f"History now contains {len(history)} entries")
    
    def get_history(
        self,
        limit: Optional[int] = None,
        status: Optional[str] = None,
        model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get generation history.
        
        Args:
            limit: Maximum number of entries to return
            status: Filter by status
            model: Filter by model
            
        Returns:
            List of generation metadata
        """
        logger.info(f"Loading history (limit={limit}, status={status}, model={model})")
        
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, "r") as f:
                history = json.load(f)
        except json.JSONDecodeError:
            logger.error("Failed to load history file")
            return []
        
        # Apply filters
        if status:
            history = [h for h in history if h.get("status") == status]
        if model:
            history = [h for h in history if h.get("model") == model]
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda h: h.get("timestamp", ""), reverse=True)
        
        # Apply limit
        if limit:
            history = history[:limit]
        
        logger.debug(f"Returning {len(history)} history entries")
        return history
    
    def get_generation_by_id(self, generation_id: str) -> Optional[Dict[str, Any]]:
        """Get specific generation by ID.
        
        Args:
            generation_id: Generation ID
            
        Returns:
            Generation metadata or None if not found
        """
        logger.debug(f"Looking for generation: {generation_id}")
        
        history = self.get_history()
        for entry in history:
            if entry.get("id") == generation_id:
                logger.debug("Found generation")
                return entry
        
        logger.warning(f"Generation not found: {generation_id}")
        return None
    
    def sanitize_filename(self, text: str, max_length: int = 50) -> str:
        """Sanitize text for use in filename.
        
        Args:
            text: Text to sanitize
            max_length: Maximum length
            
        Returns:
            Sanitized text
        """
        # Replace spaces with underscores
        text = text.replace(" ", "_")
        
        # Remove special characters
        text = re.sub(r"[^a-zA-Z0-9_.-]", "", text)
        
        # Truncate
        if len(text) > max_length:
            text = text[:max_length]
        
        # Remove trailing dots or underscores
        text = text.rstrip("._")
        
        return text or "untitled"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        logger.info("Calculating storage statistics")
        
        history = self.get_history()
        
        # Count files
        source_count = len(list(self.source_dir.glob("*.*")))
        generated_count = len(list(self.generated_dir.rglob("*.png"))) + \
                         len(list(self.generated_dir.rglob("*.jpeg")))
        
        # Calculate stats
        stats = {
            "total_generations": len(history),
            "successful_generations": len([h for h in history if h.get("status") == "success"]),
            "failed_generations": len([h for h in history if h.get("status") == "failed"]),
            "source_images": source_count,
            "generated_images": generated_count,
            "models_used": list(set(h.get("model", "") for h in history if h.get("model"))),
            "total_generation_time": sum(
                h.get("response", {}).get("generation_time", 0) 
                for h in history
            ),
            "average_generation_time": None
        }
        
        if stats["successful_generations"] > 0:
            stats["average_generation_time"] = (
                stats["total_generation_time"] / stats["successful_generations"]
            )
        
        logger.debug(f"Storage stats: {stats}")
        return stats
    
    def cleanup_orphaned_metadata(self) -> int:
        """Remove metadata files without corresponding images.
        
        Returns:
            Number of files cleaned up
        """
        logger.info("Cleaning up orphaned metadata files")
        
        cleaned = 0
        for metadata_file in self.generated_dir.rglob("*.json"):
            # Check if corresponding image exists
            image_extensions = [".png", ".jpeg", ".jpg"]
            image_exists = any(
                metadata_file.with_suffix(ext).exists() 
                for ext in image_extensions
            )
            
            if not image_exists:
                logger.debug(f"Removing orphaned metadata: {metadata_file}")
                metadata_file.unlink()
                cleaned += 1
        
        logger.info(f"Cleaned up {cleaned} orphaned metadata files")
        return cleaned