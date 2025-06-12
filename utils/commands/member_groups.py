# Member command groups organization
# This file defines how member commands should be grouped with English names

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
import hashlib
import random
import aiohttp
import asyncio
import json
import os
import datetime
from utils.core.formatting import create_embed

class InfoCommands(commands.GroupCog, name="info"):
    """Information and utility commands for members"""
    
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="user", description="Shows detailed user information")
    @app_commands.describe(member="The member to get information about")
    async def user_info(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        """Shows user information - replaces whois command"""
        if not member:
            member = interaction.user

        embed = discord.Embed(title=member.name, description=member.mention, color=discord.Colour.blue())
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Joined at", value=member.joined_at.strftime("%a, %d %B %Y, %I:%M  UTC"))
        embed.add_field(name="Joined Server On:", value=(member.joined_at.strftime("%a, %d %B %Y, %I:%M %p UTC")))
        embed.add_field(name="Highest Role:", value=member.top_role.mention)
        embed.add_field(name="Voice:", value=member.voice)
        embed.set_thumbnail(url=member.display_avatar)
        embed.set_footer(icon_url=interaction.user.display_avatar, text=f"Requested by {interaction.user}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Shows user avatar")
    @app_commands.describe(member="The member whose avatar to display")
    async def user_avatar(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        """Shows user avatar - simplified"""
        member = member or interaction.user
        
        embed = discord.Embed(
            title=f"{member.display_name}'s Avatar", 
            color=discord.Color.blue()
        )
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="server", description="Shows server information")
    async def server_info(self, interaction: discord.Interaction):
        """Shows server information - simplified"""
        guild = interaction.guild
        
        embed = discord.Embed(
            title=f"📊 {guild.name}",
            description=guild.description or "No description available.",
            color=discord.Color.blue()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        embed.add_field(name="👑 Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="👥 Members", value=f"{guild.member_count:,}", inline=True)
        embed.add_field(name="📅 Created", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="💬 Channels", value=len(guild.text_channels), inline=True)
        embed.add_field(name="🔊 Voice", value=len(guild.voice_channels), inline=True)
        
        if guild.premium_tier > 0:
            embed.add_field(name="⭐ Boost", value=f"Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=False)
        
        await interaction.response.send_message(embed=embed)

class FunCommands(commands.GroupCog, name="fun"):
    """Fun and entertainment commands for members"""
    
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="love", description="Send love to another member")
    @app_commands.describe(member="The member to send love to")
    async def send_love(self, interaction: discord.Interaction, member: discord.Member):
        """Send love message to another member"""
        embed = discord.Embed(
            title="💕 Love Message",
            description=f"{interaction.user.mention} sends love to {member.mention}! 💖",
            color=discord.Color.pink()
        )
        embed.set_footer(text="Spread the love!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="love_calc", description="Calculate love percentage")
    @app_commands.describe(member="The member to calculate love with")
    async def love_calculator(self, interaction: discord.Interaction, member: discord.Member):
        """Calculate love percentage between users"""
        # Create a deterministic but seemingly random percentage based on user IDs
        combined_ids = str(interaction.user.id) + str(member.id)
        hash_object = hashlib.md5(combined_ids.encode())
        percentage = int(hash_object.hexdigest(), 16) % 101
        
        # Create heart bar
        hearts = "💖" * (percentage // 10) + "🤍" * (10 - (percentage // 10))
        
        embed = discord.Embed(
            title="💕 Love Calculator",
            description=f"Love between {interaction.user.mention} and {member.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="Love Percentage", value=f"{percentage}%", inline=False)
        embed.add_field(name="Love Meter", value=hearts, inline=False)
        
        if percentage >= 80:
            embed.add_field(name="Result", value="💖 Perfect Match!", inline=False)
        elif percentage >= 60:
            embed.add_field(name="Result", value="💕 Great Compatibility!", inline=False)
        elif percentage >= 40:
            embed.add_field(name="Result", value="💛 Good Chemistry!", inline=False)
        elif percentage >= 20:
            embed.add_field(name="Result", value="💙 Friendship Potential!", inline=False)
        else:
            embed.add_field(name="Result", value="💔 Maybe just friends...", inline=False)
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="zodiac", description="Get your zodiac sign")
    @app_commands.describe(
        day="Your birth day (1-31)",
        month="Your birth month (1-12)", 
        year="Your birth year (optional)"
    )
    async def zodiac_sign(self, interaction: discord.Interaction, day: int, month: int, year: Optional[int] = None):
        """Get zodiac sign based on birthday - replaces birthday command"""
        try:
            # Validate day and month
            if not (1 <= day <= 31):
                await interaction.response.send_message("❌ Day must be between 1 and 31!", ephemeral=True)
                return
            if not (1 <= month <= 12):
                await interaction.response.send_message("❌ Month must be between 1 and 12!", ephemeral=True)
                return
                
            # Zodiac sign logic
            if (month == 3 and day >= 21) or (month == 4 and day <= 19):
                sign = "♈ Aries"
                traits = "Energetic, brave, and confident!"
            elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
                sign = "♉ Taurus"
                traits = "Reliable, practical, and determined!"
            elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
                sign = "♊ Gemini"
                traits = "Versatile, curious, and communicative!"
            elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
                sign = "♋ Cancer"
                traits = "Emotional, intuitive, and protective!"
            elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
                sign = "♌ Leo"
                traits = "Confident, generous, and creative!"
            elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
                sign = "♍ Virgo"
                traits = "Practical, analytical, and helpful!"
            elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
                sign = "♎ Libra"
                traits = "Diplomatic, fair-minded, and social!"
            elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
                sign = "♏ Scorpio"
                traits = "Passionate, resourceful, and determined!"
            elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
                sign = "♐ Sagittarius"
                traits = "Adventurous, optimistic, and philosophical!"
            elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
                sign = "♑ Capricorn"
                traits = "Ambitious, practical, and disciplined!"
            elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
                sign = "♒ Aquarius"
                traits = "Independent, innovative, and humanitarian!"
            else:  # Pisces
                sign = "♓ Pisces"
                traits = "Compassionate, artistic, and intuitive!"
                
            embed = discord.Embed(
                title="🔮 Your Zodiac Sign",
                color=discord.Color.purple()
            )
            embed.add_field(name="Sign", value=sign, inline=True)
            embed.add_field(name="Date", value=f"{day:02d}/{month:02d}" + (f"/{year}" if year else ""), inline=True)
            embed.add_field(name="Traits", value=traits, inline=False)
            embed.set_footer(text=f"Zodiac for {interaction.user.display_name}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message("❌ An error occurred while calculating your zodiac sign!", ephemeral=True)

class MediaCommands(commands.GroupCog, name="media"):
    """Media search and information commands"""
    
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="movie", description="Search for movie information")
    @app_commands.describe(name="The name of the movie to search for")
    async def movie_search(self, interaction: discord.Interaction, name: str):
        """Search for movie information - simplified"""
        embed = discord.Embed(
            title=f"🎬 Movie Search: {name}",
            description=f"Searching for movie information...",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="🔍 Search Results",
            value=f"Use IMDb or other movie databases to search for: `{name}`\n"
                 f"[Search on IMDb](https://www.imdb.com/find?q={name.replace(' ', '+')})",
            inline=False
        )
        embed.set_footer(text="Movie search simplified - use external links for detailed info")
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Search on IMDb",
            url=f"https://www.imdb.com/find?q={name.replace(' ', '+')}",
            style=discord.ButtonStyle.url,
            emoji="🎬"
        ))
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="tv", description="Search for TV show information")
    @app_commands.describe(name="The name of the TV show to search for")
    async def tv_search(self, interaction: discord.Interaction, name: str):
        """Search for TV show information - simplified"""
        embed = discord.Embed(
            title=f"📺 TV Show Search: {name}",
            description="Find information about this TV show:",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="🔍 Search Options",
            value=f"• [IMDb](https://www.imdb.com/find?q={name.replace(' ', '+')})\n"
                 f"• [TV Database](https://www.thetvdb.com/search?query={name.replace(' ', '+')})\n"
                 f"• [Rotten Tomatoes](https://www.rottentomatoes.com/search?search={name.replace(' ', '+')})",
            inline=False
        )
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Search on IMDb",
            url=f"https://www.imdb.com/find?q={name.replace(' ', '+')}",
            style=discord.ButtonStyle.url,
            emoji="📺"
        ))
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="game", description="Search for game information")
    @app_commands.describe(name="The name of the game to search for")
    async def game_search(self, interaction: discord.Interaction, name: str):
        """Search for game information - simplified"""
        embed = discord.Embed(
            title=f"🎮 Game Search: {name}",
            description=f"Find information about this game:",
            color=discord.Color.green()
        )
        embed.add_field(
            name="🔍 Search Options",
            value=f"• [Steam Store](https://store.steampowered.com/search/?term={name.replace(' ', '+')})\n"
                 f"• [Metacritic](https://www.metacritic.com/search/game/{name.replace(' ', '+')})\n"
                 f"• [IGN](https://www.ign.com/search?q={name.replace(' ', '+')})",
            inline=False
        )
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Steam Store",
            url=f"https://store.steampowered.com/search/?term={name.replace(' ', '+')}",
            style=discord.ButtonStyle.url,
            emoji="🎮"
        ))
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="spotify", description="Search Spotify")
    @app_commands.describe(query="Your search query")
    async def spotify_search(self, interaction: discord.Interaction, query: str):
        """Search Spotify for music - simplified"""
        embed = discord.Embed(
            title="🎵 Spotify Search",
            description=f"Search for: **{query}**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="🔍 Quick Access",
            value=f"Click the button below to search on Spotify Web Player",
            inline=False
        )
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Open in Spotify",
            url=f"https://open.spotify.com/search/{query.replace(' ', '%20')}",
            style=discord.ButtonStyle.url,
            emoji="🎵"
        ))
        
        await interaction.response.send_message(embed=embed, view=view)

class TextCommands(commands.GroupCog, name="text"):
    """Text manipulation and language commands"""
    
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="word", description="Get word definition and usage")
    @app_commands.describe(word="The word to define")
    async def word_definition(self, interaction: discord.Interaction, word: str):
        """Get word definition and example usage"""
        await interaction.response.defer()
        
        try:
            api_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            entry = data[0]
                            embed = discord.Embed(
                                title=f"📖 {entry.get('word', word).title()}",
                                color=discord.Color.orange()
                            )
                            
                            # Add phonetics if available
                            if entry.get('phonetics'):
                                for phonetic in entry.get('phonetics', []):
                                    if phonetic.get('text'):
                                        embed.add_field(name="Pronunciation", value=phonetic.get('text'), inline=True)
                                        break
                            
                            # Add meanings
                            meanings = entry.get('meanings', [])[:3]  # Limit to 3 meanings
                            for i, meaning in enumerate(meanings):
                                part_of_speech = meaning.get('partOfSpeech', 'Unknown')
                                definitions = meaning.get('definitions', [])[:2]  # Limit to 2 definitions per part
                                
                                for j, definition in enumerate(definitions):
                                    field_name = f"{part_of_speech.title()}" + (f" ({j+1})" if len(definitions) > 1 else "")
                                    field_value = definition.get('definition', 'No definition available')
                                    
                                    # Add example if available
                                    if definition.get('example'):
                                        field_value += f"\n*Example: {definition.get('example')}*"
                                    
                                    embed.add_field(name=field_name, value=field_value[:1024], inline=False)
                            
                            await interaction.followup.send(embed=embed)
                        else:
                            await interaction.followup.send(f"❌ No definition found for '{word}'!")
                    else:
                        await interaction.followup.send(f"❌ Word '{word}' not found in dictionary!")
        except Exception as e:
            await interaction.followup.send("❌ An error occurred while fetching the word definition!")

    @app_commands.command(name="sentence", description="Get example sentence with word")
    @app_commands.describe(word="The word to use in a sentence")
    async def example_sentence(self, interaction: discord.Interaction, word: str):
        """Generate example sentence with word"""
        await interaction.response.defer()
        
        try:
            api_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            # Look for examples in definitions
                            examples = []
                            for meaning in data[0].get('meanings', []):
                                for definition in meaning.get('definitions', []):
                                    if definition.get('example'):
                                        examples.append(definition.get('example'))
                            
                            if examples:
                                embed = discord.Embed(
                                    title=f"📝 Example Sentences for '{word}'",
                                    color=discord.Color.blue()
                                )
                                
                                # Show up to 3 examples
                                for i, example in enumerate(examples[:3], 1):
                                    embed.add_field(
                                        name=f"Example {i}",
                                        value=f"*{example}*",
                                        inline=False
                                    )
                                
                                await interaction.followup.send(embed=embed)
                            else:
                                await interaction.followup.send(f"❌ No example sentences found for '{word}'!")
                        else:
                            await interaction.followup.send(f"❌ Word '{word}' not found!")
                    else:
                        await interaction.followup.send(f"❌ Word '{word}' not found in dictionary!")
        except Exception as e:
            await interaction.followup.send("❌ An error occurred while fetching example sentences!")

    @app_commands.command(name="reverse", description="Reverse text")
    @app_commands.describe(text="The text to reverse")
    async def reverse_text(self, interaction: discord.Interaction, text: str):
        """Reverse the provided text"""
        if len(text) > 1000:
            await interaction.response.send_message("❌ Text is too long! Maximum 1000 characters.", ephemeral=True)
            return
            
        reversed_text = text[::-1]
        
        embed = discord.Embed(
            title="🔄 Text Reverser",
            color=discord.Color.purple()
        )
        embed.add_field(name="Original", value=f"```{text}```", inline=False)
        embed.add_field(name="Reversed", value=f"```{reversed_text}```", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="echo", description="Echo a message")
    @app_commands.describe(message="The message to echo")
    async def echo_message(self, interaction: discord.Interaction, message: str):
        """Echo/repeat a message"""
        if len(message) > 1500:
            await interaction.response.send_message("❌ Message is too long! Maximum 1500 characters.", ephemeral=True)
            return
            
        # Filter out mentions and links for safety
        safe_message = message.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')
        
        embed = discord.Embed(
            title="📢 Echo",
            description=safe_message,
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Echoed by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

class UtilityCommands(commands.GroupCog, name="utility"):
    """Utility commands for members"""
    
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="crypto", description="Get cryptocurrency price")
    @app_commands.describe(asset="The cryptocurrency symbol (e.g., bitcoin, ethereum)")
    async def crypto_price(self, interaction: discord.Interaction, asset: str):
        """Get cryptocurrency price - simplified"""
        embed = discord.Embed(
            title=f"💰 Crypto Search: {asset.upper()}",
            description=f"Check current prices for {asset}",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="🔍 Price Sources",
            value=f"• [CoinGecko](https://www.coingecko.com/en/coins/{asset.lower()})\n"
                 f"• [CoinMarketCap](https://coinmarketcap.com/currencies/{asset.lower()})\n"
                 f"• [Binance](https://www.binance.com/en/trade/{asset.upper()}_USDT)",
            inline=False
        )
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="View on CoinGecko",
            url=f"https://www.coingecko.com/en/coins/{asset.lower()}",
            style=discord.ButtonStyle.url,
            emoji="💰"
        ))
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="shorten", description="Shorten a URL")
    @app_commands.describe(url="The URL to shorten")
    async def shorten_url(self, interaction: discord.Interaction, url: str):
        """Shorten a long URL - simplified"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        embed = discord.Embed(
            title="🔗 URL Shortener",
            description="Use these services to shorten your URL:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Original URL", 
            value=url[:100] + "..." if len(url) > 100 else url, 
            inline=False
        )
        embed.add_field(
            name="🔗 Shortening Services",
            value="• [TinyURL](https://tinyurl.com/)\n• [Bit.ly](https://bitly.com/)\n• [Short.link](https://short.link/)",
            inline=False
        )
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Shorten with TinyURL",
            url=f"https://tinyurl.com/create.php?url={url}",
            style=discord.ButtonStyle.url,
            emoji="🔗"
        ))
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="poll", description="Create a poll")
    @app_commands.describe(
        question="The poll question",
        options="Poll options separated by commas"
    )
    async def create_poll(self, interaction: discord.Interaction, question: str, options: str):
        """Create a poll with multiple options"""
        option_list = [opt.strip() for opt in options.split(',') if opt.strip()]
        
        if len(option_list) < 2:
            await interaction.response.send_message("❌ Poll must have at least 2 options!", ephemeral=True)
            return
        if len(option_list) > 10:
            await interaction.response.send_message("❌ Poll can have maximum 10 options!", ephemeral=True)
            return
            
        # Emoji numbers for reactions
        emoji_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        
        embed = discord.Embed(
            title="📊 Poll",
            description=f"**{question}**",
            color=discord.Color.blue()
        )
        
        # Add options
        options_text = ""
        for i, option in enumerate(option_list):
            options_text += f"{emoji_numbers[i]} {option}\n"
        
        embed.add_field(name="Options", value=options_text, inline=False)
        embed.set_footer(text=f"Poll created by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
        
        # Add reactions
        message = await interaction.original_response()
        for i in range(len(option_list)):
            await message.add_reaction(emoji_numbers[i])

    @app_commands.command(name="privacy", description="View bot privacy policy")
    async def privacy_policy(self, interaction: discord.Interaction):
        """Display the bot's privacy policy"""
        embed = discord.Embed(
            title="Privacy Policy for Contro",
            description="Effective Date: 10.06.2025",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="1. Introduction",
            value=(
                "Welcome to Contro. This Privacy Policy explains how we collect, use, "
                "and protect your information when you use our Discord bot. By using Contro, "
                "you agree to the collection and use of information in accordance with this policy. "
                "Contro is developed as a hobby project to enhance software development experience, "
                "not for commercial purposes."
            ),
            inline=False
        )
        
        embed.add_field(
            name="2. Information We Collect",
            value=(
                "- **User Data:** Discord user ID, username, display name, and avatar for personalized services\n"
                "- **Message Content:** Command inputs and context for processing (not stored permanently)\n"
                "- **Guild Data:** Server ID, name, member count, channels, and roles for bot functionality\n"
                "- **Activity Data:** Game statistics, command usage, and interaction patterns for features\n"
                "- **Settings Data:** User preferences, server configurations, and customization options"
            ),
            inline=False
        )
        
        embed.add_field(
            name="3. Data Protection & Non-Commercial Use",
            value=(
                "- **No Sale:** Your data is NEVER sold or shared with third parties for profit\n"
                "- **Hobby Project:** Contro is developed for learning and community benefit, not commercial gain\n"
                "- **Purpose Limitation:** Data used solely for stated purposes, never for advertising or marketing\n"
                "- **Security:** Data stored securely with encryption and access controls"
            ),
            inline=False
        )
        
        embed.add_field(
            name="4. Contact Us",
            value="If you have any questions or concerns about this Privacy Policy, please contact us at bergasoft@pm.me.",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

# Command group migration mapping
COMMAND_MIGRATIONS = {
    # From utility.py
    "whois": ("info", "user"),
    "avatar": ("info", "avatar"), 
    "server": ("info", "server"),
    "poll": ("utility", "poll"),
    "privacy_policy": ("utility", "privacy"),
    
    # From fun.py
    "love": ("fun", "love"),
    "love_calculator": ("fun", "love_calc"),
    "birthday": ("fun", "zodiac"),
    "movie": ("media", "movie"),
    "tv": ("media", "tv"),
    "game": ("media", "game"),
    "spotify": ("media", "spotify"),
    "word": ("text", "word"),
    "sentence": ("text", "sentence"),
    "reverse": ("text", "reverse"),
    "echo": ("text", "echo"),
    "crypto": ("utility", "crypto"),
    "shorten": ("utility", "shorten"),
}

# Commands that should remain as standalone (not in groups)
STANDALONE_COMMANDS = [
    "ping",
    "support", 
    "version",
    "spin",
    "bump",
    "changelog",
    "roadmap"
]
