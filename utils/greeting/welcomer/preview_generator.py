import os
import logging
import discord
from io import BytesIO
import base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter  # Add missing ImageDraw import

from .image_utils import (
    circle_avatar, add_text_with_outline, 
    apply_blur_background, resize_and_crop_image,
    download_image_from_url
)

logger = logging.getLogger('welcomer.preview_generator')

async def generate_card_preview(bot, member, config, is_welcome=True):
    """
    Generate a preview image for welcome/bye configuration
    
    Args:
        bot: Discord bot instance
        member: Discord member to use for the preview
        config: Configuration dictionary
        is_welcome: True for welcome card, False for goodbye card
    
    Returns:
        Path to the saved preview image
    """
    try:
        # Get background from config
        background_image = None
        
        # Handle background from config
        if "background_data" in config and config["background_data"]:
            try:
                # Try to decode base64 background data
                if isinstance(config["background_data"], str):
                    bg_data = base64.b64decode(config["background_data"])
                    background_image = Image.open(BytesIO(bg_data)).convert("RGBA")
                else:
                    background_image = Image.open(BytesIO(config["background_data"])).convert("RGBA")
            except Exception as e:
                logger.warning(f"Failed to load background data: {e}")
        
        # If not loaded via data, try URL or file path
        if background_image is None and config.get("background_url"):
            try:
                background_url = config["background_url"]
                # Check if it's a URL
                if background_url.startswith(('http://', 'https://')):
                    # Download image from URL
                    background_image = download_image_from_url(background_url)
                else:
                    # It's a local file path
                    background_image = Image.open(background_url).convert("RGBA")
            except Exception as e:
                logger.warning(f"Failed to load background from URL or path: {e}")
        
        # If still no background, use a default solid color
        if background_image is None:
            category = "welcome" if is_welcome else "byebye"
            default_bg = os.path.join("data", "Backgrounds", f"{category}_default.png")
            if os.path.exists(default_bg):
                background_image = Image.open(default_bg).convert("RGBA")
            else:
                # Create a solid color background as last resort
                background_image = Image.new("RGBA", (1024, 500), (50, 50, 50, 255))
        
        # Resize the background
        background_image = background_image.resize((1024, 500))
        
        # Apply background effects if configured
        if config.get("blur_background", False):
            background_image = apply_blur_background(background_image, blur_amount=config.get("blur_amount", 5))
        
        # Get user avatar
        if member.avatar:
            asset = member.avatar.with_size(512)
        else:
            asset = bot.user.avatar.with_size(512)
            
        data = BytesIO(await asset.read())
        pfp = Image.open(data).convert("RGBA")
        
        # Create circular avatar
        avatar_size = config.get("avatar_size", 226)
        pfp = circle_avatar(pfp, size=(avatar_size, avatar_size))
        
        # Prepare text
        main_text_key = "welcome_text" if is_welcome else "byebye_text"
        main_text = config.get(main_text_key, "HOŞ GELDİN!" if is_welcome else "GÜLE GÜLE!")
        
        member_text = f"{member.name}"
        if hasattr(member, "discriminator") and member.discriminator != "0":
            member_text += f"#{member.discriminator}"
        
        # Set up drawing
        draw = ImageDraw.Draw(background_image)
        
        # Define colors and effects
        fill_color = config.get("fill", "#FFFFFF")
        outline_color = config.get("outline_color", "#000000")
        shadow = config.get("text_shadow", False)
        
        # Load fonts
        try:
            from PIL import ImageFont
            welcome_font_size = config.get("welcome_font_size", 100)
            member_font_size = config.get("member_font_size", 42)
            
            # Try to load fonts
            welcome_font = ImageFont.truetype("data/fonts/GothamNarrow-Bold.otf", welcome_font_size)
            member_font = ImageFont.truetype("data/fonts/GothamNarrow-Bold.otf", member_font_size)
        except Exception as e:
            logger.error(f"Failed to load fonts: {e}")
            # Fall back to default font
            welcome_font = ImageFont.load_default()
            member_font = ImageFont.load_default()
        
        # Canvas dimensions and positions
        W, H = (1024, 500)
        welcome_y = config.get("welcome_y", 295)
        member_y = config.get("member_y", 390)
        avatar_y = config.get("avatar_y", 50)
        
        # Draw main text
        add_text_with_outline(
            draw, main_text, welcome_font,
            (W // 2, welcome_y), fill_color, outline_color,
            use_outline=config.get("text_outline", False),
            shadow=shadow,
            center=True
        )
        
        # Draw member text
        add_text_with_outline(
            draw, member_text, member_font,
            (W // 2, member_y), fill_color, outline_color,
            use_outline=config.get("text_outline", False),
            shadow=shadow,
            center=True
        )
        
        # Place avatar
        background_image.paste(pfp, (int((W - avatar_size) / 2), avatar_y), pfp)
        
        # Save to temporary file
        file_type = "welcome" if is_welcome else "byebye"
        output_path = f"data/Temp/{file_type}_preview_{member.id}.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        background_image.save(output_path)
        
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate card preview: {e}")
        return None
