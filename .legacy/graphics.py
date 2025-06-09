import cv2
import numpy as np
from pathlib import Path
import os
import random
import uuid
import asyncio
from io import BytesIO
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import PIL.ImageFilter
import PIL.ImageEnhance
import math  # Move math import to the top level

def create_level_card(username, level, current_xp, required_xp, avatar=None):
    """
    Create a level card image showing user's level and XP progress.
    
    Args:
        username (str): User's name to display
        level (int): Current level number
        current_xp (int): Current XP points
        required_xp (int): XP required for next level
        avatar (numpy.ndarray, optional): User's avatar image as numpy array
        
    Returns:
        numpy.ndarray: The generated level card image
    """
    # Card dimensions
    card_width, card_height = 800, 250
    
    # Create a blank dark card with slight gradient
    card = np.zeros((card_height, card_width, 3), dtype=np.uint8)
    cv2.rectangle(card, (0, 0), (card_width, card_height), (40, 40, 45), -1)
    
    # Add subtle gradient background
    for i in range(card_height):
        alpha = i / card_height
        card[i, :] = (1 - alpha) * np.array([40, 40, 45]) + alpha * np.array([30, 30, 35])
    
    # Calculate progress percentage
    progress = min(current_xp / required_xp, 1.0) if required_xp > 0 else 1.0
    
    # Draw avatar placeholder or actual avatar if provided
    avatar_size = 150
    avatar_border = 5
    avatar_x, avatar_y = 50, 50
    
    if avatar is not None:
        # Resize avatar if needed
        avatar = cv2.resize(avatar, (avatar_size, avatar_size))
        
        # Create circle mask for round avatar
        mask = np.zeros((avatar_size, avatar_size), dtype=np.uint8)
        cv2.circle(mask, (avatar_size//2, avatar_size//2), avatar_size//2, 255, -1)
        
        # Apply mask to avatar
        masked_avatar = cv2.bitwise_and(avatar, avatar, mask=mask)
        
        # Draw circle border
        cv2.circle(card, (avatar_x + avatar_size//2, avatar_y + avatar_size//2), 
                  avatar_size//2 + avatar_border, (200, 200, 200), avatar_border)
        
        # Place avatar on card
        for i in range(avatar_size):
            for j in range(avatar_size):
                if mask[i, j] > 0:
                    card[avatar_y + i, avatar_x + j] = avatar[i, j]
    else:
        # Draw avatar placeholder
        cv2.circle(card, (avatar_x + avatar_size//2, avatar_y + avatar_size//2), 
                  avatar_size//2, (80, 80, 85), -1)
        cv2.circle(card, (avatar_x + avatar_size//2, avatar_y + avatar_size//2), 
                  avatar_size//2 + avatar_border, (200, 200, 200), avatar_border)
    
    # Add username
    username_x = avatar_x + avatar_size + 30
    username_y = avatar_y + 40
    cv2.putText(card, username, (username_x, username_y), cv2.FONT_HERSHEY_SIMPLEX, 
                1.2, (230, 230, 230), 2, cv2.LINE_AA)
    
    # Add level text
    level_text = f"Level {level}"
    level_x = username_x
    level_y = username_y + 40
    cv2.putText(card, level_text, (level_x, level_y), cv2.FONT_HERSHEY_SIMPLEX, 
                0.9, (200, 200, 200), 2, cv2.LINE_AA)
    
    # Add XP text
    xp_text = f"XP: {current_xp}/{required_xp}"
    xp_x = username_x
    xp_y = level_y + 40
    cv2.putText(card, xp_text, (xp_x, xp_y), cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, (180, 180, 180), 1, cv2.LINE_AA)
    
    # Draw progress bar background
    bar_x = username_x
    bar_y = xp_y + 30
    bar_width = 450
    bar_height = 25
    cv2.rectangle(card, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                 (70, 70, 75), -1)
    
    # Draw progress bar fill
    fill_width = int(bar_width * progress)
    cv2.rectangle(card, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), 
                 (65, 105, 225), -1)
    
    # Add percentage text on progress bar
    percent_text = f"{int(progress * 100)}%"
    text_size = cv2.getTextSize(percent_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
    text_x = bar_x + (bar_width - text_size[0]) // 2
    text_y = bar_y + bar_height - 6
    cv2.putText(card, percent_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, (240, 240, 240), 1, cv2.LINE_AA)
    
    return card

def save_level_card(card, user_id, output_dir="level_cards"):
    """
    Save the generated level card to a file.
    
    Args:
        card (numpy.ndarray): The level card image
        user_id (str): User ID to use in the filename
        output_dir (str): Directory to save the image
        
    Returns:
        str: Path to the saved image
    """
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save image
    filepath = os.path.join(output_dir, f"level_card_{user_id}.png")
    cv2.imwrite(filepath, card)
    
    return filepath

async def create_ticket_card(guild, bot=None, max_members=60):
    """
    Create a ticket card with member avatars in a grid layout using custom fonts.
    Each avatar has a contour based on the member's XP level.
    """
    try:
        # Start a timer for performance tracking
        start_time = asyncio.get_event_loop().time()
        
        # Card dimensions
        card_width, card_height = 800, 250
        
        # Create a PIL Image for background
        pil_bg = PIL.Image.new('RGB', (card_width, card_height), (25, 25, 30))
        
        # Add background pattern/effect - simplified for speed
        try:
            # Try to load a background image if it exists
            bg_path = "images/default_background.png"
            if os.path.exists(bg_path):
                pil_bg = PIL.Image.open(bg_path).convert('RGB')
                pil_bg = pil_bg.resize((card_width, card_height))
                
                # Simplified processing - less blur for speed
                enhancer = PIL.ImageEnhance.Brightness(pil_bg)
                pil_bg = enhancer.enhance(0.85)  # Slightly darker
            else:
                # Simplified gradient - much faster
                for y in range(0, card_height, 2):  # Process every 2nd pixel for speed
                    r = 20 + int(20 * y / card_height)
                    g = 20 + int(20 * y / card_height)
                    b = 35 + int(20 * y / card_height)
                    for x in range(0, card_width, 2):  # Process every 2nd pixel
                        pil_bg.putpixel((x, y), (r, g, b))
        except Exception as e:
            print(f"Using default background due to error: {e}")
        
        # Set much lower optimal member count to prevent timeouts
        OPTIMAL_MEMBER_COUNT = 25
        max_members = min(max_members, OPTIMAL_MEMBER_COUNT)
        
        # Get members - FIXED APPROACH using list instead of calling chunked() as function
        members = []
        try:
            # Properly check if we're in a guild with members
            if guild and hasattr(guild, 'members') and guild.members:
                # Get a sample of non-bot members
                all_members = [m for m in guild.members if not m.bot]
                
                # Take a random sample to avoid always getting the same members
                if len(all_members) > max_members:
                    members = random.sample(all_members, max_members)
                else:
                    members = all_members
                    
                # Check time to avoid hanging
                if asyncio.get_event_loop().time() - start_time > 2.0:
                    # Already taking too long, reduce member count further
                    if len(members) > 10:
                        members = members[:10]
            else:
                print("Guild has no members or is not available")
        except Exception as e:
            print(f"Error getting members: {e}, falling back to basic mode")
            try:
                # Last resort: just get a few members if possible
                if guild and hasattr(guild, 'members'):
                    members = [m for m in guild.members if not m.bot][:10]
            except:
                members = []
        
        # Faster XP data fetching - with timeout protection - UPDATED FOR CORRECT SCHEMA
        member_xp_data = {}
        xp_fetch_complete = False
        
        if bot and members:
            try:
                cog = bot.get_cog("TurkOyto")
                if cog and hasattr(cog, 'xp_manager'):
                    member_ids = [m.id for m in members]
                    guild_id = str(guild.id)  # Convert to string to match document keys
                    
                    # Try to get mongo client with async support
                    if hasattr(cog.xp_manager, 'mongo_db'):
                        try:
                            from utils.db import AsyncMongoClient
                            
                            # Check if we can use async MongoDB
                            if isinstance(cog.xp_manager.mongo_db, AsyncMongoClient):
                                # Use the async client directly - much faster
                                async_db = cog.xp_manager.mongo_db
                                
                                # UPDATED: Use the correct schema query - user_id only, no guild_id filter
                                results = await asyncio.wait_for(
                                    async_db.find_many("turkoyto_users", {"user_id": {"$in": member_ids}}),
                                    timeout=2.0
                                )
                                
                                # UPDATED: Parse the nested guilds structure
                                for user_data in results:
                                    user_id = user_data.get('user_id')
                                    guilds_data = user_data.get('guilds', {})
                                    
                                    # Get this guild's data if it exists
                                    if guild_id in guilds_data:
                                        guild_data = guilds_data[guild_id]
                                        member_xp_data[int(user_id)] = {
                                            'level': guild_data.get('level', 0),
                                            'xp': guild_data.get('xp', 0)
                                        }
                                xp_fetch_complete = True
                            else:
                                # Use optimized find query with standard MongoDB
                                db = cog.xp_manager.mongo_db
                                try:
                                    # Use a background task with timeout to avoid blocking
                                    async def fetch_xp_data():
                                        # UPDATED: Query with correct schema
                                        results = list(db.turkoyto_users.find(
                                            {"user_id": {"$in": member_ids}}
                                        ))
                                        return results
                                    
                                    # Execute with timeout
                                    results = await asyncio.wait_for(
                                        asyncio.create_task(fetch_xp_data()),
                                        timeout=2.0
                                    )
                                    
                                    # UPDATED: Parse using the correct structure
                                    for user_data in results:
                                        user_id = user_data.get('user_id')
                                        guilds_data = user_data.get('guilds', {})
                                        
                                        # Get this guild's data if it exists
                                        if guild_id in guilds_data:
                                            guild_data = guilds_data[guild_id]
                                            member_xp_data[int(user_id)] = {
                                                'level': guild_data.get('level', 0),
                                                'xp': guild_data.get('xp', 0)
                                            }
                                    xp_fetch_complete = True
                                except (asyncio.TimeoutError, Exception) as e:
                                    print(f"DB query timed out or failed: {e}, continuing without XP data")
                        except ImportError:
                            print("AsyncMongoClient not available, using standard approach")
                            db = cog.xp_manager.mongo_db
                            try:
                                # UPDATED: Query with correct schema
                                results = list(db.turkoyto_users.find(
                                    {"user_id": {"$in": member_ids}}
                                ))
                                
                                # UPDATED: Parse using the correct structure
                                for user_data in results:
                                    user_id = user_data.get('user_id')
                                    guilds_data = user_data.get('guilds', {})
                                    
                                    # Get this guild's data if it exists
                                    if guild_id in guilds_data:
                                        guild_data = guilds_data[guild_id]
                                        member_xp_data[int(user_id)] = {
                                            'level': guild_data.get('level', 0),
                                            'xp': guild_data.get('xp', 0)
                                        }
                                xp_fetch_complete = True
                            except Exception as e:
                                print(f"Error fetching XP data: {e}")
            except Exception as e:
                print(f"Error accessing XP data: {e}")
        
        # Shuffle members for variety
        if members:
            random.shuffle(members)
        
        # Calculate optimal avatar size and grid layout
        avatar_size = 45  # Base avatar size
        avatar_margin = 4  # Space between avatars
        
        # Grid dimensions
        cols = card_width // (avatar_size + avatar_margin)
        rows = card_height // (avatar_size + avatar_margin)
        
        # Create a temporary surface for drawing avatars
        avatar_surface = PIL.Image.new('RGBA', (card_width, card_height), (0, 0, 0, 0))
        
        # Fast color selection function - simplified for speed
        def get_avatar_style(member_id):
            level = 0
            if member_id in member_xp_data:
                level = member_xp_data[member_id].get('level', 0)
            
            # Simplified color and glow mapping
            if level >= 50:  # Legendary
                return (255, 215, 0, 255), 3, 1.0  # Color, border width, glow
            elif level >= 30:  # Rare
                return (192, 192, 192, 255), 3, 0.8
            elif level >= 20:  # Uncommon+
                return (150, 75, 0, 255), 2, 0.7
            elif level >= 10:  # Uncommon
                return (0, 191, 255, 255), 2, 0.6
            elif level >= 5:  # Common+
                return (50, 205, 50, 255), 2, 0.5
            else:  # Common
                return (65, 105, 225, 255), 1, 0.3
        
        # Optimized avatar processing with concurrency limit and shared session
        async def process_avatars():
            # Create a shared aiohttp session for all requests
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Use a semaphore to limit concurrent requests
                semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests
                
                async def fetch_and_process(member, x, y):
                    if not member.avatar:
                        return False
                    
                    async with semaphore:
                        try:
                            # Fast avatar fetching with timeout
                            url = member.avatar.url
                            async with session.get(url, timeout=1.0) as resp:
                                if resp.status == 200:
                                    avatar_data = await resp.read()
                                    
                                    # Process avatar
                                    avatar_img = PIL.Image.open(BytesIO(avatar_data)).convert('RGBA')
                                    avatar_img = avatar_img.resize((avatar_size, avatar_size))
                                    
                                    # Create mask
                                    mask = PIL.Image.new('L', (avatar_size, avatar_size), 0)
                                    mask_draw = PIL.ImageDraw.Draw(mask)
                                    mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                                    
                                    # Get color and effects - simpler for speed
                                    color, border_width, glow = get_avatar_style(member.id)
                                    
                                    # Create border
                                    border = PIL.Image.new('RGBA', (avatar_size + 6, avatar_size + 6), (0, 0, 0, 0))
                                    border_draw = PIL.ImageDraw.Draw(border)
                                    
                                    # Draw border with glow
                                    alpha = int(255 * glow)
                                    glow_color = (*color[:3], alpha)
                                    border_draw.ellipse((0, 0, avatar_size + 6, avatar_size + 6), fill=glow_color)
                                    border_draw.ellipse((border_width, border_width, 
                                                        avatar_size + 6 - border_width, 
                                                        avatar_size + 6 - border_width), 
                                                      fill=color)
                                    
                                    # Add to the surface
                                    avatar_surface.paste(border, (x - 3, y - 3), border)
                                    avatar_surface.paste(avatar_img, (x, y), mask)
                                    return True
                        except Exception as e:
                            print(f"Error processing avatar for {member.name}: {e}")
                        return False
                
                # Create tasks for all avatars
                tasks = []
                count = 0
                for row in range(rows):
                    for col in range(cols):
                        if count >= len(members):
                            break
                            
                        member = members[count]
                        x = col * (avatar_size + avatar_margin) + avatar_margin
                        y = row * (avatar_size + avatar_margin) + avatar_margin
                        
                        tasks.append(fetch_and_process(member, x, y))
                        count += 1
                
                # Run all tasks concurrently with a global timeout
                try:
                    return await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=4.0  # Short timeout to prevent hanging
                    )
                except asyncio.TimeoutError:
                    print("Avatar processing timed out")
                    return []
        
        # Process avatars
        if members:
            await process_avatars()
        
        # Create the rest of the card (faster version)
        # Composite the avatar surface with the background
        try:
            pil_bg = PIL.Image.alpha_composite(pil_bg.convert('RGBA'), avatar_surface)
        except Exception as e:
            print(f"Error compositing images: {e}")
            pil_bg = pil_bg.convert('RGBA')
        
        # Add text overlay
        overlay = PIL.Image.new('RGBA', (card_width, 60), (0, 0, 0, 180))
        pil_bg.paste(overlay, (0, (card_height - 60) // 2), overlay)
        
        # Add text - simplified font handling for speed
        draw = PIL.ImageDraw.Draw(pil_bg)
        
        # Try to load a font quickly with few fallbacks
        title_font = None
        try:
            font_paths = [
                "fonts/GothamNarrow-Bold.otf",
                "C:/Windows/Fonts/Arial.ttf",
                "C:/Windows/Fonts/Segoe UI Bold.ttf"
            ]
            for path in font_paths:
                if os.path.exists(path):
                    title_font = PIL.ImageFont.truetype(path, 30)
                    break
        except Exception as e:
            print(f"Error loading font: {e}")
            
        # Fallback to default if needed
        if not title_font:
            title_font = PIL.ImageFont.load_default()
            
        # Add title
        title_text = "Türk Oyuncu Topluluğu"
        subtitle_text = "Destek Sistemi"
        
        # Simplified text positioning
        title_x = 250
        title_y = 100
        
        # Draw text
        draw.text((title_x+2, title_y+2), title_text, font=title_font, fill=(0, 0, 0, 180))
        draw.text((title_x, title_y), title_text, font=title_font, fill=(255, 255, 255, 255))
        draw.text((title_x+50, title_y+40), subtitle_text, font=title_font, fill=(200, 200, 200, 255))
        
        # Save image - ensure directory exists
        os.makedirs("images", exist_ok=True)
        output_path = f"images/ticket_card_{uuid.uuid4()}.png"
        pil_bg.convert('RGB').save(output_path)
        
        return output_path
    
    except Exception as e:
        print(f"Error in create_ticket_card: {e}")
        # Simple fallback that doesn't depend on complex operations
        fallback_path = f"images/ticket_card_fallback_{uuid.uuid4()}.png"
        os.makedirs("images", exist_ok=True)
        
        try:
            # Create minimal image
            img = PIL.Image.new('RGB', (800, 250), (30, 30, 40))
            draw = PIL.ImageDraw.Draw(img)
            font = PIL.ImageFont.load_default()
            draw.text((250, 100), "Türk Oyuncu Topluluğu", font=font, fill=(255, 255, 255))
            draw.text((300, 130), "Destek Sistemi", font=font, fill=(200, 200, 200))
            img.save(fallback_path)
            return fallback_path
        except Exception as fallback_error:
            print(f"Even fallback image creation failed: {fallback_error}")
            return None
