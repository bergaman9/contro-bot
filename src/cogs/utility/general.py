import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Union, Dict, Any
import os
import json
import time
import asyncio
import aiohttp
import datetime
from datetime import datetime, timedelta
import psutil
import platform
import requests
import math
import shlex
import re
import traceback
import io
import shutil
import logging
from PIL import Image
from io import BytesIO

# Use consistent import paths
from src.utils.core.formatting import create_embed, hex_to_int, calculate_how_long_ago_member_joined, calculate_how_long_ago_member_created
from src.utils.database.connection import initialize_mongodb, is_db_available
from src.utils.core.db import get_document, get_documents, update_document
from src.utils.database.utility_stats import increment_utility_stat

# Configure logger
logger = logging.getLogger('utility')
from src.utils.core.class_utils import Paginator
from src.utils.imaging import circle, download_background
from src.utils.core.content_loader import load_content

# Standart embed formatları - Contro Bot tarzında
def contro_embed(title=None, description=None, color=None, footer=None, author=None, thumbnail=None, image=None, timestamp=True):
    """Create a standardized embed for Contro Bot with consistent styling"""
    # Default color - Contro's signature color
    if color is None:
        color = discord.Color.from_rgb(114, 137, 218)  # Discord blurple
        
    # Create embed with description
    embed = discord.Embed(description=description, color=color)
    
    # Add title if provided
    if title:
        embed.title = title
        
    # Add footer if provided or use default
    if footer:
        embed.set_footer(text=footer)
    
    # Set author if provided
    if author:
        if isinstance(author, discord.Member) or isinstance(author, discord.User):
            name = author.name
            icon_url = author.display_avatar.url
            embed.set_author(name=name, icon_url=icon_url)
        elif isinstance(author, dict):
            embed.set_author(**author)
        else:
            embed.set_author(name=str(author))
    
    # Set thumbnail if provided
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
        
    # Set image if provided
    if image:
        embed.set_image(url=image)
        
    # Add timestamp if requested
    if timestamp:
        embed.timestamp = datetime.datetime.now()
        
    return embed
    
# Define create_embed function as backup
if 'create_embed' not in locals():
    def create_embed(description, color=discord.Color.blue()):
        """Create a simple embed with description and color"""
        return discord.Embed(description=description, color=color)

def generate_members_of_role_embeds(role, members):
    """Generate embeds for members of a role"""
    embeds = []
    members_per_page = 10
    
    for i in range(0, len(members), members_per_page):
        page_members = members[i:i + members_per_page]
        embed = discord.Embed(
            title=f"Members with role {role.name}",
            color=role.color,
            description="\n".join([f"{member.mention} - {member.name}" for member in page_members])
        )
        embed.set_footer(text=f"Page {i//members_per_page + 1}/{(len(members)-1)//members_per_page + 1}")
        embeds.append(embed)
    
    return embeds

class IdeaModal(discord.ui.Modal, title='Share Idea'):
    idea = discord.ui.TextInput(label='Your idea about bot.', placeholder="Write your idea here.", min_length=10, max_length=1000, row=3, custom_id="idea_text")

class SupportView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Support Server", url="https://discord.gg/ynGqvsYxah"))
        self.add_item(discord.ui.Button(label="Invite Bot", url=f"https://discord.com/api/oauth2/authorize?client_id={bot.application_id}&permissions=8&scope=bot"))
        self.add_item(discord.ui.Button(label="Vote Bot", url="https://top.gg/bot/869041978467201280/vote"))
        self.add_item(discord.ui.Button(label="Share Idea", style=discord.ButtonStyle.green, custom_id="idea_button"))

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        
        # Add format file path
        self.format_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'data', 'config', 'format.json')
        self.format_variables = self.load_format_variables()
        
    def load_format_variables(self):
        """Format değişkenlerini JSON dosyasından yükler, dosya yoksa boş sözlük döndürür"""
        try:
            if os.path.exists(self.format_file_path):
                with open(self.format_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading format variables: {e}")
            return {}
            
    def get_format_mentions(self, guild):
        """Mevcut sunucudan tüm formatlama değişkenleri için mention'ları oluşturur"""
        format_mentions = {}

        # Rolleri işle
        for role_code, role_name in self.format_variables.get("roles", {}).items():
            role = discord.utils.get(guild.roles, name=role_name)
            format_mentions[role_code] = role.mention if role else f"@{role_name}"

        # Kanalları işle
        for channel_code, channel_name in self.format_variables.get("channels", {}).items():
            channel = discord.utils.get(guild.channels, name=channel_name)
            format_mentions[channel_code] = channel.mention if channel else f"#{channel_name}"

        # Kullanıcıları işle
        for user_code, user_id in self.format_variables.get("users", {}).items():
            user = guild.get_member(user_id)
            format_mentions[user_code] = user.mention if user else f"<@{user_id}>"

        # Sunucu ID'si
        format_mentions["guild_id"] = guild.id

        # Ensure "destek" key is always present (fallback to "support" if available)
        if "destek" not in format_mentions and "support" in format_mentions:
            format_mentions["destek"] = format_mentions["support"]

        return format_mentions

    # Utility helper methods
    def parse_color(self, color_input: str) -> int:
        """Convert predefined color names or hex strings to Discord color values"""
        # Dictionary of predefined colors
        color_map = {
            "red": 0xFF0000,
            "green": 0x00FF00,
            "blue": 0x0000FF,
            "yellow": 0xFFFF00,
            "purple": 0x800080,
            "orange": 0xFFA500,
            "pink": 0xFFC0CB,
            "black": 0x000000,
            "white": 0xFFFFFF
        }
        
        # Check if it's a predefined color
        if color_input.lower() in color_map:
            return color_map[color_input.lower()]
        
        # Try to parse as hex
        try:
            if color_input.startswith('#'):
                return int(color_input[1:], 16)
            else:
                return int(color_input, 16)
        except ValueError:
            return 0x0099FF  # Default blue color
            
    @commands.hybrid_group(name="server", description="Server-related commands")
    async def server(self, ctx):
        """Server-related commands"""
        if ctx.invoked_subcommand is None:
            # Default to server info
            await self.server_info(ctx)

    @server.command(name="info", description="Displays detailed server information.")
    async def server_info(self, ctx):
        """Displays information about the current server including member counts, boost status, and more."""
        guild = ctx.guild
        embed = discord.Embed(title=f"{guild.name} Server Information", color=discord.Color.blue())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        
        # Basic information
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Created", value=discord.utils.format_dt(guild.created_at, style='D'), inline=True)
        
        # Member counts
        total_members = guild.member_count
        humans = sum(1 for m in guild.members if not m.bot)
        bots = total_members - humans
        embed.add_field(name="Members", value=f"Total: {total_members}\nHumans: {humans}\nBots: {bots}", inline=True)
        
        # Channels
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        embed.add_field(name="Channels", value=f"Text: {text_channels}\nVoice: {voice_channels}\nCategories: {categories}", inline=True)
        
        # Server boost info
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count
        embed.add_field(name="Boost Status", value=f"Level {boost_level}\n{boost_count} Boosts", inline=True)
        
        # Additional info
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="Emojis", value=len(guild.emojis), inline=True)
        embed.add_field(name="Verification Level", value=str(guild.verification_level).title(), inline=True)
        
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @server.command(name="games", description="Show the most played games in the server")
    async def server_games(self, ctx):
        """Display the top played games on the server with statistics."""
        try:
            # Get game stats cog
            game_stats_cog = self.bot.get_cog("GameStats")
            if not game_stats_cog or not game_stats_cog.mongodb:
                embed = discord.Embed(
                    title="❌ Game Statistics Unavailable",
                    description="The game statistics system is not available.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)

            # Get guild stats
            game_stats = game_stats_cog.mongodb["game_stats"]
            guild_data = await game_stats.find_one({"guild_id": ctx.guild.id})
            
            if not guild_data or not guild_data.get("played_games"):
                embed = discord.Embed(
                    title="📊 No Game Statistics",
                    description="No game statistics available yet. Statistics will appear once members start playing games.",
                    color=discord.Color.blue()
                )
                return await ctx.send(embed=embed)

            # Sort games by total time played
            played_games = guild_data.get("played_games", [])
            sorted_games = sorted(played_games, key=lambda x: x.get("total_time_played", 0), reverse=True)
            
            # Take top 10 games
            top_games = sorted_games[:10]
            
            embed = discord.Embed(
                title="🎮 Most Played Games",
                description=f"Game statistics for {ctx.guild.name}:",
                color=discord.Color.blue()
            )
            
            if top_games:
                game_list = []
                for idx, game in enumerate(top_games, 1):
                    game_name = game.get("game_name", "Unknown Game")
                    total_time = game.get("total_time_played", 0)
                    player_count = len(game.get("players", []))
                    
                    # Convert time to hours and minutes
                    hours = total_time // 60
                    minutes = total_time % 60
                    
                    if hours > 0:
                        time_str = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
                    else:
                        time_str = f"{minutes}m"
                    
                    # Add medal emojis for top 3
                    if idx == 1:
                        medal = "🥇"
                    elif idx == 2:
                        medal = "🥈"
                    elif idx == 3:
                        medal = "🥉"
                    else:
                        medal = f"{idx}."
                    
                    game_list.append(f"{medal} **{game_name}**\n└ ⏱️ {time_str} • 👥 {player_count} players")
                
                # Split into chunks if too long
                game_text = "\n\n".join(game_list)
                if len(game_text) <= 1024:
                    embed.add_field(
                        name="📈 Statistics",
                        value=game_text,
                        inline=False
                    )
                else:
                    # Split into multiple fields
                    for i in range(0, len(game_list), 5):
                        chunk = game_list[i:i+5]
                        embed.add_field(
                            name="📈 Statistics" if i == 0 else "\u200b",
                            value="\n\n".join(chunk),
                            inline=False
                        )
            
            # Add footer with additional info
            total_games_tracked = len(played_games)
            embed.set_footer(text=f"Tracking {total_games_tracked} different games • Requested by {ctx.author}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in server games command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while fetching game statistics.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="copy_emoji", 
        description="Copy an emoji from another server or URL and add it to this server"
    )
    @app_commands.describe(
        source="Discord emoji, image URL, or type for autocomplete suggestions",
        name="Custom name for the emoji (optional)"
    )
    @commands.has_permissions(manage_emojis=True)
    @commands.cooldown(1, 15, commands.BucketType.user)  # 15 second cooldown per user
    async def copy_emoji(self, ctx, source: str, name: str = None):
        """
        Copy an emoji from another server or URL and add it to this server.
        
        Parameters:
        - source: Can be a Discord emoji, URL to an image, or a predefined emoji name
        - name: Optional custom name for the emoji (if not provided, uses original name or 'emoji')
        
        Examples:
        - /copy_emoji source:<:emoji:123456789> name:cool_emoji
        - /copy_emoji source:https://emoji.gg/emoji/6442-snake-pog
        - /copy_emoji source:pepe_laugh
        """
        guild = ctx.guild
        await ctx.defer()
        
        # Dictionary of predefined emoji URLs
        predefined_emojis = {
            "pepe_laugh": "https://cdn3.emoji.gg/emojis/6158_PepeLaugh.png",
            "pepe_hands": "https://cdn3.emoji.gg/emojis/PepeHands.png",
            "pepe_think": "https://cdn3.emoji.gg/emojis/pepethink.png",
            "dogge": "https://cdn3.emoji.gg/emojis/1225_doggee.png",
            "kekw": "https://cdn3.emoji.gg/emojis/99779-kekw.png",
            "pog": "https://cdn3.emoji.gg/emojis/49759-pog.png",
        }
        
        try:
            # Check if source is a Discord emoji
            if source.startswith("<") and source.endswith(">"):
                # Extract emoji ID
                emoji_id = int(source.split(":")[-1].replace(">", ""))
                emoji_name = source.split(":")[-2] if not name else name
                emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
            
            # Check if source is a predefined emoji
            elif source.lower() in predefined_emojis:
                emoji_url = predefined_emojis[source.lower()]
                emoji_name = name if name else source.lower()
            
            # Otherwise treat source as a direct URL
            else:
                emoji_url = source
                emoji_name = name if name else "emoji"
                
            # Download and add the emoji
            async with aiohttp.ClientSession() as session:
                async with session.get(emoji_url) as resp:
                    if resp.status != 200:
                        return await ctx.send(
                            embed=create_embed(description=f"Could not download emoji from {emoji_url}. Invalid source or URL.", color=discord.Color.red()))
                    
                    data = io.BytesIO(await resp.read())
                    image_data = data.getvalue()
                    
                    # Sanitize emoji name - remove special characters and ensure valid length
                    emoji_name = ''.join(c for c in emoji_name if c.isalnum() or c == '_')
                    emoji_name = emoji_name[:32] if len(emoji_name) > 32 else emoji_name
                    if not emoji_name:  # If name ended up empty after sanitization
                        emoji_name = "emoji"
                    
                    try:
                        new_emoji = await guild.create_custom_emoji(name=emoji_name, image=image_data)
                        embed = discord.Embed(
                            title="Emoji Added Successfully!",
                            description=f"Added emoji {new_emoji} to the server.",
                            color=discord.Color.green()
                        )
                        embed.add_field(name="Name", value=emoji_name, inline=True)
                        embed.add_field(name="Source", value="Discord Emoji" if source.startswith("<") else 
                                        ("Predefined Emoji" if source.lower() in predefined_emojis else "URL"), inline=True)
                        embed.set_footer(text="You can use this command again in 15 seconds")
                        embed.set_thumbnail(url=emoji_url)
                        await ctx.send(embed=embed)
                        await increment_utility_stat(ctx.guild.id, 'messagesProcessed', 1)
                        await increment_utility_stat(ctx.guild.id, 'activeTools', 1)
                    except discord.HTTPException as e:
                        await ctx.send(embed=create_embed(
                            description=f"Error adding emoji: {str(e)}. The image might be too large or in an unsupported format.",
                            color=discord.Color.red()
                        ))
        
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Emoji Error: {error_details}")  # Log detailed error to console
            
            await ctx.send(embed=create_embed(
                description=f"Failed to process emoji: {str(e)}\n\n"
                           f"Usage: `/copy_emoji <emoji/url/preset> [name]`\n"
                           f"Available presets: {', '.join(predefined_emojis.keys())}\n"
                           f"You can also use any image URL or emoji.gg link",
                color=discord.Color.red()
            ))

    # Add autocomplete for emoji sources
    @copy_emoji.autocomplete("source")
    async def emoji_source_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        # Dictionary of predefined emoji suggestions with descriptions
        predefined_emojis = {
            "pepe_laugh": "PepeLaugh Emote",
            "pepe_hands": "PepeHands Emote",
            "pepe_think": "PepeThink Emote",
            "dogge": "Dogge Emote",
            "kekw": "KEKW Laughing Emote",
            "pog": "PogChamp Emote",
        }

        # Filter suggestions based on current input
        suggestions = [
            app_commands.Choice(name=f"{key} - {value}", value=key)
            for key, value in predefined_emojis.items() 
            if current.lower() in key.lower() or current.lower() in value.lower()
        ]
        
        # If the current input looks like a URL, add it as a suggestion
        if current.startswith(("http://", "https://")) and len(current) > 10:
            suggestions.insert(0, app_commands.Choice(name=f"Custom URL: {current[:30]}...", value=current))
            
        # If current looks like a Discord emoji, add it as a suggestion
        if current.startswith("<") and ":" in current:
            suggestions.insert(0, app_commands.Choice(name=f"Discord Emoji: {current}", value=current))
            
        # Return up to 25 suggestions (Discord limit)
        return suggestions[:25]

    @copy_emoji.error
    async def copy_emoji_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=create_embed(
                description=f"You're on cooldown! Try again in {error.retry_after:.1f} seconds.",
                color=discord.Color.orange()
            ), ephemeral=True)
        else:
            await ctx.send(embed=create_embed(
                description=f"An error occurred: {str(error)}",
                color=discord.Color.red()
            ), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Utility(bot))
