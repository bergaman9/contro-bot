

import discord, asyncio, os, json, logging
from ordinal import ordinal
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance
from io import BytesIO
import requests
import pymongo
import base64
import random
import io
from typing import Optional, List, Union

# Updated imports for new organization
from utils.core.formatting import create_embed, hex_to_int
from utils.database.connection import initialize_mongodb 
from utils.greeting.imaging import download_background

# Import new view components from updated paths
from utils.greeting.welcomer.config_view import WelcomerConfigView, ByeByeConfigView
from utils.greeting.welcomer.image_utils import (
    circle_avatar, add_text_with_outline, 
    apply_blur_background, get_predefined_backgrounds,
    resize_and_crop_image
)

logger = logging.getLogger('welcomer')

class Welcomer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.name = "hidden"
        self.mongo_db = initialize_mongodb()
        self.predefined_backgrounds = get_predefined_backgrounds()
        
        # Create directories for temporary files if they don't exist
        os.makedirs("data/Backgrounds", exist_ok=True)
        os.makedirs("data/Temp", exist_ok=True)
        os.makedirs("data/fonts", exist_ok=True)
        
        # Ensure default background exists
        self.ensure_default_background()
        
        logger.info("Welcomer cog initialized and event listeners registered")

    def ensure_default_background(self):
        """Ensure default background exists"""
        default_bg = os.path.join("data", "Backgrounds", "default_background.png")
        if not os.path.exists(default_bg):
            try:
                # Create a simple gradient background
                img = Image.new("RGB", (1024, 500), (32, 16, 64))
                img.save(default_bg)
                logger.info(f"Created default background: {default_bg}")
            except Exception as e:
                logger.error(f"Failed to create default background: {e}")

    async def create_welcome_image(self, member, background, config):
        """Creates a welcome image with advanced customization options"""
        try:
            background_image = None
            
            # Handle different background types
            if isinstance(background, str):
                # If it's a URL or filepath
                if background.startswith(('http://', 'https://')):
                    # Download from URL
                    try:
                        response = requests.get(background, timeout=10)
                        response.raise_for_status()
                        background_image = Image.open(BytesIO(response.content)).convert("RGBA")
                    except Exception as e:
                        logger.error(f"Failed to download background from URL: {e}")
                        # Fallback to default
                        default_bg = os.path.join("data", "Backgrounds", "default_background.png")
                        background_image = Image.open(default_bg).convert("RGBA")
                else:
                    # Local file path
                    if os.path.exists(background):
                        background_image = Image.open(background).convert("RGBA")
                    else:
                        # Fallback to default
                        default_bg = os.path.join("data", "Backgrounds", "default_background.png")
                        background_image = Image.open(default_bg).convert("RGBA")
            elif isinstance(background, bytes):
                # If it's binary data from database
                background_image = Image.open(BytesIO(background)).convert("RGBA")
            else:
                # Fallback to default
                default_bg = os.path.join("data", "Backgrounds", "default_background.png")
                background_image = Image.open(default_bg).convert("RGBA")
            
            # Resize the background
            background_image = resize_and_crop_image(background_image, (1024, 500))
            
            # Apply background effects if configured
            if config.get("blur_background", False):
                background_image = apply_blur_background(background_image, blur_amount=config.get("blur_amount", 5))
            
            # Get user avatar
            try:
                asset = member.avatar.with_size(1024) if member.avatar else self.bot.user.avatar.with_size(1024)
                data = BytesIO(await asset.read())
                pfp = Image.open(data).convert("RGBA")
            except Exception as e:
                logger.error(f"Failed to get avatar: {e}")
                # Create a default avatar
                pfp = Image.new("RGBA", (1024, 1024), (128, 128, 128, 255))
            
            # Process avatar
            avatar_size = config.get("avatar_size", 226)
            pfp = circle_avatar(pfp, size=(avatar_size, avatar_size))
            
            # Prepare text
            welcome_text = config.get("welcome_text", "HOŞ GELDİN!")
            member_text = f"{member.name}"
            if hasattr(member, "discriminator") and member.discriminator != "0":
                member_text += f"#{member.discriminator}"
            
            # Define colors and styles
            fill_color = config.get("fill", "#FFFFFF")
            outline_color = config.get("outline_color", "#000000")
            shadow = config.get("text_shadow", False)
            
            # Create a drawing canvas
            draw = ImageDraw.Draw(background_image)
            
            # Load fonts with configurable sizes
            welcome_font_size = config.get("welcome_font_size", 100)
            member_font_size = config.get("member_font_size", 42)
            
            try:
                welcome_font = ImageFont.truetype("data/fonts/GothamNarrow-Bold.otf", welcome_font_size)
                member_font = ImageFont.truetype("data/fonts/GothamNarrow-Bold.otf", member_font_size)
            except Exception as e:
                logger.warning(f"Failed to load custom fonts, using default: {e}")
                try:
                    welcome_font = ImageFont.load_default()
                    member_font = ImageFont.load_default()
                except Exception:
                    # Create very basic font
                    welcome_font = ImageFont.load_default()
                    member_font = ImageFont.load_default()
            
            # Canvas dimensions
            W, H = (1024, 500)
            
            # Position configurations
            welcome_y = config.get("welcome_y", 295)
            member_y = config.get("member_y", 390)
            avatar_y = config.get("avatar_y", 50)
            
            # Draw welcome text with optional effects
            add_text_with_outline(
                draw, welcome_text, welcome_font, 
                (W // 2, welcome_y), fill_color, outline_color,
                use_outline=config.get("text_outline", False),
                shadow=shadow,
                center=True
            )
            
            # Draw member text with optional effects
            add_text_with_outline(
                draw, member_text, member_font, 
                (W // 2, member_y), fill_color, outline_color,
                use_outline=config.get("text_outline", False),
                shadow=shadow,
                center=True
            )
            
            # Place avatar
            background_image.paste(pfp, (int((W - avatar_size) / 2), avatar_y), pfp)
            
            # Save the result
            filename = f"data/Temp/welcome_{member.id}.png"
            background_image.save(filename, format="PNG")
            return filename
            
        except Exception as e:
            logger.error(f"Error in create_welcome_image: {e}", exc_info=True)
            # Return None so the calling function can handle the fallback
            return None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Event listener for when a member joins the server"""
        logger.info(f"Member joined: {member.name} in {member.guild.name}")
        try:
            # Get guild configuration
            guild_config = await self.get_guild_config(member.guild.id)
            if not guild_config:
                logger.warning(f"No welcomer configuration found for guild {member.guild.name}")
                return
            
            # Check if welcomer is enabled
            if not guild_config.get("enabled", True):  # Default to enabled
                logger.info(f"Welcomer disabled for guild {member.guild.name}")
                return
                
            # Get welcome channel - try both field names for compatibility
            channel_id = guild_config.get("channel_id") or guild_config.get("welcome_channel_id")
            if not channel_id:
                logger.warning(f"Welcome channel not configured for guild {member.guild.name}")
                return
                
            channel = member.guild.get_channel(int(channel_id))
            if not channel:
                logger.warning(f"Welcome channel {channel_id} not found in guild {member.guild.name}")
                return
            
            logger.info(f"Found welcome channel {channel.name} ({channel_id}) for {member.guild.name}")
                
            # Send welcome message
            await self.send_welcome_message(member, channel, guild_config)
            
        except Exception as e:
            logger.error(f"Error in on_member_join event: {e}", exc_info=True)

    async def get_guild_config(self, guild_id):
        """Get welcome configuration from database"""
        try:
            # Get welcome configuration from database
            guild_config = self.mongo_db['welcomer'].find_one({"guild_id": str(guild_id)})
            if guild_config is None:
                logger.warning(f"No welcomer config found for guild {guild_id}")
                return {}
            
            return guild_config
        except Exception as e:
            logger.error(f"Error retrieving guild config for {guild_id}: {e}")
            return {}

    async def send_welcome_message(self, member, channel, guild_config):
        """Send welcome message with image to channel"""
        try:
            # Format welcome message with safe fallback
            description_template = guild_config.get("description", "Welcome {mention} to {server}! You are our {member_count}th member.")
            try:
                description = description_template.format(
                    mention=member.mention, name=member.name,
                    member_count=member.guild.member_count, server=member.guild.name
                )
            except Exception as e:
                logger.error(f"Error formatting welcome message: {e}")
                description = f"Welcome {member.mention} to {member.guild.name}! You are our {member.guild.member_count}th member."
            
            # Get color and background configuration with safe defaults
            color_value = guild_config.get("color", 0x5865F2)  # Discord Blue as default
            
            # Handle different color formats (hex string, int, etc.)
            if isinstance(color_value, str):
                try:
                    if color_value.startswith('#'):
                        color_value = int(color_value[1:], 16)
                    else:
                        color_value = int(color_value, 16)
                except ValueError:
                    color_value = 0x5865F2  # Default to Discord Blue
            
            color = discord.Color(color_value)
            background = None
            
            # Handle custom uploaded background
            if "background_data" in guild_config and guild_config["background_data"]:
                try:
                    # Decode base64 if it's stored that way
                    if isinstance(guild_config["background_data"], str):
                        background = base64.b64decode(guild_config["background_data"])
                    else:
                        background = guild_config["background_data"]
                except Exception as e:
                    logger.error(f"Failed to decode background data: {e}")
                    background = os.path.join("data", "Backgrounds", "default_background.png")
            else:
                # Use URL or default background
                background = guild_config.get("background_url", os.path.join("data", "Backgrounds", "default_background.png"))

            # Create embed first (fallback)
            embed = discord.Embed(
                title=guild_config.get("welcome_text", "HOŞ GELDİN!"), 
                description=description, 
                color=color
            )

            # Try to create and send welcome image
            try:
                filename = await self.create_welcome_image(member, background, guild_config)
                
                if filename and os.path.exists(filename):
                    # Send with image
                    try:
                        file = discord.File(filename, filename=f"welcome_{member.id}.png")
                        embed.set_image(url=f"attachment://welcome_{member.id}.png")
                        await channel.send(file=file, embed=embed)
                        logger.info(f"Welcome image sent successfully for {member.name} in {member.guild.name}")
                    except Exception as e:
                        logger.error(f"Failed to send welcome image file: {e}")
                        # Send embed without image
                        await channel.send(embed=embed)
                    finally:
                        # Clean up temporary file
                        try:
                            if filename and os.path.exists(filename):
                                os.remove(filename)
                        except Exception as e:
                            logger.error(f"Failed to remove temporary file: {e}")
                else:
                    # Send embed without image
                    await channel.send(embed=embed)
                    logger.warning(f"Welcome image could not be created for {member.name}, sent embed only")
                    
            except Exception as e:
                logger.error(f"Complete failure in welcome message: {e}")
                # Last resort - just send the embed
                try:
                    await channel.send(embed=embed)
                except Exception as e2:
                    logger.error(f"Failed to send even basic welcome message: {e2}")
        except Exception as e:
            logger.error(f"Error in send_welcome_message: {e}", exc_info=True)


class ByeBye(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        self.welcomer = bot.get_cog("Welcomer")  # Get reference to Welcomer cog for image utilities
        self.predefined_backgrounds = get_predefined_backgrounds("byebye")
        
        logger.info("ByeBye cog initialized and event listeners registered")
        
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Event listener for when a member leaves the server"""
        logger.info(f"Member left: {member.name} in {member.guild.name}")
        try:
            # Get guild configuration
            guild_config = await self.get_guild_config(member.guild.id)
            if not guild_config:
                logger.warning(f"No byebye configuration found for guild {member.guild.name}")
                return
            
            # Check if byebye is enabled
            if not guild_config.get("enabled", True):  # Default to enabled
                logger.info(f"ByeBye disabled for guild {member.guild.name}")
                return
                
            # Get goodbye channel - try both field names for compatibility
            channel_id = guild_config.get("channel_id") or guild_config.get("byebye_channel_id")
            if not channel_id:
                logger.warning(f"Goodbye channel not configured for guild {member.guild.name}")
                return
                
            channel = member.guild.get_channel(int(channel_id))
            if not channel:
                logger.warning(f"Goodbye channel {channel_id} not found in guild {member.guild.name}")
                return
            
            logger.info(f"Found goodbye channel {channel.name} ({channel_id}) for {member.guild.name}")
                
            # Send goodbye message
            await self.send_goodbye_message(member, channel, guild_config)
            
        except Exception as e:
            logger.error(f"Error in on_member_remove event: {e}", exc_info=True)

    async def get_guild_config(self, guild_id):
        """Get goodbye configuration from database"""
        try:
            # Get goodbye configuration from database
            guild_config = self.mongo_db['byebye'].find_one({"guild_id": str(guild_id)})
            if guild_config is None:
                logger.warning(f"No byebye config found for guild {guild_id}")
                return {}
            
            return guild_config
        except Exception as e:
            logger.error(f"Error retrieving guild config for {guild_id}: {e}")
            return {}

    async def send_goodbye_message(self, member, channel, guild_config):
        """Send goodbye message with image to channel"""
        try:
            # Format goodbye message with safe fallback
            description_template = guild_config.get("description", "{name} has left {server}. We now have {member_count} members.")
            try:
                description = description_template.format(
                    name=member.name, member_count=member.guild.member_count, 
                    server=member.guild.name
                )
            except Exception as e:
                logger.error(f"Error formatting goodbye message: {e}")
                description = f"{member.name} has left the server. We now have {member.guild.member_count} members."

            # Get color and background configuration with safe defaults
            color_value = guild_config.get("color", 0x5865F2)  # Discord Blue as default
            
            # Handle different color formats (hex string, int, etc.)
            if isinstance(color_value, str):
                try:
                    if color_value.startswith('#'):
                        color_value = int(color_value[1:], 16)
                    else:
                        color_value = int(color_value, 16)
                except ValueError:
                    color_value = 0x5865F2  # Default to Discord Blue
            
            color = discord.Color(color_value)
            background = None
            
            # Handle custom uploaded background
            if "background_data" in guild_config and guild_config["background_data"]:
                try:
                    # Decode base64 if it's stored that way
                    if isinstance(guild_config["background_data"], str):
                        background = base64.b64decode(guild_config["background_data"])
                    else:
                        background = guild_config["background_data"]
                except Exception as e:
                    logger.error(f"Failed to decode background data: {e}")
                    background = os.path.join("data", "Backgrounds", "default_background.png")
            else:
                # Use URL or default background
                background = guild_config.get("background_url", os.path.join("data", "Backgrounds", "default_background.png"))
                
            # Create embed first (fallback)
            embed = discord.Embed(
                title=guild_config.get("byebye_text", "GÜLE GÜLE!"), 
                description=description, 
                color=color
            )

            # Try to create and send goodbye image
            try:
                filename = await self.create_goodbye_image(member, background, guild_config)
                
                if filename and os.path.exists(filename):
                    # Send with image
                    try:
                        file = discord.File(filename, filename=f"goodbye_{member.id}.png")
                        embed.set_image(url=f"attachment://goodbye_{member.id}.png")
                        await channel.send(file=file, embed=embed)
                        logger.info(f"Goodbye image sent successfully for {member.name} in {member.guild.name}")
                    except Exception as e:
                        logger.error(f"Failed to send goodbye image file: {e}")
                        # Send embed without image
                        await channel.send(embed=embed)
                    finally:
                        # Clean up temporary file
                        try:
                            if filename and os.path.exists(filename):
                                os.remove(filename)
                        except Exception as e:
                            logger.error(f"Failed to remove temporary file: {e}")
                else:
                    # Send embed without image
                    await channel.send(embed=embed)
                    logger.warning(f"Goodbye image could not be created for {member.name}, sent embed only")
                    
            except Exception as e:
                logger.error(f"Complete failure in goodbye message: {e}")
                # Last resort - just send the embed
                try:
                    await channel.send(embed=embed)
                except Exception as e2:
                    logger.error(f"Failed to send even basic goodbye message: {e2}")
        except Exception as e:
            logger.error(f"Error in send_goodbye_message: {e}", exc_info=True)

    async def create_goodbye_image(self, member, background, config):
        """Creates a goodbye image with advanced customization options"""
        try:
            # Get the Welcomer cog for its image creation functionality
            welcomer_cog = self.bot.get_cog("Welcomer")
            if not welcomer_cog:
                logger.error("Welcomer cog not found for byebye image creation")
                return None
            
            # Copy and update the config for goodbye message
            byebye_config = config.copy()
            byebye_config["welcome_text"] = config.get("byebye_text", "GÜLE GÜLE!")
            
            # Use the Welcomer's create_welcome_image method
            return await welcomer_cog.create_welcome_image(member, background, byebye_config)
        except Exception as e:
            logger.error(f"Error in create_goodbye_image: {e}")
            return None

async def setup(bot):
    # Use async setup function for modern discord.py
    welcomer = Welcomer(bot)
    byebye = ByeBye(bot)
    await bot.add_cog(welcomer)
    await bot.add_cog(byebye)
    return welcomer  # Return at least one cog to avoid NoneType error
