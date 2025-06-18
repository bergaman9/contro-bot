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
from utils.core.formatting import create_embed, hex_to_int, calculate_how_long_ago_member_joined, calculate_how_long_ago_member_created
from utils.database.connection import initialize_mongodb, is_db_available
from utils.core.db import get_document, get_documents, update_document

# Configure logger
logger = logging.getLogger('utility')
from utils.core.class_utils import Paginator
from utils.imaging import circle, download_background
from utils.content_loader import load_content

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
        self.format_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'format.json')
        self.format_variables = self.load_format_variables()
        
    @commands.hybrid_command(name="ping", description="Shows the latency between in the bot and the Discord API.", aliases=["latency"])
    async def ping(self, ctx: commands.Context):
        try:
            # Get basic info
            latency = round(self.bot.latency * 1000)  # latency in ms
            
            # Calculate uptime - use fallback if startTime not available
            if hasattr(self.bot, 'startTime'):
                uptime = str(timedelta(seconds=int(round(time.time() - self.bot.startTime))))
            else:
                uptime = "Unknown"
                
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get server region/provider
            server_region = "Unknown Region"
            server_provider = "Unknown Provider"
            
            try:
                ip_resp = requests.get("https://ipwho.is/").json()
                server_country = ip_resp.get("country", "N/A")
                server_city = ip_resp.get("city", "N/A")
                server_provider_name = ip_resp.get("connection", {}).get("isp", "N/A")
                server_flag = ip_resp.get("flag", {}).get("emoji", "")
                server_region = f"{server_flag} {server_country}, {server_city}" if server_flag else f"{server_country}, {server_city}"
                server_provider = f"🌐 {server_provider_name}"
            except Exception:
                pass
            
            # Try to get version from settings
            version = "N/A"
            try:
                settings_doc = self.mongo_db["settings"].find_one({"guild_id": 939587672081592340})
                if settings_doc and "version" in settings_doc:
                    version = settings_doc["version"]
                if version == "N/A":
                    all_settings = self.mongo_db["settings"].find({"version": {"$exists": True}})
                    if all_settings.count():
                        version = all_settings[0].get("version", "N/A")
            except Exception as e:
                print(f"Error fetching bot version: {e}")
            
            embed = discord.Embed(
                title="🏓 Ping & Hosting Info",
                color=0x45C2BE
            )
            embed.add_field(name='Ping', value=f'{latency}ms', inline=True)
            embed.add_field(name='Uptime', value=f'{uptime}', inline=True)
            embed.add_field(name='Bot Version', value=f'{version}', inline=True)
            embed.add_field(name='CPU Usage', value=f'{cpu_percent}%', inline=True)
            embed.add_field(name='RAM Usage', value=f'{memory.percent}% ({memory.used / 1024**2:.1f}MB / {memory.total / 1024**2:.1f}MB)', inline=True)
            embed.add_field(name='Disk Usage', value=f'{disk.percent}% ({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)', inline=True)
            embed.add_field(name='Download Speed', value='Calculating...', inline=True)
            embed.add_field(name='Upload Speed', value='Calculating...', inline=True)
            embed.add_field(name='Discord.py', value=f'{discord.__version__}', inline=True)
            embed.add_field(name='Python', value=f'{platform.python_version()}', inline=True)
            embed.add_field(name='Platform', value=f'{platform.system()} {platform.release()}', inline=True)
            embed.add_field(name='Server Region', value=f'{server_region}', inline=True)
            embed.add_field(name='Server Provider', value=f'{server_provider}', inline=True)
            embed.add_field(name='Active Users', value=f'{len(self.bot.users)}', inline=True)
            embed.add_field(name='Active Commands', value=f'{len(self.bot.commands)}', inline=True)
            
            if self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)
            
            user_emoji = getattr(ctx.author, 'display_avatar', None)
            user_emoji_url = user_emoji.url if user_emoji else None
            if user_emoji_url:
                embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=user_emoji_url)
            else:
                embed.set_footer(text=f"Requested by {ctx.author.name}")
            
            msg = await ctx.send(embed=embed)
            
            # Calculate internet speeds
            download_speed = "N/A"
            upload_speed = "N/A"
            try:
                import speedtest
                st = await asyncio.to_thread(speedtest.Speedtest)
                await asyncio.to_thread(st.get_best_server)
                download_mbps = await asyncio.to_thread(st.download) / 1_000_000
                upload_mbps = await asyncio.to_thread(st.upload) / 1_000_000
                download_speed = f"{download_mbps:.1f} Mbps"
                upload_speed = f"{upload_mbps:.1f} Mbps"
            except ImportError:
                print("speedtest-cli library not installed, using fallback method")
                try:
                    import urllib.request
                    start_time = time.time()
                    await asyncio.to_thread(
                        lambda: urllib.request.urlopen("https://github.com/LibreSpeed/speedtest-go/raw/master/speedtest/garbage.php?ckSize=1000000", timeout=5).read()
                    )
                    end_time = time.time()
                    duration = end_time - start_time
                    if duration > 0:
                        file_size_mb = 1
                        download_speed = f"{(file_size_mb * 8) / duration:.1f} Mbps"
                    upload_speed = "~5.0 Mbps (estimated)"
                except Exception as e:
                    print(f"Error in fallback speed test: {e}")
                    download_speed = "Test failed"
                    upload_speed = "Test failed"
            except Exception as e:
                print(f"Error testing internet speed with speedtest: {e}")
                download_speed = "Test failed"
                upload_speed = "Test failed"
            
            embed.set_field_at(6, name='Download Speed', value=f'{download_speed}', inline=True)
            embed.set_field_at(7, name='Upload Speed', value=f'{upload_speed}', inline=True)
            await msg.edit(embed=embed)
            
        except Exception as e:
            print(f"Error in ping command: {e}")
            await ctx.send(embed=discord.Embed(description="An error occurred while getting server status.", color=discord.Color.red()))

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
            
    # Information commands
    @commands.hybrid_command(name="whois", description="Shows member info.")
    @app_commands.describe(member="The member to display information about. Defaults to yourself if not provided.")
    async def whois(self, ctx, member: discord.Member = None):
        if not member:
            member = ctx.author

        embed = discord.Embed(title=member.name, description=member.mention, color=discord.Colour.blue())
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Joined at", value=member.joined_at.strftime("%a, %d %B %Y, %I:%M  UTC"))
        embed.add_field(name="Joined Server On:", value=(member.joined_at.strftime("%a, %d %B %Y, %I:%M %p UTC")))
        embed.add_field(name="Highest Role:", value=member.top_role.mention)
        embed.add_field(name="Voice:", value=member.voice)
        embed.set_thumbnail(url=member.display_avatar)
        embed.set_footer(icon_url=ctx.author.display_avatar, text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", description="Shows member avatar.")
    @app_commands.describe(member="The member whose avatar you want to see. Defaults to yourself if not provided.")
    async def avatar(self, ctx, *, member: discord.Member = None):
        if not member:
            member = ctx.author
        userAvatar = member.display_avatar
        embed = discord.Embed(title=f"{member.name}'s Avatar", description="", color=0xffff00)
        embed.set_image(url=userAvatar.url)
        embed.set_footer(icon_url=ctx.author.display_avatar, text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

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

    @commands.hybrid_command(name="members_of_role", description="Lists members with a specific role.")
    @app_commands.describe(role="The role to list members from.")
    async def members_of_role(self, ctx, role: discord.Role):
        members_with_role = [member for member in ctx.guild.members if role in member.roles]

        if not members_with_role:
            await ctx.send(f"Hiçbir kullanıcının {role.name} rolü yok.")
            return

        embeds = generate_members_of_role_embeds(members_with_role, role)
        paginator = Paginator(embed_list=embeds)
        await paginator.send_initial_message(ctx)

    @commands.hybrid_command(name="detect_advertisements", description="Detects and lists all custom activities that are discord invites or suspicious links.")
    @commands.has_permissions(manage_guild=True)
    async def advertisements(self, ctx):
        """Detects and lists all custom activities in the server that are Discord invites or suspicious links."""
        guild = ctx.guild
        found_advertisements = False
        suspicious_keywords = ["discord.gg/", "https://", "http://", "www.", ".com", ".net", ".org"]

        embed = discord.Embed(
            title="Detected Advertisements",
            description="List of members with suspicious custom statuses:",
            color=discord.Color.red()
        )

        for member in guild.members:
            for activity in member.activities:
                if activity.type == discord.ActivityType.custom:
                    message = activity.name
                    if message and any(keyword in message.lower() for keyword in suspicious_keywords):
                        embed.add_field(
                            name=f"{member.display_name} ({member.id})",
                            value=f"Custom Status: `{message}`",
                            inline=False
                        )
                        found_advertisements = True

        if found_advertisements:
            await ctx.send(embed=embed)
        else:
            await ctx.send(
                embed=create_embed(description="No advertisements or suspicious links found in the server.", color=discord.Color.green())
            )

    # Emoji related commands
    @commands.hybrid_command(name="emoji_list", description="Fetch emojis of the server.")
    async def emoji_list(self, ctx):
        emojis = await ctx.guild.fetch_emojis()
        static_emojis = [f"<:{emoji.name}:{emoji.id}>" for emoji in emojis if not emoji.animated]
        animated_emojis = [f"<a:{emoji.name}:{emoji.id}>" for emoji in emojis if emoji.animated]

        # Sayfa başına kaç emoji gösterilecek
        emojis_per_page = 50

        # Embed'leri oluşturma
        def create_embed_pages(emojis_list, title):
            pages = []
            for i in range(0, len(emojis_list), emojis_per_page):
                chunk = emojis_list[i:i + emojis_per_page]
                embed = discord.Embed(title=title, description=" ".join(chunk), color=discord.Color.blurple())
                embed.set_thumbnail(url=ctx.guild.icon.url)
                pages.append(embed)
            return pages

        static_embeds = create_embed_pages(static_emojis, "Server Static Emojis")
        animated_embeds = create_embed_pages(animated_emojis, "Server Animated Emojis")

        # İlk olarak statik emoji listesini gönderelim
        if len(static_embeds) > 0:
            static_paginator = Paginator(static_embeds)
            await static_paginator.send_initial_message(ctx)
        else:
            await ctx.send(embed=create_embed(description="No static emojis found.", color=discord.Color.red()))

        # Sonrasında animasyonlu emoji listesini gönderelim
        if len(animated_embeds) > 0:
            animated_paginator = Paginator(animated_embeds)
            await animated_paginator.send_initial_message(ctx)
        else:
            await ctx.send(embed=create_embed(description="No animated emojis found.", color=discord.Color.red()))

    @commands.command(name="download_emojis", description="Fetch emojis of the server.")
    @commands.has_permissions(manage_messages=True)
    async def download_emojis(self, interaction):

        # defer response
        await interaction.response.defer()

        # mkdir images
        if not os.path.exists("images"):
            os.mkdir("images")

        # download emojis
        emojis = await interaction.guild.fetch_emojis()
        for emoji in emojis:
            response = requests.get(emoji.url)
            img = Image.open(BytesIO(response.content))
            img.save(f"images/{emoji.name}.png")

        # zip folder
        shutil.make_archive(f"{interaction.guild.name} emojis", "zip", "images")
        shutil.rmtree("images")

        # send file
        await interaction.followup.send(file=discord.File(f"{interaction.guild.name} emojis.zip"))
        os.remove(f"{interaction.guild.name} emojis.zip")

        # remove images folder
        if os.path.exists("images"):
            shutil.rmtree("images")

    @commands.hybrid_command(name="emote", description="Shows emote info.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(emoji="The emoji to show information about.")
    async def emote(self, ctx, emoji: discord.Emoji):

        if not emoji:
            return ctx.invoke(self.bot.get_command("help"), entity="emote")

        try:
            emoji = await emoji.guild.fetch_emoji(emoji.id)
        except discord.NotFound:
            return await ctx.send("I could not find this emoji in the given guild.")

        is_managed = "Yes" if emoji.managed else "No"
        is_animated = "Yes" if emoji.animated else "No"
        require_colons = "Yes" if emoji.require_colons else "No"
        creation_time = emoji.created_at.strftime("%I:%M %p, %d %B %Y")
        can_use_emoji = "Everyone" if not emoji.roles else "".join(role.name for role in emoji.roles)

        description = f"""
        **General:**
        **- Name: **{emoji.name}
        **- ID: **{emoji.id}
        **- URL: **[Link to Emoji]({emoji.url})
        **- Author: ** {emoji.user.mention}    
        **- Time Created: ** {creation_time}    
        **- Usable by: ** {can_use_emoji}    

        **Other:**
        **- Animated: ** {is_animated}
        **- Managed: ** {is_managed}
        **- Requires Colons: ** {require_colons}
        **- Guild Colons: ** {emoji.guild.name}
        **- Guild ID: ** {emoji.guild.id}
        """

        embed = discord.Embed(
            title=f"**Emoji Information for: ** `{emoji.name}`",
            description=description,
            colour=0xadd8e6)

        embed.set_thumbnail(url=emoji.url)
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

    # Role management commands
    # REMOVED: This command is now integrated into the unified /settings panel (Status Roles section)
    # @commands.hybrid_command(name="set_status_role",
    #                          description="Sets the custom status and role for the status_role command.")
    # @commands.has_permissions(manage_guild=True)
    # @app_commands.describe(
    #     custom_status="The custom status text to trigger role assignment (comma-separated for multiple statuses)",
    #     role="The role to assign when a member has the specified custom status"
    # )
    # async def set_status_role(self, ctx, custom_status: str, role: discord.Role):
    #     # Get the status_roles collection from the database
    #     cleaned_custom_status = custom_status.strip().lower()
    #     collection = self.mongo_db["status_roles"]
    #     
    #     # Update the status_role mapping
    #     collection.update_one({"guild_id": ctx.guild.id},
    #                           {"$set": {"custom_status": cleaned_custom_status, "role_id": role.id}}, upsert=True)
    #     await ctx.send(f"Status role set to {role.mention} for custom status '{custom_status}'.")

    @app_commands.command(name="mass_unban", description="Mass unban people banned from the server.")
    @commands.has_permissions(manage_guild=True)
    async def mass_unban(self, interaction):
        async for entry in interaction.guild.bans(limit=None):
            await interaction.guild.unban(entry.user)

        await interaction.response.send_message("All banned members from the server unbanned.", ephemeral=True)





    # Embed and content commands
    @commands.hybrid_command(name="poll", description="Creates a poll.")
    @app_commands.describe(
        question="The question for the poll",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
        option5="Fifth option (optional)",
        option6="Sixth option (optional)",
        option7="Seventh option (optional)",
        option8="Eighth option (optional)",
        option9="Ninth option (optional)",
        option10="Tenth option (optional)"
    )
    async def poll(self, ctx, question: str, option1: str, option2: str, option3: str = None, option4: str = None,
                   option5: str = None, option6: str = None, option7: str = None, option8: str = None,
                   option9: str = None, option10: str = None):

        emoji_list = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        # Gather all the options into a list and filter out None values
        options = [opt for opt in
                   [option1, option2, option3, option4, option5, option6, option7, option8, option9, option10] if
                   opt is not None]

        # Create the embed
        embed_description = "\n".join(f"{emoji_list[idx]} {option}" for idx, option in enumerate(options))
        embed = discord.Embed(title=question, description=embed_description, color=ctx.author.color)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)

        # Send the embed
        message = await ctx.send(embed=embed)

        # Add the reactions
        for emoji in emoji_list[:len(options)]:
            await message.add_reaction(emoji)

    @app_commands.command(name="embed", description="Creates embed message with optional file content and buttons.")
    @app_commands.describe(
        title="Title of the embed.",
        description="Description of the embed. Can be skipped if content file is provided.",
        content_file="Content file to use (any text format).",
        color="Color of embed (e.g., red, blue, green, or hex like ff0000).",
        image_url="URL for embed main image.",
        thumbnail_url="URL for embed thumbnail image.",
        footer_text="Optional text to display in the footer.",
        footer_icon_url="Optional icon URL for the footer.",
        use_server_format="Whether to use server format variables for replacements.",
        button_labels="Button labels separated by | (e.g., 'Website|Discord|Contact')",
        button_urls="Button URLs separated by | (must match number of labels)",
        button_emojis="Optional button emojis separated by | (can be fewer than labels)"
    )
    @app_commands.choices(color=[
        app_commands.Choice(name="Red", value="red"),
        app_commands.Choice(name="Blue", value="blue"),
        app_commands.Choice(name="Green", value="green"),
        app_commands.Choice(name="Yellow", value="yellow"),
        app_commands.Choice(name="Purple", value="purple"),
        app_commands.Choice(name="Orange", value="orange"),
        app_commands.Choice(name="Pink", value="pink"),
        app_commands.Choice(name="Cyan", value="cyan"),
        app_commands.Choice(name="Gold", value="gold"),
        app_commands.Choice(name="Discord Default", value="default")
    ])
    @commands.has_permissions(manage_messages=True)
    async def embed(self, interaction, *, 
                    title: str, 
                    description: str = None,
                    content_file: discord.Attachment = None,
                    color: str = "default", 
                    image_url: str = None,
                    thumbnail_url: str = None,
                    footer_text: str = None,
                    footer_icon_url: str = None,
                    use_server_format: bool = False,
                    button_labels: str = None,
                    button_urls: str = None,
                    button_emojis: str = None):
        # Defer the response since we might need to process files
        await interaction.response.defer(ephemeral=True)
        
        # Determine the content source
        embed_description = None
        
        # If a content file is provided, use its content as the description
        if content_file:
            # Check if the file is a text file
            if not content_file.filename.lower().endswith(('.md', '.markdown', '.txt', '.text', '.html', '.htm', '.xml', '.json', '.csv', '.rtf')):
                await interaction.followup.send("Please upload a text file.", ephemeral=True)
                return
            
            # Download and read the file content
            file_content = await content_file.read()
            try:
                # Try to decode as UTF-8
                embed_description = file_content.decode('utf-8')
            except UnicodeDecodeError:
                await interaction.followup.send("Could not decode file. Please ensure it is a valid text file.", ephemeral=True)
                return
        else:
            # If no content file, use the provided description parameter
            if not description:
                await interaction.followup.send("Please provide either a description or a content file.", ephemeral=True)
                return
            embed_description = description
        
        # Apply server format variables if requested
        if use_server_format:
            format_mentions = self.get_format_mentions(interaction.guild)
            try:
                embed_description = embed_description.format(**format_mentions)
            except KeyError as e:
                await interaction.followup.send(f"Format error: Missing key {e} in format variables.", ephemeral=True)
                return
            except Exception as e:
                await interaction.followup.send(f"Error applying format: {str(e)}", ephemeral=True)
                return
        
        # Parse the color
        try:
            color_value = self.parse_color(color)
        except Exception as e:
            await interaction.followup.send(f"Error parsing color: {str(e)}. Using default color.", ephemeral=True)
            color_value = 0x5865f2  # Discord default blue
        
        # Create button view if buttons are specified
        view = None
        if button_labels and button_urls:
            # Split the input strings by the pipe character
            labels = [label.strip() for label in button_labels.split('|')]
            urls = [url.strip() for url in button_urls.split('|')]
            
            # Check if the number of labels and URLs match
            if len(labels) != len(urls):
                await interaction.followup.send("The number of button labels and URLs must match.", ephemeral=True)
                return
                
            # Process emojis if provided
            emojis = []
            if button_emojis:
                emojis = [emoji.strip() for emoji in button_emojis.split('|')]
                # Pad with None if there are fewer emojis than buttons
                while len(emojis) < len(labels):
                    emojis.append(None)
            else:
                emojis = [None] * len(labels)
            
            # Create the view with buttons
            view = discord.ui.View()
            for i in range(len(labels)):
                view.add_item(discord.ui.Button(
                    label=labels[i],
                    url=urls[i],
                    emoji=emojis[i] if i < len(emojis) else None,
                    style=discord.ButtonStyle.link
                ))
        
        # Check if the description is too long (Discord limit is about 4000 characters)
        if len(embed_description) > 4000:
            # Split the content into chunks of 4000 characters
            # Try to split at paragraphs or line breaks when possible
            chunks = []
            current_chunk = ""
            
            # Split by lines first to try to keep paragraphs together
            lines = embed_description.split('\n')
            
            for line in lines:
                # If adding this line would make the chunk too long, start a new chunk
                if len(current_chunk) + len(line) + 1 > 4000:  # +1 for the newline
                    if current_chunk:  # Only append if not empty
                        chunks.append(current_chunk)
                    current_chunk = line
                else:
                    if current_chunk:
                        current_chunk += '\n' + line
                    else:
                        current_chunk = line
            
            # Add the last chunk if it has content
            if current_chunk:
                chunks.append(current_chunk)
            
            # Create and send multiple embeds
            for i, chunk in enumerate(chunks):
                embed = discord.Embed(
                    title=title,
                    description=chunk,
                    colour=color_value
                )
                
                # Add image and thumbnail only to the first embed
                if i == 0:
                    if image_url:
                        embed.set_image(url=image_url)
                    if thumbnail_url:
                        embed.set_thumbnail(url=thumbnail_url)
                
                # Custom footer with page numbers for all embeds
                page_footer_text = f"{footer_text} • Page {i+1}/{len(chunks)}" if footer_text else f"Page {i+1}/{len(chunks)}"
                embed.set_footer(text=page_footer_text, icon_url=footer_icon_url if footer_icon_url else None)
                
                # Only add the view to the last embed
                if i == len(chunks) - 1 and view:
                    await interaction.channel.send(embed=embed, view=view)
                else:
                    await interaction.channel.send(embed=embed)
            
            await interaction.followup.send(f"Embed created in {len(chunks)} pages due to content length!", ephemeral=True)
        else:
            # Create and send a single embed
            embed = discord.Embed(title=title, description=embed_description, colour=color_value)
            
            # Add optional elements
            if image_url:
                embed.set_image(url=image_url)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
            if footer_text:
                embed.set_footer(text=footer_text, icon_url=footer_icon_url if footer_icon_url else None)
            
            # Send the embed with the view if buttons were added
            if view:
                await interaction.channel.send(embed=embed, view=view)
            else:
                await interaction.channel.send(embed=embed)
                
            await interaction.followup.send("Embed is created!", ephemeral=True)

    @app_commands.command(name="link_buttons", description="Creates an embed with up to 5 link buttons.")
    @app_commands.describe(
        title="The title of the embed",
        description="The description of the embed",
        color="The hex color code for the embed (default is red: ff0000)",
        button_labels="Space-separated labels for buttons (use quotes for multi-word labels)",
        button_links="Space-separated URLs for the buttons (must match number of labels)",
        button_emojis="Space-separated emojis for the buttons (optional)"
    )
    async def link_buttons(self, interaction, title: str, description: str, color: str = "ff0000", 
                           button_labels: str = None, button_links: str = None, button_emojis: str = None):
        """
        Creates an embed with up to 5 link buttons.

        Args:
            title (str): The title of the embed.
            description (str): The description of the embed.
            color (str): The hex color code for the embed (default is "ff0000").
            button_labels (str): Space-separated labels for the buttons. Use quotes for multi-word labels.
            button_links (str): Space-separated URLs for the buttons.
            button_emojis (str): Space-separated emojis for the buttons (optional).
        """

        view = discord.ui.View()

        if button_labels and button_links:
            labels = shlex.split(button_labels)
            links = shlex.split(button_links)
            emojis = shlex.split(button_emojis) if button_emojis else []

            if len(labels) > 5 or len(links) > 5:
                await interaction.response.send_message(
                    "You can only add up to 5 buttons.", ephemeral=True
                )
                return

            for i in range(len(labels)):
                view.add_item(discord.ui.Button(
                    label=labels[i],
                    url=links[i],
                    style=discord.ButtonStyle.link,
                    emoji=emojis[i] if i < len(emojis) else None
                ))

        embed = discord.Embed(title=title, description=description, color=int(color, 16))
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            embed=create_embed(description="Embed with link buttons created!", color=discord.Color.green()), 
            ephemeral=True
        )

    # Copy message utility
    @commands.command(name="copy_message", description="Copies a user's message and sends it as the bot.")
    @commands.has_permissions(manage_messages=True)
    async def copy_message(self, ctx: commands.Context, message_id: str = None, channel: discord.TextChannel = None):
        """
        Copies a message and sends it as the bot.
        
        Parameters:
            ctx (commands.Context): The Discord context containing information about the command invocation.
            message_id (str): The ID of the message to copy. Can be found by enabling Developer Mode and right-clicking on a message.
            channel (discord.TextChannel): Optional channel where the message is located. If not provided, uses the current channel.
        
        Examples:
            !copy_message 123456789012345678
            !copy_message 123456789012345678 #general
        """
        if not message_id:
            return await ctx.send("Please provide a message ID to copy.")
        
        try:
            # Get the channel to fetch the message from
            channel = channel or ctx.channel
            
            # Fetch the message
            message = await channel.fetch_message(int(message_id))
            
            # Delete the command message if possible
            try:
                await ctx.message.delete()
            except:
                pass
            
            # Handle embeds
            if message.embeds:
                for embed in message.embeds:
                    await ctx.send(embed=embed)

            # Handle attachments (e.g., images)
            if message.attachments:
                for attachment in message.attachments:
                    await ctx.send(file=await attachment.to_file())

            # Handle text content
            if message.content:
                await ctx.send(message.content)
                
            # Send success confirmation as ephemeral if this was invoked from a slash command
            if hasattr(ctx, 'interaction') and ctx.interaction:
                await ctx.send("Message copied successfully!", ephemeral=True, delete_after=5)
        except discord.NotFound:
            await ctx.send("Couldn't find that message. Make sure the ID is correct.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to access that message.")
        except ValueError:
            await ctx.send("Invalid message ID. Please provide a valid message ID.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Make sure commands are synced on cog load
        self._sync_commands_task = self.bot.loop.create_task(self._sync_commands())
        
    async def _sync_commands(self):
        """Ensure commands are properly synced"""
        try:
            await self.bot.wait_until_ready()
            # Only sync if we're in the primary bot instance to avoid rate limiting
            if getattr(self.bot, 'is_primary_instance', True):
                await self.bot.tree.sync()
                print("Command tree successfully synced")
        except Exception as e:
            print(f"Error syncing command tree: {e}")

    # REMOVED: These commands are now integrated into the unified /settings panel
    # contro_guilds is now in Developer section (owner-only)
    # support is replaced by button in settings or website
    # @commands.hybrid_command(name="contro_guilds", description="Shows a list of all servers the bot is in.")
    # @commands.is_owner()
    # async def contro_guilds(self, ctx):
    #     try:
    #         # Create an embed with guild list
    #         guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
    #         
    #         # Paginate if there are many guilds
    #         embeds = []
    #         for i in range(0, len(guilds), 10):
    #             embed = discord.Embed(
    #                 title=f"📊 Bot Servers ({len(guilds)} total)",
    #                 color=discord.Color.blue()
    #             )
    #             
    #             guild_slice = guilds[i:i+10]
    #             for guild in guild_slice:
    #                 embed.add_field(
    #                     name=guild.name,
    #                     value=f"Members: {guild.member_count}\nID: {guild.id}",
    #                     inline=True
    #                 )
    #             
    #             embed.set_footer(text=f"Page {i//10 + 1}/{(len(guilds)-1)//10 + 1}")
    #             embeds.append(embed)
    #         
    #         # Send with pagination if multiple pages
    #         if len(embeds) > 1:
    #             view = PaginationView(embeds)
    #             await ctx.send(embed=embeds[0], view=view)
    #         else:
    #             await ctx.send(embed=embeds[0])
    #             
    #     except Exception as e:
    #         await ctx.send(f"Error: {str(e)}")

    # @commands.hybrid_command(name="support", description="Shows information about the bot's support server.")
    # async def support(self, ctx):
    #     embed = discord.Embed(
    #         title="🛡️ Support Server",
    #         description="Need help? Join our support server!",
    #         color=discord.Color.blue()
    #     )
    #     
    #     embed.add_field(
    #         name="Support Server",
    #         value="[Click here to join](https://discord.gg/YOUR_INVITE_LINK)",
    #         inline=False
    #     )
    #     
    #     embed.add_field(
    #         name="Website",
    #         value="[Visit our website](https://your-website.com)",
    #         inline=True
    #     )
    #     
    #     embed.add_field(
    #         name="Documentation",
    #         value="[Read the docs](https://docs.your-website.com)",
    #         inline=True
    #     )
    #     
    #     await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        try:
            # Handle button interactions
            if interaction.type == discord.InteractionType.component:
                custom_id = interaction.data.get("custom_id")
                if custom_id == "idea_button":
                    await interaction.response.send_modal(IdeaModal())
                    return
            
            # Handle modal submissions
            elif interaction.type == discord.InteractionType.modal_submit:
                components = interaction.data.get('components', [])
                if not components:
                    return
                    
                component = components[0].get('components', [{}])[0]
                if component.get('custom_id') == "idea_text":
                    idea = component.get('value', '')
                    await self._handle_idea_submission(interaction, idea)
        except Exception as e:
            print(f"Error in on_interaction: {e}")
    
    async def _handle_idea_submission(self, interaction: discord.Interaction, idea: str):
        """Helper method to handle idea submissions"""
        try:
            # Create and send embed to the ideas channel
            embed = discord.Embed(description=idea, color=discord.Color.pink())
            embed.set_author(name=f"Idea of {interaction.user.name}", icon_url=interaction.user.avatar.url)
            
            # Get ideas channel and send message
            channel = self.bot.get_channel(970327943312191488)
            if not channel:
                await interaction.response.send_message(
                    embed=discord.Embed(title="Error", description="Ideas channel not found.", color=discord.Color.red()),
                    ephemeral=True
                )
                return
                
            message = await channel.send(embed=embed)
            
            # Send confirmation to user
            await interaction.response.send_message(
                embed=discord.Embed(title="Your idea has been sent to the developer.",
                                    description="Thank you for your idea.", color=discord.Color.pink()))
            
            # Add reactions to the idea message
            await message.add_reaction("👍")
            await message.add_reaction("👎")
            
            # Delete the interaction message after 30 seconds
            await asyncio.sleep(30)
            if interaction.message:
                await interaction.message.delete()
        except Exception as e:
            print(f"Error handling idea submission: {e}")


async def setup(bot):
    """Load the cog."""
    bot.add_cog(Utility(bot))
    bot.add_cog(Config(bot))
