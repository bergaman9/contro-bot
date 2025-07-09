"""
Imaging utilities for various image processing tasks.
"""
import discord
import io
import aiohttp
import logging
from typing import Optional, Union, Tuple
from PIL import Image, ImageDraw, ImageOps, ImageFilter

logger = logging.getLogger('imaging')

async def download_background(url: str) -> Optional[bytes]:
    """
    Download an image from a URL.
    
    Args:
        url: URL of the image to download
        
    Returns:
        bytes: Image data or None if download fails
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.warning(f"Failed to download image: HTTP {resp.status}")
                return None
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None

def circle(img_bytes: bytes, size: Tuple[int, int] = (128, 128)) -> Optional[bytes]:
    """
    Convert an image to a circular shape.
    
    Args:
        img_bytes: Raw image data
        size: Target size (width, height)
        
    Returns:
        bytes: Processed image data or None if processing fails
    """
    try:
        # Open the image
        with Image.open(io.BytesIO(img_bytes)) as img:
            # Convert to RGBA if not already
            img = img.convert("RGBA")
            
            # Resize to desired dimensions
            img = img.resize(size, Image.LANCZOS)
            
            # Create a circular mask
            mask = Image.new("L", size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size[0], size[1]), fill=255)
            
            # Apply the mask
            result = Image.new("RGBA", size, (0, 0, 0, 0))
            result.paste(img, (0, 0), mask)
            
            # Convert back to bytes
            output = io.BytesIO()
            result.save(output, format="PNG")
            return output.getvalue()
    except Exception as e:
        logger.error(f"Error creating circular image: {e}")
        return None

def apply_blur(img_bytes: bytes, radius: int = 15) -> Optional[bytes]:
    """
    Apply a blur effect to an image.
    
    Args:
        img_bytes: Raw image data
        radius: Blur radius
        
    Returns:
        bytes: Processed image data or None if processing fails
    """
    try:
        # Open the image
        with Image.open(io.BytesIO(img_bytes)) as img:
            # Apply blur filter
            blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
            
            # Convert back to bytes
            output = io.BytesIO()
            blurred.save(output, format="PNG")
            return output.getvalue()
    except Exception as e:
        logger.error(f"Error applying blur to image: {e}")
        return None

def add_overlay(img_bytes: bytes, overlay_color: Tuple[int, int, int, int] = (0, 0, 0, 128)) -> Optional[bytes]:
    """
    Add a semi-transparent overlay to an image.
    
    Args:
        img_bytes: Raw image data
        overlay_color: RGBA color tuple for the overlay
        
    Returns:
        bytes: Processed image data or None if processing fails
    """
    try:
        # Open the image
        with Image.open(io.BytesIO(img_bytes)) as img:
            # Convert to RGBA if not already
            img = img.convert("RGBA")
            
            # Create an overlay with the same size
            overlay = Image.new("RGBA", img.size, overlay_color)
            
            # Combine the images
            result = Image.alpha_composite(img, overlay)
            
            # Convert back to bytes
            output = io.BytesIO()
            result.save(output, format="PNG")
            return output.getvalue()
    except Exception as e:
        logger.error(f"Error adding overlay to image: {e}")
        return None
