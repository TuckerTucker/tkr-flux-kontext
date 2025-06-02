"""Flux API client implementation."""

import base64
import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import requests
from dotenv import load_dotenv

from .models import (
    GenerationRequest,
    GenerationResponse,
    GenerationResult,
    GenerationStatus,
    FluxModel,
    OutpaintingRequest
)
from ..utils.queue import GenerationQueue

logger = logging.getLogger(__name__)
load_dotenv()


class FluxAPIError(Exception):
    """Base exception for Flux API errors."""
    pass


class FluxAuthenticationError(FluxAPIError):
    """Authentication failed."""
    pass


class FluxValidationError(FluxAPIError):
    """Request validation failed."""
    pass


class FluxTimeoutError(FluxAPIError):
    """Generation timed out."""
    pass


class FluxAPIClient:
    """Client for interacting with Flux API.
    
    Attributes:
        api_key: API key for authentication
        base_url: Base URL for API endpoints
        timeout: Request timeout in seconds
        polling_interval: Seconds between polling attempts
        max_polling_attempts: Maximum polling attempts before timeout
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        polling_interval: float = 1.5,
        max_polling_attempts: int = 200  # 5 minutes with 1.5s interval
    ):
        """Initialize Flux API client.
        
        Args:
            api_key: API key (defaults to FLUX_API_KEY env var)
            base_url: Base URL (defaults to FLUX_API_BASE_URL env var)
            timeout: Request timeout in seconds
            polling_interval: Seconds between polling attempts
            max_polling_attempts: Maximum polling attempts
        """
        logger.info("Initializing Flux API client")
        
        self.api_key = api_key or os.getenv("FLUX_API_KEY")
        if not self.api_key:
            raise FluxAuthenticationError("No API key provided. Set FLUX_API_KEY environment variable.")
        
        self.base_url = (base_url or os.getenv("FLUX_API_BASE_URL", "https://api.us1.bfl.ai")).rstrip("/")
        self.timeout = timeout
        self.polling_interval = polling_interval
        self.max_polling_attempts = max_polling_attempts
        
        self.session = requests.Session()
        self.session.headers.update({
            "x-key": self.api_key,
            "Content-Type": "application/json"
        })
        
        logger.debug(f"Client initialized with base URL: {self.base_url}")
    
    def _get_endpoint(self, model: FluxModel) -> str:
        """Get API endpoint for model."""
        endpoints = {
            FluxModel.KONTEXT_PRO: "/v1/flux-kontext-pro",
            FluxModel.KONTEXT_MAX: "/v1/flux-kontext-max",
            FluxModel.PRO_EXPAND: "/v1/flux-pro-1.0-expand"
        }
        return endpoints.get(model, "/v1/flux-kontext-pro")
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and errors.
        
        Args:
            response: HTTP response
            
        Returns:
            Response data as dictionary
            
        Raises:
            FluxAPIError: On API errors
        """
        logger.debug(f"Handling response with status code: {response.status_code}")
        
        try:
            data = response.json()
        except ValueError:
            data = {"error": response.text}
        
        if response.status_code == 200:
            return data
        elif response.status_code == 401:
            raise FluxAuthenticationError("Invalid API key")
        elif response.status_code == 422:
            detail = data.get("detail", [])
            errors = [f"{err.get('loc', [])}: {err.get('msg', '')}" for err in detail]
            raise FluxValidationError(f"Validation errors: {'; '.join(errors)}")
        elif response.status_code == 429:
            raise FluxAPIError("Rate limit exceeded")
        else:
            raise FluxAPIError(f"API error ({response.status_code}): {data}")
    
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Submit generation request to API.
        
        Args:
            request: Generation request parameters
            
        Returns:
            Initial response with generation ID and polling URL
            
        Raises:
            FluxAPIError: On API errors
        """
        logger.info(f"Submitting generation request for model: {request.model}")
        
        endpoint = self._get_endpoint(request.model)
        url = f"{self.base_url}{endpoint}"
        payload = request.to_api_payload()
        
        # Debug log the payload
        logger.debug(f"API request payload: {payload}")
        
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            data = self._handle_response(response)
            
            result = GenerationResponse.from_api_response(data)
            logger.debug(f"Generation initiated with ID: {result.id}")
            
            return result
            
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise FluxAPIError(f"Request failed: {e}")
    
    def poll_result(
        self,
        polling_url: str,
        callback: Optional[callable] = None
    ) -> Tuple[GenerationStatus, Optional[str]]:
        """Poll for generation result.
        
        Args:
            polling_url: URL to poll for results (can be full URL or just ID)
            callback: Optional callback for progress updates
            
        Returns:
            Tuple of (status, image_url)
            
        Raises:
            FluxTimeoutError: If polling times out
            FluxAPIError: On API errors
        """
        # Extract request ID from polling URL if it's a full URL
        if polling_url.startswith("http"):
            # Extract ID from URL like https://api.us1.bfl.ai/v1/get_result?id=xxx
            import urllib.parse
            parsed = urllib.parse.urlparse(polling_url)
            params = urllib.parse.parse_qs(parsed.query)
            request_id = params.get('id', [None])[0]
            if not request_id:
                # Try to extract from path
                request_id = polling_url.split('/')[-1]
        else:
            request_id = polling_url
        
        logger.info(f"Starting polling for result with ID: {request_id}")
        
        attempts = 0
        start_time = time.time()
        
        # Use the documented endpoint
        poll_url = f"{self.base_url}/v1/get_result"
        
        while attempts < self.max_polling_attempts:
            attempts += 1
            
            try:
                response = self.session.get(
                    poll_url,
                    params={'id': request_id},
                    timeout=self.timeout
                )
                data = self._handle_response(response)
                
                # Handle status - example shows capitalized values
                status_str = data.get("status", "")
                
                # Map API status to our enum (handle both cases)
                status_map = {
                    "ready": GenerationStatus.READY,
                    "processing": GenerationStatus.PROCESSING,
                    "queued": GenerationStatus.QUEUED,
                    "pending": GenerationStatus.PENDING,
                    "success": GenerationStatus.SUCCESS,
                    "failed": GenerationStatus.FAILED
                }
                
                status = status_map.get(status_str.lower(), GenerationStatus.PROCESSING)
                logger.debug(f"Received status: {status_str} -> {status}")
                
                if callback:
                    callback(status, attempts)
                
                # Check for completion based on the example
                if status == GenerationStatus.READY:
                    # When Ready, the image URL is available
                    image_url = data.get("result", {}).get("sample")
                    logger.info(f"Generation completed after {attempts} attempts")
                    return GenerationStatus.SUCCESS, image_url
                
                elif status == GenerationStatus.FAILED:
                    error = data.get("error", "Unknown error")
                    logger.error(f"Generation failed: {error}")
                    raise FluxAPIError(f"Generation failed: {error}")
                
                elif status not in [GenerationStatus.PROCESSING, GenerationStatus.QUEUED, GenerationStatus.PENDING]:
                    # Unexpected status as per the example
                    logger.error(f"Unexpected status: {status_str}")
                    raise FluxAPIError(f"Unexpected status: {status_str}")
                
                # Still processing, wait before next attempt (1.5s as in example)
                time.sleep(1.5)
                
            except requests.RequestException as e:
                logger.warning(f"Polling attempt {attempts} failed: {e}")
                time.sleep(self.polling_interval)
        
        elapsed = time.time() - start_time
        logger.error(f"Polling timed out after {elapsed:.1f}s and {attempts} attempts")
        raise FluxTimeoutError(f"Generation timed out after {attempts} attempts")
    
    def download_image(self, image_url: str, output_path: Path) -> int:
        """Download generated image.
        
        Args:
            image_url: URL of generated image
            output_path: Path to save image
            
        Returns:
            File size in bytes
            
        Raises:
            FluxAPIError: On download errors
        """
        logger.info(f"Downloading image to: {output_path}")
        
        try:
            response = requests.get(image_url, timeout=self.timeout)
            response.raise_for_status()
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            
            file_size = len(response.content)
            logger.debug(f"Downloaded {file_size} bytes")
            
            return file_size
            
        except requests.RequestException as e:
            logger.error(f"Failed to download image: {e}")
            raise FluxAPIError(f"Failed to download image: {e}")
    
    def encode_image(self, image_path: Path) -> str:
        """Encode image file to base64.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded string
            
        Raises:
            FileNotFoundError: If image not found
            FluxAPIError: On encoding errors
        """
        logger.debug(f"Encoding image: {image_path}")
        
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        try:
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            
            logger.debug(f"Encoded image size: {len(encoded)} chars")
            return encoded
            
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            raise FluxAPIError(f"Failed to encode image: {e}")
    
    def generate_and_download(
        self,
        request: GenerationRequest,
        output_path: Path,
        progress_callback: Optional[callable] = None,
        use_queue: bool = True
    ) -> GenerationResult:
        """Complete generation workflow: submit, poll, download.
        
        Args:
            request: Generation request
            output_path: Path to save generated image
            progress_callback: Optional progress callback
            use_queue: Whether to save to queue for recovery
            
        Returns:
            Complete generation result
            
        Raises:
            FluxAPIError: On any API errors
        """
        logger.info("Starting complete generation workflow")
        start_time = time.time()
        
        # Initialize result
        result = GenerationResult(
            model=request.model.value,
            request=request.to_api_payload()
        )
        
        # Initialize queue if enabled
        queue = GenerationQueue() if use_queue else None
        
        try:
            # Submit generation request
            response = self.generate(request)
            result.id = response.id
            
            if not response.polling_url:
                raise FluxAPIError("No polling URL returned")
            
            # SAVE TO QUEUE IMMEDIATELY - This is the key change!
            if queue:
                queue.add_generation(
                    generation_id=response.id,
                    polling_url=response.polling_url,
                    request=request.to_api_payload(),
                    model=request.model.value
                )
                logger.info(f"Saved generation {response.id} to recovery queue")
            
            # Poll for result with queue updates
            def update_callback(status, attempts):
                # Update queue status
                if queue:
                    queue.update_status(response.id, status, attempts)
                # Call original callback
                if progress_callback:
                    progress_callback(status, attempts)
                # Update result
                result.polling_attempts = attempts
            
            status, image_url = self.poll_result(
                response.polling_url,
                callback=update_callback
            )
            
            result.status = status
            
            if image_url:
                # Update queue with image URL before download
                if queue:
                    queue.update_status(
                        response.id, 
                        GenerationStatus.SUCCESS,
                        result.polling_attempts,
                        {"image_url": image_url}
                    )
                
                # Download image
                file_size = self.download_image(image_url, output_path)
                result.file_path = str(output_path)
                result.file_size = file_size
                
                # Get image dimensions
                try:
                    from PIL import Image
                    with Image.open(output_path) as img:
                        result.dimensions = img.size
                except Exception as e:
                    logger.warning(f"Failed to get image dimensions: {e}")
                
                # Remove from queue on successful completion
                if queue:
                    logger.info(f"Removing completed generation {response.id} from queue")
                    queue.remove_generation(response.id)
            
            result.generation_time = time.time() - start_time
            logger.info(f"Generation completed in {result.generation_time:.1f}s")
            
        except Exception as e:
            result.status = GenerationStatus.FAILED
            result.error = {
                "type": type(e).__name__,
                "message": str(e)
            }
            
            # Update queue with error
            if queue and result.id:
                queue.update_status(
                    result.id,
                    GenerationStatus.FAILED,
                    result.polling_attempts,
                    error=str(e)
                )
            
            logger.error(f"Generation failed: {e}")
            raise
        
        return result