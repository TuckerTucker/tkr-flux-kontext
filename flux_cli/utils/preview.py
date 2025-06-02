"""Image preview utilities for terminal display."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


class ImagePreview:
    """Terminal image preview functionality.
    
    Attributes:
        method: Preview method (ascii/iterm2/kitty)
        max_width: Maximum preview width
        max_height: Maximum preview height
    """
    
    def __init__(
        self,
        method: str = "ascii",
        max_width: int = 80,
        max_height: int = 40
    ):
        """Initialize image preview.
        
        Args:
            method: Preview method
            max_width: Maximum width in characters
            max_height: Maximum height in characters
        """
        self.method = method
        self.max_width = max_width
        self.max_height = max_height
        
        logger.debug(f"Initialized image preview with method: {method}")
    
    def can_preview(self) -> bool:
        """Check if preview is available.
        
        Returns:
            True if preview method is supported
        """
        if self.method == "ascii":
            try:
                import ascii_magic
                return True
            except ImportError:
                logger.warning("ascii_magic not installed")
                return False
        
        elif self.method == "iterm2":
            # Check if running in iTerm2
            return os.environ.get("TERM_PROGRAM") == "iTerm.app"
        
        elif self.method == "kitty":
            # Check if running in Kitty
            return "kitty" in os.environ.get("TERM", "").lower()
        
        return False
    
    def preview(self, image_path: Path) -> bool:
        """Display image preview in terminal.
        
        Args:
            image_path: Path to image file
            
        Returns:
            True if preview was displayed
        """
        if not image_path.exists():
            logger.error(f"Image not found: {image_path}")
            return False
        
        if not self.can_preview():
            logger.warning(f"Preview method '{self.method}' not available")
            return False
        
        try:
            if self.method == "ascii":
                return self._preview_ascii(image_path)
            elif self.method == "iterm2":
                return self._preview_iterm2(image_path)
            elif self.method == "kitty":
                return self._preview_kitty(image_path)
            
        except Exception as e:
            logger.error(f"Preview failed: {e}")
            return False
        
        return False
    
    def _preview_ascii(self, image_path: Path) -> bool:
        """Display ASCII art preview.
        
        Args:
            image_path: Path to image
            
        Returns:
            True if successful
        """
        try:
            import ascii_magic
            
            # Create ASCII art - updated API
            art = ascii_magic.AsciiArt.from_image(str(image_path))
            art.to_terminal(columns=self.max_width)
            
            return True
            
        except AttributeError:
            # Try alternative ASCII library if ascii_magic API changed
            try:
                from PIL import Image
                import sys
                
                # Simple ASCII conversion
                chars = " .:-=+*#%@"
                
                with Image.open(image_path) as img:
                    # Resize to fit terminal
                    aspect = img.height / img.width
                    new_width = min(self.max_width, img.width)
                    new_height = int(aspect * new_width * 0.55)  # Terminal chars are taller
                    
                    img = img.resize((new_width, new_height))
                    img = img.convert('L')  # Convert to grayscale
                    
                    # Convert to ASCII
                    for y in range(img.height):
                        line = ""
                        for x in range(img.width):
                            pixel = img.getpixel((x, y))
                            char_idx = int((pixel / 255) * (len(chars) - 1))
                            line += chars[char_idx]
                        print(line)
                
                return True
                
            except Exception as e:
                logger.error(f"Fallback ASCII preview failed: {e}")
                return False
            
        except Exception as e:
            logger.error(f"ASCII preview failed: {e}")
            return False
    
    def _preview_iterm2(self, image_path: Path) -> bool:
        """Display inline image in iTerm2.
        
        Args:
            image_path: Path to image
            
        Returns:
            True if successful
        """
        try:
            import base64
            
            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            encoded = base64.b64encode(image_data).decode("ascii")
            
            # Get image dimensions
            with Image.open(image_path) as img:
                width, height = self._calculate_dimensions(img.size)
            
            # iTerm2 proprietary escape sequence
            osc = "\033]"
            st = "\a"
            
            # Build inline image sequence
            sequence = f"{osc}1337;File="
            sequence += f"name={base64.b64encode(image_path.name.encode()).decode()};"
            sequence += f"size={len(image_data)};"
            sequence += f"inline=1;"
            sequence += f"width={width};"
            sequence += f"height={height};"
            sequence += f":{encoded}{st}"
            
            print(sequence)
            return True
            
        except Exception as e:
            logger.error(f"iTerm2 preview failed: {e}")
            return False
    
    def _preview_kitty(self, image_path: Path) -> bool:
        """Display inline image in Kitty terminal.
        
        Args:
            image_path: Path to image
            
        Returns:
            True if successful
        """
        try:
            # Use Kitty's icat protocol
            import subprocess
            
            # Get dimensions
            with Image.open(image_path) as img:
                width, height = self._calculate_dimensions(img.size)
            
            # Use kitty's icat command if available
            result = subprocess.run(
                ["kitty", "+kitten", "icat", "--align", "left", 
                 f"--place={width}x{height}@0x0", str(image_path)],
                capture_output=True
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Kitty preview failed: {e}")
            return False
    
    def _calculate_dimensions(
        self,
        original_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Calculate preview dimensions maintaining aspect ratio.
        
        Args:
            original_size: Original (width, height)
            
        Returns:
            Scaled (width, height) in terminal characters
        """
        orig_width, orig_height = original_size
        
        # Calculate scaling factor
        width_scale = self.max_width / orig_width
        height_scale = self.max_height / orig_height
        scale = min(width_scale, height_scale, 1.0)
        
        # Apply scaling
        width = int(orig_width * scale)
        height = int(orig_height * scale)
        
        return width, height
    
    def preview_multiple(self, image_paths: list[Path], cols: int = 2) -> bool:
        """Preview multiple images in a grid.
        
        Args:
            image_paths: List of image paths
            cols: Number of columns
            
        Returns:
            True if all previews successful
        """
        if self.method != "ascii":
            # Grid preview only supported for ASCII
            logger.warning("Grid preview only supported for ASCII method")
            for path in image_paths:
                self.preview(path)
                print("-" * self.max_width)
            return True
        
        try:
            import ascii_magic
            
            # Calculate dimensions for each image
            img_width = (self.max_width - (cols - 1)) // cols
            img_height = self.max_height // ((len(image_paths) + cols - 1) // cols)
            
            # Create ASCII art for each image
            ascii_images = []
            for path in image_paths:
                if path.exists():
                    output = ascii_magic.from_image_file(
                        str(path),
                        columns=img_width,
                        width_ratio=2.2,
                        mode=ascii_magic.Modes.ASCII
                    )
                    ascii_images.append(output.split('\n'))
                else:
                    # Empty placeholder
                    ascii_images.append(['[Image not found]'] * img_height)
            
            # Display in grid
            for row in range(0, len(ascii_images), cols):
                row_images = ascii_images[row:row + cols]
                
                # Print each line of the row
                max_lines = max(len(img) for img in row_images)
                for line_idx in range(max_lines):
                    line_parts = []
                    for img in row_images:
                        if line_idx < len(img):
                            line_parts.append(img[line_idx].ljust(img_width))
                        else:
                            line_parts.append(" " * img_width)
                    print(" ".join(line_parts))
                
                # Separator between rows
                if row + cols < len(ascii_images):
                    print("-" * self.max_width)
            
            return True
            
        except Exception as e:
            logger.error(f"Grid preview failed: {e}")
            return False