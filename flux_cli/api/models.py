"""Data models for Flux API requests and responses."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import uuid4

logger = logging.getLogger(__name__)


class FluxModel(str, Enum):
    """Available Flux models."""
    KONTEXT_PRO = "flux-kontext-pro"
    KONTEXT_MAX = "flux-kontext-max"
    PRO_EXPAND = "flux-pro-1.0-expand"


class OutputFormat(str, Enum):
    """Supported output image formats."""
    PNG = "png"
    JPEG = "jpeg"


class GenerationStatus(str, Enum):
    """Status of image generation."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class GenerationRequest:
    """Request model for image generation.
    
    Attributes:
        prompt: Text description for image generation
        model: Flux model to use
        seed: Optional seed for reproducibility
        aspect_ratio: Image aspect ratio (21:9 to 9:21)
        output_format: Output image format
        input_image: Optional base64 encoded image for image-to-image
        prompt_upsampling: Whether to enhance prompt creativity
        safety_tolerance: Content moderation level (0-6)
        webhook_url: Optional webhook URL for notifications
        webhook_secret: Optional webhook secret for signature
    """
    prompt: str
    model: FluxModel = FluxModel.KONTEXT_PRO
    seed: Optional[int] = None
    aspect_ratio: str = "1:1"
    output_format: OutputFormat = OutputFormat.PNG
    input_image: Optional[str] = None
    prompt_upsampling: bool = False
    safety_tolerance: int = 2
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None

    def to_api_payload(self) -> Dict[str, Any]:
        """Convert to API request payload."""
        logger.debug(f"Converting request to API payload for model: {self.model}")
        
        payload = {
            "prompt": self.prompt,
            "output_format": self.output_format.value,
            "aspect_ratio": self.aspect_ratio,
            "prompt_upsampling": self.prompt_upsampling,
            "safety_tolerance": self.safety_tolerance
        }
        
        # Always include seed (required by API)
        if self.seed is not None:
            payload["seed"] = self.seed
            
        # Add other optional fields
        if self.input_image:
            payload["input_image"] = self.input_image
        if self.webhook_url:
            payload["webhook_url"] = self.webhook_url
        if self.webhook_secret:
            payload["webhook_secret"] = self.webhook_secret
            
        return payload


@dataclass
class OutpaintingRequest(GenerationRequest):
    """Request model for outpainting/expansion.
    
    Additional Attributes:
        image: Base64 encoded source image (replaces input_image)
        top: Pixels to expand on top
        bottom: Pixels to expand on bottom
        left: Pixels to expand on left
        right: Pixels to expand on right
        steps: Number of generation steps
        guidance: Guidance scale value
    """
    image: str = ""  # Required for outpainting
    top: int = 0
    bottom: int = 0
    left: int = 0
    right: int = 0
    steps: int = 50
    guidance: float = 50.75
    
    def __post_init__(self):
        """Set default model for outpainting."""
        self.model = FluxModel.PRO_EXPAND
        if self.image and not self.input_image:
            self.input_image = self.image
    
    def to_api_payload(self) -> Dict[str, Any]:
        """Convert to API request payload for outpainting."""
        logger.debug("Converting outpainting request to API payload")
        
        payload = super().to_api_payload()
        # Remove input_image as outpainting uses 'image'
        payload.pop("input_image", None)
        
        # Add outpainting specific fields
        payload.update({
            "image": self.image,
            "top": self.top,
            "bottom": self.bottom,
            "left": self.left,
            "right": self.right,
            "steps": self.steps,
            "guidance": self.guidance
        })
        
        return payload


@dataclass
class GenerationResponse:
    """Response model from initial API call.
    
    Attributes:
        id: Unique generation ID
        status: Current status
        polling_url: URL to poll for results
        webhook_url: Webhook URL if provided
    """
    id: str
    status: GenerationStatus = GenerationStatus.PENDING
    polling_url: Optional[str] = None
    webhook_url: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "GenerationResponse":
        """Create from API response data."""
        # Handle case-insensitive status
        status_str = data.get("status", "pending").lower()
        try:
            status = GenerationStatus(status_str)
        except ValueError:
            logger.warning(f"Unknown status in response: {status_str}, treating as pending")
            status = GenerationStatus.PENDING
        
        return cls(
            id=data.get("id", ""),
            status=status,
            polling_url=data.get("polling_url"),
            webhook_url=data.get("webhook_url")
        )


@dataclass
class GenerationResult:
    """Complete generation result with metadata.
    
    Attributes:
        id: Unique generation ID
        timestamp: When generation was initiated
        status: Final status
        model: Model used
        request: Original request
        file_path: Path to generated image
        file_size: Size in bytes
        dimensions: Image dimensions (width, height)
        generation_time: Time taken in seconds
        polling_attempts: Number of polling attempts
        error: Error details if failed
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    status: GenerationStatus = GenerationStatus.PENDING
    model: str = ""
    request: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    dimensions: Optional[tuple[int, int]] = None
    generation_time: Optional[float] = None
    polling_attempts: int = 0
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        logger.debug(f"Converting GenerationResult {self.id} to dict")
        
        # Ensure seed is always in request data
        request_data = self.request.copy() if self.request else {}
        
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "model": self.model,
            "request": request_data,
            "response": {
                "generation_time": self.generation_time,
                "polling_attempts": self.polling_attempts,
                "file_path": self.file_path,
                "file_size": self.file_size,
                "dimensions": self.dimensions
            },
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationResult":
        """Create from dictionary."""
        result = cls(
            id=data.get("id", str(uuid4())),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            status=GenerationStatus.PENDING,  # Will be set below
            model=data.get("model", ""),
            request=data.get("request", {})
        )
        
        # Handle status with fallback
        status_str = data.get("status", "pending").lower()
        try:
            result.status = GenerationStatus(status_str)
        except ValueError:
            logger.warning(f"Unknown status in saved data: {status_str}")
            result.status = GenerationStatus.PENDING
        
        if response := data.get("response"):
            result.generation_time = response.get("generation_time")
            result.polling_attempts = response.get("polling_attempts")
            result.file_path = response.get("file_path")
            result.file_size = response.get("file_size")
            result.dimensions = response.get("dimensions")
            
        result.error = data.get("error")
        
        return result


@dataclass
class BatchPrompt:
    """Single prompt in a batch operation.
    
    Attributes:
        prompt: Text prompt
        seed: Optional seed for this specific prompt
        variations: Number of variations to generate
    """
    prompt: str
    seed: Optional[int] = None
    variations: int = 1


@dataclass
class BatchRequest:
    """Request for batch processing multiple prompts.
    
    Attributes:
        prompts: List of prompts to process
        base_settings: Base settings to apply to all prompts
    """
    prompts: List[BatchPrompt]
    base_settings: GenerationRequest = field(default_factory=GenerationRequest)
    
    def __post_init__(self):
        """Validate batch request."""
        if not self.prompts:
            raise ValueError("Batch request must contain at least one prompt")
        
        logger.info(f"Created batch request with {len(self.prompts)} prompts")