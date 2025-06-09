import os
import math
import logging
import random
import uuid
import asyncio
from datetime import datetime, timedelta
from io import BytesIO
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

import discord

logger = logging.getLogger('turkoyto.card_renderer')

# Constants
FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'fonts', 'GothamNarrow-Bold.otf')

# Helper functions
async def get_user_avatar(bot, member):
    """Get user avatar as PIL Image"""
    if member.avatar:
        asset = member.avatar.with_size(512)
    else:
        default_avatar = discord.Asset(
            state=bot._connection,
            url=str(member.default_avatar.url),
            key=member.default_avatar.key
        )
        asset = default_avatar
    
    data = BytesIO(await asset.read())
    return Image.open(data).convert("RGBA")

def get_level_scheme(level):
    """Get color scheme for a specific level"""
    # Define a default scheme in case the lookup fails
    default_scheme = {
        "bg_grad": [(35, 38, 45, 255), (45, 48, 55, 255)],
        "accent": (210, 210, 210, 255),
        "panel_bg": (44, 47, 51, 200),
        "panel_border": (230, 230, 230, 240),
        "progress_bg": (60, 60, 70, 180),
        "progress_fg": (230, 230, 230, 255),
        "glow_color": (210, 210, 210, 50)
    }
    
    # Expanded color schemes for 20 levels with unique themes
    level_schemes = {
        0: {
            "bg_grad": [(35, 38, 45, 255), (45, 48, 55, 255)],
            "accent": (210, 210, 210, 255),  # White tones for level 0
            "panel_bg": (44, 47, 51, 200),
            "panel_border": (230, 230, 230, 240),  # White border
            "progress_bg": (60, 60, 70, 180),
            "progress_fg": (230, 230, 230, 255),  # White progress
            "glow_color": (210, 210, 210, 50)  # White glow
        },
        1: {
            "bg_grad": [(45, 55, 68, 255), (50, 65, 80, 255)],
            "accent": (85, 220, 216, 255),
            "panel_bg": (44, 47, 51, 190),
            "panel_border": (85, 220, 216, 240),
            "progress_bg": (60, 60, 70, 180),
            "progress_fg": (85, 220, 216, 255),
            "glow_color": (85, 220, 216, 60)
        },
        2: {
            "bg_grad": [(55, 45, 80, 255), (65, 55, 95, 255)],
            "accent": (180, 155, 255, 255),
            "panel_bg": (44, 47, 51, 180),
            "panel_border": (180, 155, 255, 240),
            "progress_bg": (60, 60, 80, 180),
            "progress_fg": (180, 155, 255, 255),
            "glow_color": (180, 155, 255, 60)
        },
        3: {
            "bg_grad": [(65, 60, 25, 255), (75, 70, 30, 255)],
            "accent": (255, 215, 20, 255),
            "panel_bg": (44, 47, 51, 170),
            "panel_border": (255, 215, 20, 240),
            "progress_bg": (70, 60, 40, 180),
            "progress_fg": (255, 215, 20, 255),
            "glow_color": (255, 215, 20, 60)
        },
        4: {
            "bg_grad": [(60, 35, 35, 255), (75, 40, 40, 255)],  # Adjusted background
            "accent": (255, 110, 110, 255),
            "panel_bg": (44, 47, 51, 180),  # Increased opacity for better visibility
            "panel_border": (255, 110, 110, 240),
            "progress_bg": (70, 50, 50, 180),
            "progress_fg": (255, 110, 110, 255),
            "glow_color": (255, 110, 110, 70)  # Increased glow intensity
        },
        5: {
            "bg_grad": [(35, 65, 35, 255), (40, 80, 40, 255)],
            "accent": (120, 255, 120, 255),
            "panel_bg": (44, 47, 51, 150),
            "panel_border": (120, 255, 120, 240),
            "progress_bg": (50, 70, 50, 180),
            "progress_fg": (120, 255, 120, 255),
            "glow_color": (120, 255, 120, 60)
        },
        6: {
            "bg_grad": [(70, 40, 85, 255), (85, 50, 105, 255)],  # Royal purple
            "accent": (200, 130, 255, 255),  # Bright purple
            "panel_bg": (44, 47, 51, 180),
            "panel_border": (200, 130, 255, 240),
            "progress_bg": (60, 45, 75, 180),
            "progress_fg": (200, 130, 255, 255),
            "glow_color": (200, 130, 255, 60)
        },
        7: {
            "bg_grad": [(30, 60, 80, 255), (40, 75, 100, 255)],  # Deep blue
            "accent": (100, 200, 255, 255),  # Sky blue
            "panel_bg": (44, 47, 51, 170),
            "panel_border": (100, 200, 255, 240),
            "progress_bg": (40, 60, 80, 180),
            "progress_fg": (100, 200, 255, 255),
            "glow_color": (100, 200, 255, 60)
        },
        8: {
            "bg_grad": [(80, 70, 30, 255), (100, 85, 35, 255)],  # Amber
            "accent": (255, 190, 65, 255),  # Gold
            "panel_bg": (44, 47, 51, 160),
            "panel_border": (255, 190, 65, 240),
            "progress_bg": (75, 65, 40, 180),
            "progress_fg": (255, 190, 65, 255),
            "glow_color": (255, 190, 65, 60)
        },
        9: {
            "bg_grad": [(75, 35, 75, 255), (90, 45, 90, 255)],  # Deep magenta
            "accent": (255, 105, 255, 255),  # Pink
            "panel_bg": (44, 47, 51, 170),
            "panel_border": (255, 105, 255, 240),
            "progress_bg": (70, 40, 70, 180),
            "progress_fg": (255, 105, 255, 255),
            "glow_color": (255, 105, 255, 60)
        },
        10: {
            "bg_grad": [(25, 85, 100, 255), (30, 100, 120, 255)],  # Teal
            "accent": (65, 235, 255, 255),  # Cyan
            "panel_bg": (40, 45, 50, 150),
            "panel_border": (65, 235, 255, 240),
            "progress_bg": (30, 75, 90, 180),
            "progress_fg": (65, 235, 255, 255),
            "glow_color": (65, 235, 255, 70)
        },
        11: {
            "bg_grad": [(90, 40, 30, 255), (110, 50, 40, 255)],  # Rust
            "accent": (255, 130, 90, 255),  # Coral
            "panel_bg": (44, 47, 51, 165),
            "panel_border": (255, 130, 90, 240),
            "progress_bg": (80, 50, 40, 180),
            "progress_fg": (255, 130, 90, 255),
            "glow_color": (255, 130, 90, 60)
        },
        12: {
            "bg_grad": [(50, 100, 65, 255), (60, 120, 75, 255)],  # Forest green
            "accent": (130, 255, 170, 255),  # Mint green
            "panel_bg": (44, 47, 51, 155),
            "panel_border": (130, 255, 170, 240),
            "progress_bg": (45, 85, 60, 180),
            "progress_fg": (130, 255, 170, 255),
            "glow_color": (130, 255, 170, 60)
        },
        13: {
            "bg_grad": [(55, 25, 75, 255), (65, 30, 95, 255)],  # Deep violet
            "accent": (170, 85, 255, 255),  # Lavender
            "panel_bg": (40, 42, 48, 180),
            "panel_border": (170, 85, 255, 240),
            "progress_bg": (50, 30, 70, 180),
            "progress_fg": (170, 85, 255, 255),
            "glow_color": (170, 85, 255, 65)
        },
        14: {
            "bg_grad": [(95, 70, 20, 255), (115, 85, 25, 255)],  # Bronze
            "accent": (235, 175, 50, 255),  # Golden yellow
            "panel_bg": (44, 47, 51, 160),
            "panel_border": (235, 175, 50, 240),
            "progress_bg": (80, 65, 30, 180),
            "progress_fg": (235, 175, 50, 255),
            "glow_color": (235, 175, 50, 60)
        },
        15: {
            "bg_grad": [(30, 75, 105, 255), (40, 90, 125, 255)],  # Marine blue
            "accent": (80, 180, 255, 255),  # Bright blue
            "panel_bg": (40, 43, 48, 170),
            "panel_border": (80, 180, 255, 240),
            "progress_bg": (35, 65, 90, 180),
            "progress_fg": (80, 180, 255, 255),
            "glow_color": (80, 180, 255, 65)
        },
        16: {
            "bg_grad": [(85, 30, 60, 255), (105, 40, 75, 255)],  # Burgundy
            "accent": (230, 90, 170, 255),  # Hot pink
            "panel_bg": (40, 43, 48, 175),
            "panel_border": (230, 90, 170, 240),
            "progress_bg": (75, 35, 55, 180),
            "progress_fg": (230, 90, 170, 255),
            "glow_color": (230, 90, 170, 60)
        },
        17: {
            "bg_grad": [(25, 90, 80, 255), (35, 110, 95, 255)],  # Emerald
            "accent": (60, 255, 210, 255),  # Turquoise
            "panel_bg": (40, 43, 48, 160),
            "panel_border": (60, 255, 210, 240),
            "progress_bg": (30, 80, 70, 180),
            "progress_fg": (60, 255, 210, 255),
            "glow_color": (60, 255, 210, 60)
        },
        18: {
            "bg_grad": [(100, 100, 100, 255), (125, 125, 125, 255)],  # Silver
            "accent": (220, 220, 220, 255),  # Platinum
            "panel_bg": (40, 43, 48, 150),
            "panel_border": (220, 220, 220, 240),
            "progress_bg": (80, 80, 85, 180),
            "progress_fg": (220, 220, 220, 255),
            "glow_color": (220, 220, 220, 70)
        },
        19: {
            "bg_grad": [(80, 70, 10, 255), (100, 90, 15, 255)],  # Royal gold
            "accent": (255, 230, 30, 255),  # Bright gold
            "panel_bg": (40, 43, 48, 140),
            "panel_border": (255, 230, 30, 240),
            "progress_bg": (70, 65, 25, 180),
            "progress_fg": (255, 230, 30, 255),
            "glow_color": (255, 230, 30, 80)
        }
    }
    
    # Ensure we get the right level scheme
    level_key = min(level, 19)  # Cap at level 19
    return level_schemes.get(level_key, default_scheme)

def scheme_to_discord_color(scheme):
    """Convert a color scheme's accent color to a Discord color integer"""
    rgb = scheme["accent"][:3]  # Get RGB components
    return (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]

def draw_retro_background(width=900, height=300):
    """
    Retro grid ve neon çizgilerle görseldeki gibi bir arka plan efekti oluşturur.
    """
    from PIL import Image, ImageDraw
    import math
    # Arka planı siyah/mor degrade ile başlat
    bg = Image.new('RGBA', (width, height), (25, 25, 30, 255))
    draw = ImageDraw.Draw(bg)
    # Degrade (üst: mor, alt: koyu mavi)
    for y in range(height):
        ratio = y / height
        r = int(30 + (40-30)*ratio + (120-30)*(1-ratio))
        g = int(0 + (0-0)*ratio + (0-0)*(1-ratio))
        b = int(60 + (120-60)*ratio + (255-60)*(1-ratio))
        if y < height//2:
            color = (60+int(80*ratio), 0, 120+int(80*ratio), 255)
        else:
            color = (30, 0, 60+int(195*ratio), 255)
        draw.line([(0, y), (width, y)], fill=color)
    # Yıldızlar
    import random
    for _ in range(80):
        x = random.randint(0, width-1)
        y = random.randint(0, int(height*0.6))
        star_color = (255, 255, 255, random.randint(120, 200))
        draw.ellipse((x, y, x+1, y+1), fill=star_color)
    # Grid çizgileri
    grid_color = (200, 0, 255, 120)
    grid_rows = 14
    grid_cols = 18
    grid_bottom = int(height*0.75)
    for i in range(grid_rows):
        y = grid_bottom - int((i/(grid_rows-1))**1.7 * grid_bottom)
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)
    for i in range(grid_cols):
        x = int(i/(grid_cols-1) * width)
        draw.line([(x, grid_bottom), (width//2, height)], fill=grid_color, width=1)
    # Neon çizgiler (sol üstten sağ alta ve sağ üstten sol alta)
    neon_color = (255, 0, 255, 180)
    neon_width = 4
    # Sol üst
    draw.line([(int(width*0.08), int(height*0.05)), (int(width*0.35), int(height*0.45))], fill=neon_color, width=neon_width)
    draw.line([(int(width*0.35), int(height*0.45)), (int(width*0.08), int(height*0.85))], fill=neon_color, width=neon_width)
    # Sağ üst
    draw.line([(int(width*0.92), int(height*0.05)), (int(width*0.65), int(height*0.45))], fill=neon_color, width=neon_width)
    draw.line([(int(width*0.65), int(height*0.45)), (int(width*0.92), int(height*0.85))], fill=neon_color, width=neon_width)
    return bg

def draw_theme_gradient_background(scheme, width=900, height=300):
    """
    Temaya uygun bir gradient arka plan oluşturur ve üstüne grid efekti ekler.
    """
    from PIL import Image, ImageDraw
    bg = Image.new('RGBA', (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(bg)
    grad_top = scheme["bg_grad"][0]
    grad_bot = scheme["bg_grad"][1]
    for y in range(height):
        ratio = y / (height-1)
        r = int(grad_top[0] * (1-ratio) + grad_bot[0] * ratio)
        g = int(grad_top[1] * (1-ratio) + grad_bot[1] * ratio)
        b = int(grad_top[2] * (1-ratio) + grad_bot[2] * ratio)
        a = int(grad_top[3] * (1-ratio) + grad_bot[3] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, a))
    # --- Grid efekti overlay ---
    grid_color = (200, 0, 255, 90)
    grid_rows = 14
    grid_cols = 18
    grid_bottom = int(height*0.78)
    for i in range(grid_rows):
        y = grid_bottom - int((i/(grid_rows-1))**1.7 * grid_bottom)
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)
    for i in range(grid_cols):
        x = int(i/(grid_cols-1) * width)
        draw.line([(x, grid_bottom), (width//2, height)], fill=grid_color, width=1)
    # Neon kenar çizgileri
    neon_color = (255, 0, 255, 140)
    neon_width = 4
    draw.line([(int(width*0.08), int(height*0.05)), (int(width*0.35), int(height*0.45))], fill=neon_color, width=neon_width)
    draw.line([(int(width*0.35), int(height*0.45)), (int(width*0.08), int(height*0.85))], fill=neon_color, width=neon_width)
    draw.line([(int(width*0.92), int(height*0.05)), (int(width*0.65), int(height*0.45))], fill=neon_color, width=neon_width)
    draw.line([(int(width*0.65), int(height*0.45)), (int(width*0.92), int(height*0.85))], fill=neon_color, width=neon_width)
    return bg

def draw_retro_grid_overlay(width=900, height=300):
    """
    Transparan retro grid ve neon efektli overlay döndürür.
    """
    from PIL import Image, ImageDraw
    import math
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Yıldızlar
    import random
    for _ in range(60):
        x = random.randint(0, width-1)
        y = random.randint(0, int(height*0.6))
        star_color = (255, 255, 255, random.randint(80, 160))
        draw.ellipse((x, y, x+1, y+1), fill=star_color)
    # Grid çizgileri (perspektifli)
    grid_color = (200, 0, 255, 90)
    grid_rows = 14
    grid_cols = 18
    grid_bottom = int(height*0.78)
    for i in range(grid_rows):
        y = grid_bottom - int((i/(grid_rows-1))**1.7 * grid_bottom)
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)
    for i in range(grid_cols):
        x = int(i/(grid_cols-1) * width)
        draw.line([(x, grid_bottom), (width//2, height)], fill=grid_color, width=1)
    # Neon kenar çizgileri
    neon_color = (255, 0, 255, 140)
    neon_width = 4
    draw.line([(int(width*0.08), int(height*0.05)), (int(width*0.35), int(height*0.45))], fill=neon_color, width=neon_width)
    draw.line([(int(width*0.35), int(height*0.45)), (int(width*0.08), int(height*0.85))], fill=neon_color, width=neon_width)
    draw.line([(int(width*0.92), int(height*0.05)), (int(width*0.65), int(height*0.45))], fill=neon_color, width=neon_width)
    draw.line([(int(width*0.65), int(height*0.45)), (int(width*0.92), int(height*0.85))], fill=neon_color, width=neon_width)
    return overlay

async def create_level_card(bot, member, userdata, guild=None, mongo_db=None, output_path=None):
    """
    Create a visually improved level card with retro gaming elements.
    
    Args:
        bot: Discord bot instance
        member (discord.Member): Discord member
        userdata (dict): User data prepared by XPManager
        guild (discord.Guild, optional): Discord guild for rank calculation
        mongo_db: MongoDB database connection for rank calculation (optional, preferred to use XPManager)
        output_path (str, optional): Custom output path for the image
        
    Returns:
        str: The path to the saved image file
    """
    try:
        # Log the input userdata for debugging and the member
        logger.info(f"Creating level card for user {member.id} ({member.name})")
        logger.info(f"Input userdata: {userdata}")
        
        # We expect userdata to be pre-prepared by XPManager
        # If it's not, we'll use directly provided data or fallbacks
        
        # Make sure all required fields are present
        if "level" not in userdata or userdata["level"] is None:
            userdata["level"] = 0
        if "xp" not in userdata or userdata["xp"] is None:
            userdata["xp"] = 0
        if "next_level_xp" not in userdata or userdata["next_level_xp"] is None:
            userdata["next_level_xp"] = 1000
        if "rank" not in userdata or userdata["rank"] is None:
            userdata["rank"] = "?"
            
        logger.info(f"Final userdata for rendering: Level={userdata.get('level')}, XP={userdata.get('xp')}, Rank={userdata.get('rank')}")

        # user_level'ı başta tanımla
        user_level = userdata.get("level", 0)

        # Temaya uygun gradient arka planı oluştur
        scheme = get_level_scheme(user_level)
        background_image = draw_theme_gradient_background(scheme, 900, 300)
        # Üstüne retro grid overlay ekle
        retro_overlay = draw_retro_grid_overlay(900, 300)
        background_image = Image.alpha_composite(background_image, retro_overlay)

        # Avatar size and position
        AVATAR_SIZE = 160
        AVATAR_X = 80
        AVATAR_Y = 70

        # Get user avatar
        pfp = await get_user_avatar(bot, member)
        pfp = pfp.resize((AVATAR_SIZE, AVATAR_SIZE))

        # Get user level and XP - use values from userdata
        user_level = userdata.get("level", 0)
        user_xp = userdata.get("xp", 0)

        # Cap level and XP at max values
        if user_level >= 20:
            user_level = 19
            user_next_level_xp = 500000
            user_xp = min(user_xp, 500000)
        else:
            user_next_level_xp = userdata.get("next_level_xp", 1000)
            
        # Calculate progress percentage
        try:
            if user_next_level_xp > 0:
                progress = min(max(user_xp / user_next_level_xp, 0.0), 1.0)
            else:
                progress = 0.0
        except Exception:
            progress = 0.0
        
        # Get level-specific color scheme
        scheme = get_level_scheme(user_level)

        # Create gradient background
        for y in range(300):
            r = int(scheme["bg_grad"][0][0] + (scheme["bg_grad"][1][0] - scheme["bg_grad"][0][0]) * (y / 300))
            g = int(scheme["bg_grad"][0][1] + (scheme["bg_grad"][1][1] - scheme["bg_grad"][0][1]) * (y / 300))
            b = int(scheme["bg_grad"][0][2] + (scheme["bg_grad"][1][2] - scheme["bg_grad"][0][2]) * (y / 300))
            color = (r, g, b, 255)
            for x in range(900):
                background_image.putpixel((x, y), color)

        draw = ImageDraw.Draw(background_image)

        # Load fonts
        try:
            font_big = ImageFont.truetype(FONT_PATH, 44)
            font_med = ImageFont.truetype(FONT_PATH, 30)
            font_small = ImageFont.truetype(FONT_PATH, 20)
            font_level = ImageFont.truetype(FONT_PATH, 32)
            font_rank_label = ImageFont.truetype(FONT_PATH, 18)
        except Exception as font_error:
            logger.warning(f"Error loading fonts: {font_error}. Using default font.")
            font_big = font_med = font_small = font_level = font_rank_label = ImageFont.load_default()

        white = (255, 255, 255, 255)
        gray = (180, 195, 205, 255)

        # Panel with glow effect
        panel_rect = (30, 30, 870, 270)
        glow = Image.new("RGBA", background_image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        expanded_rect = (panel_rect[0]-15, panel_rect[1]-15, panel_rect[2]+15, panel_rect[3]+15)
        glow_draw.rounded_rectangle(expanded_rect, radius=42, fill=scheme["glow_color"])
        glow = glow.filter(ImageFilter.GaussianBlur(20))
        background_image = Image.alpha_composite(background_image, glow)

        # Main panel
        panel = Image.new("RGBA", background_image.size, (0, 0, 0, 0))
        panel_draw = ImageDraw.Draw(panel)
        panel_draw.rounded_rectangle(panel_rect, radius=32, fill=scheme["panel_bg"])
        for i in range(3):
            grad_rect = (panel_rect[0]+i, panel_rect[1]+i, panel_rect[2]-i, panel_rect[3]-i)
            border_color = (*scheme["panel_border"][:3], 180 - i * 40)
            panel_draw.rounded_rectangle(grad_rect, radius=32-i, outline=border_color, width=2)
        background_image = Image.alpha_composite(background_image, panel)
        draw = ImageDraw.Draw(background_image)

        # Avatar with glow border
        mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)
        pfp_circ = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
        pfp_circ.paste(pfp, (0, 0), mask)
        border_center_x, border_center_y = AVATAR_X + AVATAR_SIZE // 2, AVATAR_Y + AVATAR_SIZE // 2
        for i in range(6):
            border_size = AVATAR_SIZE + 18 - i * 3
            border_opacity = 180 - i * 30
            if border_opacity > 0:
                border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
                border_draw = ImageDraw.Draw(border)
                border_color = (*scheme["accent"][:3], border_opacity)
                border_draw.ellipse((0, 0, border_size-1, border_size-1), outline=border_color, width=4)
                centered_x = border_center_x - border_size // 2
                centered_y = border_center_y - border_size // 2
                background_image.paste(border, (centered_x, centered_y), border)
        border = Image.new("RGBA", (AVATAR_SIZE+8, AVATAR_SIZE+8), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border)
        border_draw.ellipse((0, 0, AVATAR_SIZE+7, AVATAR_SIZE+7), fill=scheme["accent"])
        border.paste(pfp_circ, (4, 4), pfp_circ)
        background_image.paste(border, (AVATAR_X-4, AVATAR_Y-4), border)

        # Username with shadow
        name_x = AVATAR_X + AVATAR_SIZE + 40
        name_y = AVATAR_Y + 10

        try:
            name_bbox = font_big.getbbox(member.name)
            name_width = name_bbox[2] - name_bbox[0]
            name_height = name_bbox[3] - name_bbox[1]
        except AttributeError:
            name_width, name_height = font_big.getsize(member.name)

        draw.text((name_x+2, name_y+2), member.name, font=font_big, fill=(0, 0, 0, 150))
        draw.text((name_x, name_y), member.name, font=font_big, fill=white)
        
        name_y_offset = 0
        if hasattr(member, "discriminator") and member.discriminator and member.discriminator != "0":
            draw.text((name_x+1, name_y+46), f"#{member.discriminator}", font=font_small, fill=(0, 0, 0, 150))
            draw.text((name_x, name_y+45), f"#{member.discriminator}", font=font_small, fill=gray)
            name_y_offset = 25

        # Level and rank badges
        badge_height = 55
        progress_y_offset = 0
        
        if userdata.get("rank") is not None:
            # Rank badge
            rank_text = f"#{userdata['rank']}"
            rank_label = "RANK"
            
            rank_num_font_size = 30
            if len(rank_text) > 3:
                rank_num_font_size = max(30 - ((len(rank_text) - 3) * 2), 18)
            
            font_rank_num = ImageFont.truetype(FONT_PATH, rank_num_font_size)
            
            rank_number_bbox = font_rank_num.getbbox(rank_text)
            rank_number_width = rank_number_bbox[2] - rank_number_bbox[0]
            rank_label_bbox = font_rank_label.getbbox(rank_label)
            rank_label_width = rank_label_bbox[2] - rank_label_bbox[0]
            
            badge_width = max(rank_number_width, rank_label_width) + 16
            
            badge_x = 820 - badge_width
            badge_y = name_y - 8
            
            rank_badge = Image.new("RGBA", background_image.size, (0, 0, 0, 0))
            rank_badge_draw = ImageDraw.Draw(rank_badge)
            
            rank_badge_draw.rounded_rectangle(
                (badge_x, badge_y, badge_x + badge_width, badge_y + badge_height),
                radius=12,
                fill=scheme["progress_bg"]
            )
            
            for i in range(2):
                rank_badge_draw.rounded_rectangle(
                    (badge_x + i, badge_y + i, badge_x + badge_width - i, badge_y + badge_height - i),
                    radius=12-i,
                    outline=(*scheme["accent"][:3], 220 - i * 40),
                    width=2
                )
            
            background_image = Image.alpha_composite(background_image, rank_badge)
            draw = ImageDraw.Draw(background_image)
            
            label_x = badge_x + (badge_width - rank_label_width) // 2
            label_y = badge_y + 8
            
            draw.text(
                (label_x + 1, label_y + 1),
                rank_label,
                font=font_rank_label,
                fill=(0, 0, 0, 120)
            )
            
            draw.text(
                (label_x, label_y),
                rank_label,
                font=font_rank_label,
                fill=(255, 255, 255, 220)
            )
            
            number_x = badge_x + (badge_width - rank_number_width) // 2
            number_y = label_y + 15
            
            draw.text(
                (number_x + 1, number_y + 1),
                rank_text,
                font=font_rank_num,
                fill=(0, 0, 0, 120)
            )
            
            draw.text(
                (number_x, number_y),
                rank_text,
                font=font_rank_num,
                fill=scheme["accent"]
            )
            
            # Level badge
            level_label = "LEVEL"
            level_text = str(user_level)
            
            level_label_bbox = font_rank_label.getbbox(level_label)
            level_label_width = level_label_bbox[2] - level_label_bbox[0]
            
            level_num_font_size = rank_num_font_size
            font_level_num = ImageFont.truetype(FONT_PATH, level_num_font_size)
            
            level_number_bbox = font_level_num.getbbox(level_text)
            level_number_width = level_number_bbox[2] - level_number_bbox[0]
            
            level_badge_width = max(level_number_width, level_label_width) + 16
            
            level_badge_x = badge_x - level_badge_width - 10
            level_badge_y = badge_y
            
            level_badge = Image.new("RGBA", background_image.size, (0, 0, 0, 0))
            level_badge_draw = ImageDraw.Draw(level_badge)
            
            level_badge_draw.rounded_rectangle(
                (level_badge_x, level_badge_y, level_badge_x + level_badge_width, level_badge_y + badge_height),
                radius=12,
                fill=scheme["progress_bg"]
            )
            
            for i in range(2):
                level_badge_draw.rounded_rectangle(
                    (level_badge_x + i, level_badge_y + i, level_badge_x + level_badge_width - i, level_badge_y + badge_height - i),
                    radius=12-i,
                    outline=(*scheme["accent"][:3], 220 - i * 40),
                    width=2
                )
            
            background_image = Image.alpha_composite(background_image, level_badge)
            draw = ImageDraw.Draw(background_image)
            
            level_label_x = level_badge_x + (level_badge_width - level_label_width) // 2
            level_label_y = level_badge_y + 8
            
            draw.text(
                (level_label_x + 1, level_label_y + 1),
                level_label,
                font=font_rank_label,
                fill=(0, 0, 0, 120)
            )
            
            draw.text(
                (level_label_x, level_label_y),
                level_label,
                font=font_rank_label,
                fill=(255, 255, 255, 220)
            )
            
            level_number_x = level_badge_x + (level_badge_width - level_number_width) // 2
            level_number_y = level_label_y + 15
            
            draw.text(
                (level_number_x + 1, level_number_y + 1),
                level_text,
                font=font_level_num,
                fill=(0, 0, 0, 120)
            )
            
            draw.text(
                (level_number_x, level_number_y),
                level_text,
                font=font_level_num,
                fill=scheme["accent"]
            )

        # Progress bar positioning
        bar_height = 40
        
        if hasattr(member, "discriminator") and member.discriminator and member.discriminator != "0":
            base_offset = 80
        else:
            base_offset = 70
        
        bar_y0 = name_y + base_offset + progress_y_offset

        bar_x0 = name_x
        bar_x1 = 820
        bar_y1 = bar_y0 + bar_height
        bar_width = bar_x1 - bar_x0
        
        fill_width = int(bar_width * progress)
        
        # Progress bar background
        progress_bg = Image.new("RGBA", background_image.size, (0, 0, 0, 0))
        progress_bg_draw = ImageDraw.Draw(progress_bg)
        progress_bg_draw.rounded_rectangle((bar_x0, bar_y0, bar_x1, bar_y1), radius=bar_height//4, fill=scheme["progress_bg"])
        
        for i in range(1, 10):
            line_x = bar_x0 + i * (bar_width // 10)
            line_opacity = 40
            line_color = (255, 255, 255, line_opacity)
            progress_bg_draw.line((line_x, bar_y0, line_x, bar_y1), fill=line_color, width=1)
        background_image = Image.alpha_composite(background_image, progress_bg)
        draw = ImageDraw.Draw(background_image)

        # Progress fill
        if fill_width > 0:
            if fill_width < bar_height // 2:
                progress_mask = Image.new("L", background_image.size, 0)
                mask_draw = ImageDraw.Draw(progress_mask)
                
                corner_radius = bar_height // 4
                mask_draw.rounded_rectangle(
                    (bar_x0, bar_y0, bar_x0 + fill_width, bar_y1),
                    radius=corner_radius,
                    fill=255
                )
                
                progress_mask = progress_mask.filter(ImageFilter.GaussianBlur(0.5))
                
                fill_color_img = Image.new("RGBA", background_image.size, scheme["progress_fg"])
                
                background_image.paste(fill_color_img, (0, 0), progress_mask)
            else:
                fill_mask = Image.new("L", background_image.size, 0)
                fill_mask_draw = ImageDraw.Draw(fill_mask)
                
                corner_radius = bar_height // 4
                
                fill_mask_draw.rounded_rectangle(
                    (bar_x0, bar_y0, bar_x0 + fill_width, bar_y1), 
                    radius=corner_radius, 
                    fill=255
                )
                
                fill_mask = fill_mask.filter(ImageFilter.GaussianBlur(0.5))
                
                fill_color_img = Image.new("RGBA", background_image.size, scheme["progress_fg"])
                
                background_image.paste(fill_color_img, (0, 0), fill_mask)
            
            draw = ImageDraw.Draw(background_image)

        # Progress bar border
        for i in range(2):
            border_rect = (bar_x0+i, bar_y0+i, bar_x1-i, bar_y1-i)
            border_color = (*scheme["accent"][:3], 220 - i * 40)
            draw.rounded_rectangle(border_rect, radius=bar_height//4-i, outline=border_color, width=2)

        # XP text
        xp_text = f"{int(user_xp)}/{int(user_next_level_xp)} XP"

        try:
            xp_bbox = font_med.getbbox(xp_text)
            xp_w = xp_bbox[2] - xp_bbox[0] 
            xp_h = xp_bbox[3] - xp_bbox[1]
        except AttributeError:
            xp_w, xp_h = font_med.getsize(xp_text)
        
        text_x = bar_x0 + (bar_width - xp_w) // 2
        
        try:
            text_y = bar_y0 + (bar_height - xp_h) // 2 - xp_bbox[1]
        except (NameError, UnboundLocalError):
            text_y = bar_y0 + (bar_height - xp_h) // 2
        
        draw.text((text_x+1, text_y+1), xp_text, font=font_med, fill=(0, 0, 0, 120))
        draw.text((text_x, text_y), xp_text, font=font_med, fill=(255, 255, 255, 220))

        # Additional info flags
        info_texts = []
        if userdata.get("authorized"):
            info_texts.append("✅ Authorized")
        if userdata.get("processed"):
            info_texts.append("🟢 Processed")
        if info_texts:
            info_text = " | ".join(info_texts)
            
            try:
                info_bbox = font_small.getbbox(info_text)
                info_width = info_bbox[2] - info_bbox[0] + 20
            except AttributeError:
                info_width, _ = font_small.getsize(info_text)
                info_width += 20
                
            info_bg = Image.new("RGBA", background_image.size, (0, 0, 0, 0))
            info_bg_draw = ImageDraw.Draw(info_bg)
            info_bg_draw.rounded_rectangle((50, 255, 50+info_width, 275), radius=10, fill=(0, 0, 0, 100))
            background_image = Image.alpha_composite(background_image, info_bg)
            draw = ImageDraw.Draw(background_image)
            draw.text((61, 261), info_text, font=font_small, fill=(0, 0, 0, 150))
            draw.text((60, 260), info_text, font=font_small, fill=scheme["accent"])

        # Save the image
        if output_path is None:
            # Change to save in data/Temp folder
            os.makedirs("data/Temp", exist_ok=True)
            output_path = f"data/Temp/level_card_{member.id}.png"
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        background_image = background_image.convert("RGBA")
        background_image.save(output_path, format="PNG")
        logger.info(f"Saved level card to: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error creating level card for {member.id}: {e}", exc_info=True)
        return None

def get_font_path():
    font_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'fonts', 'GothamNarrow-Bold.otf'),
        'fonts/GothamNarrow-Bold.otf',
        'C:/Windows/Fonts/Arial.ttf',
        'C:/Windows/Fonts/Segoe UI Bold.ttf'
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    return None

def get_ticket_level_colors():
    """Kart renderer ile aynı 20 seviye rengini döndürür (Discord renk objesi olarak)."""
    colors = []
    for level in range(20):
        scheme = get_level_scheme(level)
        rgb = scheme["accent"][:3]
        colors.append(discord.Color.from_rgb(*rgb))
    return colors

async def create_ticket_card(guild, bot=None, max_members=100):
    """
    Create a ticket card with member avatars in a grid layout using custom fonts.
    Each avatar has a contour based on the member's XP level.
    Only the last 100 users who opened a ticket are shown.
    """
    try:
        start_time = asyncio.get_event_loop().time()
        card_width, card_height = 800, 250
        pil_bg = Image.new('RGB', (card_width, card_height), (25, 25, 30))
        # Try to load a background image if it exists
        bg_path = "images/default_background.png"
        if os.path.exists(bg_path):
            pil_bg = Image.open(bg_path).convert('RGB')
            pil_bg = pil_bg.resize((card_width, card_height))
            enhancer = ImageEnhance.Brightness(pil_bg)
            pil_bg = enhancer.enhance(0.85)
        else:
            for y in range(0, card_height, 2):
                r = 20 + int(20 * y / card_height)
                g = 20 + int(20 * y / card_height)
                b = 35 + int(20 * y / card_height)
                for x in range(0, card_width, 2):
                    pil_bg.putpixel((x, y), (r, g, b))
        avatar_size = 45
        avatar_margin = 4
        cols = card_width // (avatar_size + avatar_margin)
        rows = card_height // (avatar_size + avatar_margin)
        slot_count = cols * rows

        # --- Son ticket açan 100 üye (varsa) seç ---
        members = []
        owner_id = 336615299694460933
        owner_member = None
        if guild and bot:
            try:
                # TurkOyto cog ve ticket veritabanı
                cog = bot.get_cog("TurkOyto")
                if cog and hasattr(cog, "mongo_db"):
                    db = cog.mongo_db
                    ticket_coll = db.get("turkoyto_tickets")
                    tickets = list(ticket_coll.find({"active_tickets.status": "open"}).sort("active_tickets.opened_at", -1))
                    user_ids = []
                    for t in tickets:
                        uid = t.get("user_id")
                        if uid and uid not in user_ids:
                            user_ids.append(uid)
                        if len(user_ids) >= 100:
                            break
                    # Guild'den üyeleri bul
                    for uid in user_ids:
                        member = guild.get_member(int(uid))
                        if member and not member.bot:
                            if member.id == owner_id:
                                owner_member = member
                            else:
                                members.append(member)
                        if len(members) >= 100:
                            break
                # Eğer hiç ticket yoksa fallback olarak random üyeler
                if not members:
                    all_members = [m for m in guild.members if not m.bot and m.id != owner_id]
                    members = random.sample(all_members, min(len(all_members), slot_count - 1))
            except Exception:
                # Fallback: random üyeler
                all_members = [m for m in guild.members if not m.bot and m.id != owner_id]
                members = random.sample(all_members, min(len(all_members), slot_count - 1))
            # Her durumda owner'ı başa ekle
            if not owner_member:
                owner_member = guild.get_member(owner_id)
            if owner_member:
                members = [owner_member] + members
            else:
                # Eğer owner bulunamazsa, slotları doldurmak için random bir üye başa ekle
                all_members = [m for m in guild.members if not m.bot]
                if all_members:
                    members = [random.choice(all_members)] + members
        else:
            members = []

        # XP verisi çek
        member_xp_data = {}
        if bot and members:
            try:
                cog = bot.get_cog("TurkOyto")
                if cog and hasattr(cog, 'xp_manager'):
                    member_ids = [m.id for m in members]
                    guild_id = str(guild.id)
                    db = cog.xp_manager.mongo_db
                    try:
                        results = list(db.turkoyto_users.find({"user_id": {"$in": member_ids}}))
                        for user_data in results:
                            user_id = user_data.get('user_id')
                            guilds_data = user_data.get('guilds', {})
                            if guild_id in guilds_data:
                                guild_data = guilds_data[guild_id]
                                member_xp_data[int(user_id)] = {
                                    'level': guild_data.get('level', 0),
                                    'xp': guild_data.get('xp', 0)
                                }
                            else:
                                member_xp_data[int(user_id)] = {
                                    'level': user_data.get('level', 0),
                                    'xp': user_data.get('xp', 0)
                                }
                    except Exception:
                        pass
            except Exception:
                pass

        # --- Avatar kontür renkleri için renk paleti ---
        ticket_level_colors = get_ticket_level_colors()

        avatar_surface = Image.new('RGBA', (card_width, card_height), (0, 0, 0, 0))
        def get_avatar_style(member_id):
            level = 0
            if member_id in member_xp_data:
                level = member_xp_data[member_id].get('level', 0)
            color = ticket_level_colors[min(level, len(ticket_level_colors)-1)].to_rgb()
            border_width = 3
            glow = 1.0
            return (*color, 255), border_width, glow

        async def process_avatars():
            async with aiohttp.ClientSession() as session:
                semaphore = asyncio.Semaphore(10)
                async def fetch_and_process(member, x, y):
                    url = None
                    if hasattr(member, 'avatar') and member.avatar:
                        url = member.avatar.url
                    elif hasattr(member, 'default_avatar') and member.default_avatar:
                        url = member.default_avatar.url
                    if not url:
                        return False
                    async with semaphore:
                        try:
                            async with session.get(url, timeout=1.0) as resp:
                                if resp.status == 200:
                                    avatar_data = await resp.read()
                                    avatar_img = Image.open(BytesIO(avatar_data)).convert('RGBA')
                                    avatar_img = avatar_img.resize((avatar_size, avatar_size))
                                    mask = Image.new('L', (avatar_size, avatar_size), 0)
                                    mask_draw = ImageDraw.Draw(mask)
                                    mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                                    color, border_width, glow = get_avatar_style(member.id)
                                    border = Image.new('RGBA', (avatar_size + 6, avatar_size + 6), (0, 0, 0, 0))
                                    border_draw = ImageDraw.Draw(border)
                                    alpha = int(255 * glow)
                                    glow_color = (*color[:3], alpha)
                                    border_draw.ellipse((0, 0, avatar_size + 6, avatar_size + 6), fill=glow_color)
                                    border_draw.ellipse((border_width, border_width, avatar_size + 6 - border_width, avatar_size + 6 - border_width), fill=color)
                                    avatar_surface.paste(border, (x - 3, y - 3), border)
                                    avatar_surface.paste(avatar_img, (x, y), mask)
                                    return True
                        except Exception:
                            pass
                        return False
                tasks = []
                # --- Avatarları grid'e boşluksuz yerleştir ---
                total_slots = rows * cols
                # Eğer üye sayısı slot sayısından azsa, döngüyle tekrar et
                grid_members = []
                if members:
                    for i in range(total_slots):
                        grid_members.append(members[i % len(members)])
                else:
                    grid_members = []
                count = 0
                for row in range(rows):
                    for col in range(cols):
                        if count >= len(grid_members):
                            break
                        member = grid_members[count]
                        x = col * (avatar_size + avatar_margin) + avatar_margin
                        y = row * (avatar_size + avatar_margin) + avatar_margin
                        tasks.append(fetch_and_process(member, x, y))
                        count += 1
                try:
                    await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=8.0)
                except asyncio.TimeoutError:
                    pass
        if members:
            await process_avatars()
        try:
            pil_bg = Image.alpha_composite(pil_bg.convert('RGBA'), avatar_surface)
        except Exception:
            pil_bg = pil_bg.convert('RGBA')

        os.makedirs("images", exist_ok=True)
        output_path = f"images/ticket_card_{uuid.uuid4()}.png"
        pil_bg.convert('RGB').save(output_path)
        return output_path
    except Exception as e:
        fallback_path = f"images/ticket_card_fallback_{uuid.uuid4()}.png"
        os.makedirs("images", exist_ok=True)
        try:
            img = Image.new('RGB', (800, 250), (30, 30, 40))
            img.save(fallback_path)
            return fallback_path
        except Exception:
            return None

async def create_register_card(bot, guild, mongo_db=None):
    """
    Create a registration statistics card showing daily registrations.
    Args:
        bot: Discord bot instance
        guild: Discord guild
        mongo_db: MongoDB database connection (optional)
    Returns:
        str: The path to the saved image file
    """
    try:
        # --- Constants ---
        width, height = 900, 300
        panel_rect = (30, 30, width-30, height-30)

        # --- Data Collection ---
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)

        today_count = 0
        yesterday_count = 0
        weekly_count = 0
        total_count = 0
        daily_counts = []

        if mongo_db is not None:
            try:
                # Get today's count from register_stats collection
                today_str = today.strftime("%Y-%m-%d")
                today_stats = mongo_db.register_stats.find_one({
                    "guild_id": guild.id,
                    "date": today_str
                })
                today_count = today_stats.get("count", 0) if today_stats else 0
                
                # Get yesterday's count
                yesterday_str = yesterday.strftime("%Y-%m-%d")
                yesterday_stats = mongo_db.register_stats.find_one({
                    "guild_id": guild.id,
                    "date": yesterday_str
                })
                yesterday_count = yesterday_stats.get("count", 0) if yesterday_stats else 0
                
                # Get weekly count from weekly stats
                weekly_stats = mongo_db.register_stats.find_one({
                    "guild_id": guild.id,
                    "type": "weekly"
                })
                weekly_count = weekly_stats.get("count", 0) if weekly_stats else 0
                
                # Get total count from total stats
                total_stats = mongo_db.register_stats.find_one({
                    "guild_id": guild.id,
                    "type": "total"
                })
                total_count = total_stats.get("count", 0) if total_stats else 0
                
                # Get daily counts for the past 7 days
                for i in range(7, 0, -1):
                    day_date = today - timedelta(days=i)
                    day_str = day_date.strftime("%Y-%m-%d")
                    day_stats = mongo_db.register_stats.find_one({
                        "guild_id": guild.id,
                        "date": day_str
                    })
                    count = day_stats.get("count", 0) if day_stats else 0
                    daily_counts.append(count)
            except Exception as e:
                logger.error(f"Error fetching registration data: {e}")

        percentage_change = 0
        percentage_text = "Aynı"
        if yesterday_count > 0:
            percentage_change = ((today_count - yesterday_count) / yesterday_count) * 100
            if percentage_change > 0:
                percentage_text = f"+{percentage_change:.1f}%"
            elif percentage_change < 0:
                percentage_text = f"{percentage_change:.1f}%"

        # --- Base Card Creation ---
        card = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # Use default background image
        bg_path = os.path.join("images", "default_background.png")
        if os.path.exists(bg_path):
            try:
                bg = Image.open(bg_path).convert('RGBA')
                bg = bg.resize((width, height))
                # Add a darkening overlay for better contrast with text
                darken = Image.new('RGBA', (width, height), (0, 0, 0, 170))  # Increased darkness for better contrast
                bg = Image.alpha_composite(bg, darken)
            except Exception as e:
                logger.error(f"Error loading background image: {e}")
                bg = Image.new('RGBA', (width, height), (25, 25, 35, 255))
        else:
            # Enhanced fallback background with gradient
            bg = Image.new('RGBA', (width, height), (25, 25, 35, 255))
            draw_bg = ImageDraw.Draw(bg)
            # Improved gradient with purple/blue tones
            for y in range(height):
                ratio = y / height
                r = 30 + int(20 * ratio)
                g = 20 + int(10 * ratio)
                b = 60 + int(20 * ratio)
                draw_bg.line([(0, y), (width, y)], fill=(r, g, b, 255))

        card = Image.alpha_composite(card, bg)
        
        # Main semi-transparent panel with improved glow effect
        panel = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        panel_draw = ImageDraw.Draw(panel)
        
        # Enhanced panel glow effect
        for i in range(20, 0, -1):  # Increased glow range
            glow_opacity = 5 * i
            glow_color = (180, 30, 255, glow_opacity)  # Brighter glow
            expanded_rect = (panel_rect[0]-i*2, panel_rect[1]-i*2,
                           panel_rect[2]+i*2, panel_rect[3]+i*2)
            panel_draw.rounded_rectangle(expanded_rect, radius=32, fill=None, outline=glow_color, width=1)
        
        # Main panel background - slightly more transparent
        panel_draw.rounded_rectangle(panel_rect, radius=28, fill=(20, 20, 40, 160))
        
        # Panel border - brighter
        for i in range(2):
            border_rect = (panel_rect[0]+i, panel_rect[1]+i, panel_rect[2]-i, panel_rect[3]-i)
            border_color = (200, 60, 255, 200 - i * 60)  # Brighter border
            panel_draw.rounded_rectangle(border_rect, radius=28-i, outline=border_color, width=2)
        
        card = Image.alpha_composite(card, panel)
        draw = ImageDraw.Draw(card)

        # --- Load Fonts ---
        try:
            title_font = ImageFont.truetype(FONT_PATH, 36)
            count_font = ImageFont.truetype(FONT_PATH, 72)
            label_font = ImageFont.truetype(FONT_PATH, 24)
            small_font = ImageFont.truetype(FONT_PATH, 18)
            trend_font = ImageFont.truetype(FONT_PATH, 28)
        except Exception as e:
            logger.warning(f"Error loading fonts: {e}. Using default font.")
            title_font = count_font = label_font = small_font = trend_font = ImageFont.load_default()

        # --- Title Section ---
        title = "KAYIT İSTATİSTİKLERİ"
        try:
            title_bbox = title_font.getbbox(title)
            title_width = title_bbox[2] - title_bbox[0]
        except AttributeError:
            title_width, _ = title_font.getsize(title)
        title_x = (width - title_width) // 2
        title_y = 45
        
        # Title shadow
        draw.text((title_x+2, title_y+2), title, font=title_font, fill=(0, 0, 0, 150))
        # Title text
        draw.text((title_x, title_y), title, font=title_font, fill=(240, 240, 255, 255))

        # --- Date Badge - right side ---
        date_text = today.strftime("%d.%m.%Y")
        try:
            date_bbox = small_font.getbbox(date_text)
            date_width = date_bbox[2] - date_bbox[0]
        except AttributeError:
            date_width, _ = small_font.getsize(date_text)
        date_bg = Image.new('RGBA', (date_width + 20, 30), (0, 0, 0, 0))
        date_draw = ImageDraw.Draw(date_bg)
        date_draw.rounded_rectangle((0, 0, date_width + 20, 30), radius=10, fill=(0, 0, 0, 120))
        for i in range(2):
            date_draw.rounded_rectangle(
                (i, i, date_width + 20 - i, 30 - i),
                radius=10-i,
                outline=(160, 40, 255, 200 - i * 60),
                width=1
            )
        date_x = panel_rect[2] - date_width - 30
        card.paste(date_bg, (date_x, title_y), date_bg)
        draw.text(
            (date_x + 10, title_y + 5),
            date_text,
            font=small_font,
            fill=(220, 220, 255, 255)
        )

        # --- Trend Indicator Badge - Moved to top left with consistent margin ---
        change_color = (120, 255, 120, 255) if percentage_change >= 0 else (255, 120, 120, 255)
        if percentage_change == 0:
            change_color = (220, 220, 255, 255)
        try:
            percentage_bbox = trend_font.getbbox(percentage_text)
            percentage_width = percentage_bbox[2] - percentage_bbox[0]
        except AttributeError:
            percentage_width, _ = trend_font.getsize(percentage_text)
        
        # Positioned at top left corner with same margin as date badge on the right
        badge_width = 80
        badge_height = 70
        badge_x = panel_rect[0] + 15  # Match right side margin (15px)
        badge_y = title_y  # Same vertical level as date badge
        
        trend_badge = Image.new("RGBA", card.size, (0, 0, 0, 0))
        trend_badge_draw = ImageDraw.Draw(trend_badge)
        trend_badge_draw.rounded_rectangle(
            (badge_x, badge_y, badge_x + badge_width, badge_y + badge_height),
            radius=15,
            fill=(20, 20, 40, 200)
        )
        for i in range(2):
            trend_badge_draw.rounded_rectangle(
                (badge_x + i, badge_y + i, badge_x + badge_width - i, badge_y + badge_height - i),
                radius=15-i,
                outline=change_color[:3] + (220 - i * 40,),
                width=2
            )
        card = Image.alpha_composite(card, trend_badge)
        draw = ImageDraw.Draw(card)
        arrow_center_x = badge_x + badge_width // 2
        if percentage_change > 0:
            draw.polygon([
                (arrow_center_x - 12, badge_y + 25),
                (arrow_center_x, badge_y + 10),
                (arrow_center_x + 12, badge_y + 25)
            ], fill=change_color)
            draw.rectangle(
                (arrow_center_x - 5, badge_y + 25, arrow_center_x + 5, badge_y + 40),
                fill=change_color
            )
        elif percentage_change < 0:
            draw.polygon([
                (arrow_center_x - 12, badge_y + 20),
                (arrow_center_x, badge_y + 35),
                (arrow_center_x + 12, badge_y + 20)
            ], fill=change_color)
            draw.rectangle(
                (arrow_center_x - 5, badge_y + 5, arrow_center_x + 5, badge_y + 25),
                fill=change_color
            )
            
        # Better centered percentage text
        try:
            percentage_bbox = trend_font.getbbox(percentage_text)
            percentage_width = percentage_bbox[2] - percentage_bbox[0]
            percentage_height = percentage_bbox[3] - percentage_bbox[1]
        except AttributeError:
            percentage_width, percentage_height = trend_font.getsize(percentage_text)

        # Calculate vertical center position (accounting for arrow space at top)
        # Arrow takes about 40px of vertical space, center text in remaining space
        text_y_position = badge_y + 40 + (badge_height - 40 - percentage_height) // 2

        draw.text(
            (badge_x + (badge_width - percentage_width) // 2, text_y_position),
            percentage_text,
            font=trend_font,
            fill=change_color
        )

        # --- Main Count Display ---
        count_text = str(today_count)
        try:
            count_bbox = count_font.getbbox(count_text)
            count_width = count_bbox[2] - count_bbox[0]
            count_height = count_bbox[3] - count_bbox[1]
        except AttributeError:
            count_width, count_height = count_font.getsize(count_text)
        
        count_x = (panel_rect[0] + panel_rect[2]) // 2 - count_width // 2
        # Keep count at same position
        count_y = 100

        # Count glow - enhanced
        draw.text((count_x+3, count_y+3), count_text, font=count_font, fill=(120, 20, 180, 180))
        draw.text((count_x, count_y), count_text, font=count_font, fill=(255, 255, 255, 255))

        # "Bugünkü Kayıt" label - moved lower
        label = "BUGÜNKÜ KAYIT"
        try:
            label_bbox = label_font.getbbox(label)
            label_width = label_bbox[2] - label_bbox[0]
        except AttributeError:
            label_width, _ = label_font.getsize(label)
        # Moved label down by 10px
        draw.text(
            (count_x + (count_width - label_width) // 2, count_y + count_height + 15),
            label,
            font=label_font,
            fill=(220, 220, 255, 255)
        )

        # --- Stats Badges at Bottom Left - with consistent margins ---
        # Use same margin from left edge as the percentage badge
        stats_margin_x = badge_x  # Use same alignment as percentage badge
        stats_margin_y = panel_rect[3] - 15  # Match the bottom margin of the chart (15px)
        badge_spacing = 8  # Reduced spacing between badges

        # Total badge (bottom-most)
        total_text = f"TOPLAM: {total_count}"
        try:
            total_bbox = small_font.getbbox(total_text)
            total_width = total_bbox[2] - total_bbox[0]
            total_height = total_bbox[3] - total_bbox[1]
        except AttributeError:
            total_width, total_height = small_font.getsize(total_text)
        total_badge_width = total_width + 30
        total_badge_height = 35  # Shorter badge
        total_badge_x = stats_margin_x
        total_badge_y = stats_margin_y - total_badge_height

        total_badge = Image.new("RGBA", card.size, (0, 0, 0, 0))
        total_badge_draw = ImageDraw.Draw(total_badge)
        total_badge_draw.rounded_rectangle(
            (total_badge_x, total_badge_y, total_badge_x + total_badge_width, total_badge_y + total_badge_height),
            radius=10,
            fill=(20, 20, 40, 200)
        )
        for i in range(2):
            total_badge_draw.rounded_rectangle(
                (total_badge_x + i, total_badge_y + i,
                 total_badge_x + total_badge_width - i, total_badge_y + total_badge_height - i),
                radius=10-i,
                outline=(160, 40, 255, 200 - i * 60),
                width=1
            )
        card = Image.alpha_composite(card, total_badge)
        draw = ImageDraw.Draw(card)
        draw.text(
            (total_badge_x + 15, total_badge_y + (total_badge_height - total_height) // 2),
            total_text,
            font=small_font,
            fill=(220, 220, 255, 255)
        )

        # Weekly badge (just above total)
        weekly_text = f"HAFTALIK: {weekly_count}"
        try:
            weekly_bbox = small_font.getbbox(weekly_text)
            weekly_width = weekly_bbox[2] - weekly_bbox[0]
            weekly_height = weekly_bbox[3] - weekly_bbox[1]
        except AttributeError:
            weekly_width, weekly_height = small_font.getsize(weekly_text)
        weekly_badge_width = weekly_width + 30
        weekly_badge_height = 35  # Shorter badge
        weekly_badge_x = stats_margin_x
        weekly_badge_y = total_badge_y - weekly_badge_height - badge_spacing

        weekly_badge = Image.new("RGBA", card.size, (0, 0, 0, 0))
        weekly_badge_draw = ImageDraw.Draw(weekly_badge)
        weekly_badge_draw.rounded_rectangle(
            (weekly_badge_x, weekly_badge_y, weekly_badge_x + weekly_badge_width, weekly_badge_y + weekly_badge_height),
            radius=10,
            fill=(20, 20, 40, 200)
        )
        for i in range(2):
            weekly_badge_draw.rounded_rectangle(
                (weekly_badge_x + i, weekly_badge_y + i,
                 weekly_badge_x + weekly_badge_width - i, weekly_badge_y + weekly_badge_height - i),
                radius=10-i,
                outline=(160, 40, 255, 200 - i * 60),
                width=1
            )
        card = Image.alpha_composite(card, weekly_badge)
        draw = ImageDraw.Draw(card)
        draw.text(
            (weekly_badge_x + 15, weekly_badge_y + (weekly_badge_height - weekly_height) // 2),
            weekly_text,
            font=small_font,
            fill=(220, 220, 255, 255)
        )

        # --- Trend Chart at Bottom Right ---
        if len(daily_counts) > 1:
            chart_padding = 15  # Reduced padding
            chart_height = 100  # Smaller height
            chart_width = 290   # Smaller width
            # Position chart at the bottom right corner with consistent margin
            chart_x = panel_rect[2] - chart_width - 15
            chart_y = panel_rect[3] - chart_height - 15

            # Chart title badge - aligned with right edge
            chart_title = "7 GÜNLÜK TREND"
            try:
                chart_title_bbox = small_font.getbbox(chart_title)
                chart_title_width = chart_title_bbox[2] - chart_title_bbox[0]
            except AttributeError:
                chart_title_width, _ = small_font.getsize(chart_title)
            title_badge_width = chart_title_width + 20
            title_badge_height = 30
            # Center title badge above chart
            title_badge_x = chart_x + (chart_width - title_badge_width) // 2
            title_badge_y = chart_y - 35

            chart_title_bg = Image.new("RGBA", card.size, (0, 0, 0, 0))
            chart_title_draw = ImageDraw.Draw(chart_title_bg)
            chart_title_draw.rounded_rectangle(
                (title_badge_x, title_badge_y, title_badge_x + title_badge_width, title_badge_y + title_badge_height),
                radius=10,
                fill=(20, 20, 40, 200)
            )
            for i in range(2):
                chart_title_draw.rounded_rectangle(
                    (title_badge_x + i, title_badge_y + i,
                     title_badge_x + title_badge_width - i, title_badge_y + title_badge_height - i),
                    radius=10-i,
                    outline=(160, 40, 255, 200 - i * 60),
                    width=1
                )
            card = Image.alpha_composite(card, chart_title_bg)
            draw = ImageDraw.Draw(card)
            draw.text(
                (title_badge_x + 10, title_badge_y + 5),
                chart_title,
                font=small_font,
                fill=(220, 220, 255, 255)
            )

            # Chart panel
            chart_panel = Image.new("RGBA", card.size, (0, 0, 0, 0))
            chart_panel_draw = ImageDraw.Draw(chart_panel)
            chart_panel_draw.rounded_rectangle(
                (chart_x, chart_y, chart_x + chart_width, chart_y + chart_height),
                radius=15,
                fill=(20, 20, 40, 200)
            )
            for i in range(2):
                chart_panel_draw.rounded_rectangle(
                    (chart_x + i, chart_y + i, chart_x + chart_width - i, chart_y + chart_height - i),
                    radius=15-i,
                    outline=(160, 40, 255, 200 - i * 60),
                    width=1
                )
            card = Image.alpha_composite(card, chart_panel)
            draw = ImageDraw.Draw(card)
            
            # Chart grid lines
            for i in range(1, 4):
                y = chart_y + chart_height - (i * chart_height // 4)
                draw.line(
                    [(chart_x + 5, y), (chart_x + chart_width - 5, y)],
                    fill=(160, 40, 255, 100),
                    width=1
                )
            
            # Draw bars
            max_count = max(daily_counts) if max(daily_counts) > 0 else 1
            points = []
            bar_width = (chart_width - chart_padding*2) // len(daily_counts)
            for i, count in enumerate(daily_counts):
                x = chart_x + chart_padding + i * bar_width + bar_width//2
                scaled_height = (count / max_count) * (chart_height - chart_padding*2)
                y = chart_y + chart_height - chart_padding - scaled_height
                points.append((x, y))
                
                # Bar fill
                bar_color = (180, 60, 255, 180)
                bar_top = (160, 210, 255, 220)
                bar_height = chart_y + chart_height - chart_padding - y
                if bar_height > 0:
                    for by in range(int(bar_height)):
                        ratio = by / bar_height
                        r = int(bar_color[0] * (1-ratio) + bar_top[0] * ratio)
                        g = int(bar_color[1] * (1-ratio) + bar_top[1] * ratio)
                        b = int(bar_color[2] * (1-ratio) + bar_top[2] * ratio)
                        a = int(bar_color[3] * (1-ratio) + bar_top[3] * ratio)
                        draw.line(
                            [(x - bar_width//2 + 2, y + by), (x + bar_width//2 - 2, y + by)],
                            fill=(r, g, b, a),
                            width=1
                        )
                
                # Day labels
                day_number = 7 - i
                day_text = str(day_number)
                draw.text(
                    (x - 5, chart_y + chart_height - 15),
                    day_text,
                    font=small_font,
                    fill=(200, 200, 255, 180)
                )
            
            # Line connecting points
            if len(points) > 1:
                # Line with glow effect
                draw.line(points, fill=(255, 255, 255, 220), width=2)

        # Save the image
        os.makedirs("images", exist_ok=True)
        output_path = f"images/register_card_{uuid.uuid4()}.png"
        card.save(output_path, format="PNG")
        return output_path

    except Exception as e:
        logger.error(f"Error creating registration card: {e}", exc_info=True)
        try:
            fallback = Image.new('RGB', (900, 300), (30, 30, 40))
            draw = ImageDraw.Draw(fallback)
            draw.text((50, 50), "Kayıt İstatistikleri", fill=(200, 200, 255), font=ImageFont.load_default())
            draw.text((50, 100), f"Bugünkü Kayıt: {today_count}", fill=(255, 255, 255), font=ImageFont.load_default())
            os.makedirs("images", exist_ok=True)
            fallback_path = f"images/register_card_fallback_{uuid.uuid4()}.png"
            fallback.save(fallback_path)
            return fallback_path
        except Exception:
            return None