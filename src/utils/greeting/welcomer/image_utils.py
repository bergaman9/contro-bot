import os
import glob
import logging
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
from io import BytesIO
import requests

logger = logging.getLogger('welcomer.image_utils')

def get_predefined_backgrounds(category="welcome"):
    """Get list of predefined backgrounds for welcome or byebye"""
    backgrounds = {}
    
    # Define paths for the backgrounds directory - case sensitive fix
    bg_dir = os.path.join("data", "Backgrounds")  # Capital B for Backgrounds
    
    # Make sure the directory exists
    os.makedirs(bg_dir, exist_ok=True)
    
    # Search pattern for background images
    pattern = f"{category}_*.png" if category else "*.png"
    search_path = os.path.join(bg_dir, pattern)
    
    try:
        # Get all matching images
        for bg_file in glob.glob(search_path):
            name = os.path.basename(bg_file).replace(f"{category}_", "").replace(".png", "")
            name = name.replace("_", " ").title()
            backgrounds[name] = bg_file
        
        # If no backgrounds found, add some defaults
        if not backgrounds:
            # Create default backgrounds
            default_colors = {
                "Purple": (100, 65, 165),
                "Blue": (65, 105, 225),
                "Green": (46, 139, 87),
                "Red": (220, 20, 60),
                "Dark": (33, 33, 33),
                "Light": (240, 240, 240)
            }
            
            for name, color in default_colors.items():
                background_path = os.path.join(bg_dir, f"{category}_{name.lower()}.png")
                if not os.path.exists(background_path):
                    if create_gradient_background(background_path, color):
                        backgrounds[name] = background_path
    except Exception as e:
        logger.error(f"Failed to get predefined backgrounds: {e}")
        # Return a minimal set of backgrounds as fallback
        backgrounds = {"Default": os.path.join(bg_dir, f"{category}_default.png")}
    
    return backgrounds

def create_gradient_background(filepath, color, size=(1024, 500)):
    """Create a gradient background with the given color"""
    try:
        # Create a new image with gradient
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        r, g, b = color
        
        # Create a vertical gradient
        for y in range(size[1]):
            # Calculate color based on position (darker at bottom)
            darken_factor = 0.7 + ((y / size[1]) * 0.3)  # 0.7 to 1.0
            line_color = (
                int(r * darken_factor), 
                int(g * darken_factor),
                int(b * darken_factor), 
                255
            )
            draw.line([(0, y), (size[0], y)], fill=line_color)
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save the image
        img.save(filepath, format="PNG")
        logger.info(f"Created gradient background: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to create gradient background: {e}")
        return False

def circle_avatar(image, size=(215, 215)):
    """Convert image to circle shape with transparent background."""
    try:
        image = image.resize(size, Image.LANCZOS).convert("RGBA")

        # Create a circular mask
        bigsize = (image.size[0] * 3, image.size[1] * 3)
        mask = Image.new('L', bigsize, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + bigsize, fill=255)
        mask = mask.resize(image.size, Image.LANCZOS)
        
        # Apply the mask to the alpha channel
        mask = ImageChops.darker(mask, image.split()[-1])
        image.putalpha(mask)
        
        return image
    except Exception as e:
        logger.error(f"Failed to create circle avatar: {e}")
        # Return original image if circle creation fails
        return image.resize(size, Image.LANCZOS).convert("RGBA")

def add_text_with_outline(
    draw, text, font, position, fill_color, outline_color, 
    use_outline=False, outline_width=2, shadow=False, shadow_offset=(2, 2), center=True
):
    """Add text with optional outline and shadow effects"""
    try:
        x, y = position
        
        # Calculate text width and height for centering
        try:
            # For newer Pillow versions
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:
            # Fallback for older Pillow versions
            try:
                text_width, text_height = font.getsize(text)
            except AttributeError:
                # Very basic fallback
                text_width = len(text) * 10
                text_height = 20
        
        # Center the text if requested
        if center:
            x -= text_width // 2
        
        # Add shadow if enabled
        if shadow:
            draw.text(
                (x + shadow_offset[0], y + shadow_offset[1]), 
                text, 
                font=font, 
                fill=(0, 0, 0, 128)
            )
        
        # Add outline if enabled
        if use_outline:
            # Draw the outline by drawing the text multiple times with offsets
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1), 
                            (-outline_width, 0), (outline_width, 0), 
                            (0, -outline_width), (0, outline_width)]:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        
        # Draw the main text
        draw.text((x, y), text, font=font, fill=fill_color)
    except Exception as e:
        logger.error(f"Failed to add text with outline: {e}")
        # Fallback to basic text
        try:
            draw.text(position, text, font=font, fill=fill_color)
        except Exception as e2:
            logger.error(f"Failed even basic text drawing: {e2}")

def apply_blur_background(image, blur_amount=5):
    """Apply a blur effect to the background"""
    try:
        # Apply Gaussian blur
        return image.filter(ImageFilter.GaussianBlur(blur_amount))
    except Exception as e:
        logger.error(f"Failed to apply blur: {e}")
        # Return original image if blur fails
        return image

def resize_and_crop_image(image, target_size=(1024, 500)):
    """Resize and crop an image to fit the target size while preserving aspect ratio"""
    try:
        # Get original dimensions
        width, height = image.size
        target_width, target_height = target_size
        
        # Calculate target aspect ratio
        target_ratio = target_width / target_height
        
        # Calculate current aspect ratio
        current_ratio = width / height
        
        # Determine resize dimensions
        if current_ratio > target_ratio:
            # Image is wider than needed
            new_height = target_height
            new_width = int(new_height * current_ratio)
        else:
            # Image is taller than needed
            new_width = target_width
            new_height = int(new_width / current_ratio)
        
        # Resize image
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Calculate crop box
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        
        # Crop image
        cropped_image = resized_image.crop((left, top, right, bottom))
        
        return cropped_image
    except Exception as e:
        logger.error(f"Failed to resize and crop image: {e}")
        # Return original resized image as fallback
        return image.resize(target_size, Image.LANCZOS)

def process_uploaded_image(data, target_size=(1024, 500)):
    """Process an uploaded image to fit welcome card dimensions"""
    try:
        # Open image from binary data
        image = Image.open(BytesIO(data)).convert("RGBA")
        
        # Resize and crop
        processed_image = resize_and_crop_image(image, target_size)
        
        # Return as BytesIO object
        output = BytesIO()
        processed_image.save(output, format="PNG")
        output.seek(0)
        
        return output.getvalue()
    except Exception as e:
        logger.error(f"Failed to process uploaded image: {e}")
        return None

def download_image_from_url(url):
    """Download an image from a URL and return it as a PIL Image object"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise error for bad responses
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        logger.error(f"Failed to download image from URL {url}: {e}")
        return None
