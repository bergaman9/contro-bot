import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import json
import os
import logging
import datetime
from typing import Dict, List, Optional, Union
import time
import random
from dotenv import load_dotenv

from src.utils.core.formatting import create_embed
from src.utils.database.connection import initialize_mongodb, is_db_available
from src.utils.views.perplexity_settings import PerplexitySettingsView

# Configure logger
logger = logging.getLogger('perplexity_chat')

# Load environment variables
load_dotenv()
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

class PerplexityChat(commands.Cog):
    """🤖 AI Chat with Perplexity API
    
    Interact with an advanced AI assistant powered by Perplexity.
    Features include:
    • 🧠 AI responses using the Solar model
    • 💳 Credit system for fair usage
    • ⚙️ Customizable server settings
    • 🌐 Internet-connected responses
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        self.active_chats = {}
        self.default_credits = 10  # Default credits for new users
        self.default_daily_reset = True  # Reset credits daily by default
        self.default_max_credits = 30  # Maximum credits users can accumulate
        self.streaming_responses = True  # Stream responses by default
        
        # Initialize background tasks
        self.credit_reset_task = self.bot.loop.create_task(self.reset_credits_daily())
        self.cleanup_task = self.bot.loop.create_task(self.cleanup_old_chats())
    
    async def cog_unload(self):
        """Clean up tasks when cog is unloaded"""
        if self.credit_reset_task:
            self.credit_reset_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
    
    async def reset_credits_daily(self):
        """Reset credits daily at midnight for servers that have this enabled"""
        while not self.bot.is_closed():
            try:
                # Find the time until next midnight
                now = datetime.datetime.now()
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                seconds_until_midnight = (tomorrow - now).total_seconds()
                
                # Sleep until midnight
                await asyncio.sleep(seconds_until_midnight)
                
                # Reset credits for all servers with daily reset enabled
                server_configs = self.mongo_db.perplexity_config.find({"daily_reset": True})
                
                async for config in server_configs:
                    guild_id = config["guild_id"]
                    default_credits = config.get("default_credits", self.default_credits)
                    
                    # Update all users' credits in this guild
                    await self.mongo_db.perplexity_credits.update_many(
                        {"guild_id": guild_id},
                        {"$set": {"credits": default_credits}}
                    )
                    
                    logger.info(f"Reset credits for guild {guild_id}")
                
            except Exception as e:
                logger.error(f"Error in reset_credits_daily: {e}")
                await asyncio.sleep(3600)  # Wait an hour and try again
    
    async def cleanup_old_chats(self):
        """Clean up inactive chats to free memory"""
        while not self.bot.is_closed():
            try:
                current_time = time.time()
                to_remove = []
                
                for chat_id, chat_data in self.active_chats.items():
                    # Remove chats inactive for more than 30 minutes
                    if current_time - chat_data["last_activity"] > 1800:
                        to_remove.append(chat_id)
                
                for chat_id in to_remove:
                    self.active_chats.pop(chat_id, None)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in cleanup_old_chats: {e}")
                await asyncio.sleep(300)
    
    async def get_user_credits(self, guild_id: int, user_id: int) -> int:
        """Get user's remaining credits"""
        user_data = await self.mongo_db.perplexity_credits.find_one({
            "guild_id": str(guild_id),
            "user_id": str(user_id)
        })
        
        if not user_data:
            # Get server's default credit amount
            server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(guild_id)})
            default_credits = server_config.get("default_credits", self.default_credits) if server_config else self.default_credits
            
            # Create new user entry
            await self.mongo_db.perplexity_credits.insert_one({
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "credits": default_credits,
                "last_used": datetime.datetime.now().isoformat()
            })
            return default_credits
        
        return user_data.get("credits", 0)
    
    async def use_credit(self, guild_id: int, user_id: int) -> bool:
        """Use one credit for a user. Returns True if successful, False if not enough credits."""
        credits = await self.get_user_credits(guild_id, user_id)
        
        if credits <= 0:
            return False
        
        # Decrease credits by 1
        await self.mongo_db.perplexity_credits.update_one(
            {"guild_id": str(guild_id), "user_id": str(user_id)},
            {"$inc": {"credits": -1}, "$set": {"last_used": datetime.datetime.now().isoformat()}}
        )
        
        return True
    
    async def add_credits(self, guild_id: int, user_id: int, amount: int) -> int:
        """Add credits to a user. Returns new credit amount."""
        # Get server's max credit limit
        server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(guild_id)})
        max_credits = server_config.get("max_credits", self.default_max_credits) if server_config else self.default_max_credits
        
        # Get current credits
        current_credits = await self.get_user_credits(guild_id, user_id)
        
        # Calculate new amount, respecting the maximum
        new_amount = min(current_credits + amount, max_credits)
        
        # Update in database
        await self.mongo_db.perplexity_credits.update_one(
            {"guild_id": str(guild_id), "user_id": str(user_id)},
            {"$set": {"credits": new_amount}}
        )
        
        return new_amount
    
    async def get_server_api_key(self, guild_id: int) -> str:
        """Get server-specific API key if set, otherwise use default"""
        server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(guild_id)})
        
        if server_config and "api_key" in server_config and server_config["api_key"]:
            return server_config["api_key"]
        
        return PERPLEXITY_API_KEY
    
    async def call_perplexity_api(self, prompt: str, guild_id: int, streaming=False):
        """Call the Perplexity API with the given prompt"""
        api_key = await self.get_server_api_key(guild_id)
        
        if not api_key:
            raise ValueError("No Perplexity API key configured")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "sonar-medium-online",  # Using Solar model with internet access
            "messages": [{"role": "user", "content": prompt}],
            "stream": streaming
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"API error: {response.status} - {error_text}")
                
                if streaming:
                    return response  # Return the response object for streaming
                else:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
    
    # Chat command that responds to any message with a reply using AI
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if this is a DM or a server message
        if not message.guild:
            return  # Ignore DMs for now
        
        # Check if the message is a reply to the bot
        if not (message.reference and message.reference.resolved and 
                message.reference.resolved.author.id == self.bot.user.id):
            return
        
        # Get server settings
        server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(message.guild.id)})
        
        # Check if Perplexity is enabled for this server
        if not server_config or not server_config.get("enabled", True):
            return
        
        # Check if the channel is allowed
        allowed_channels = server_config.get("allowed_channels", [])
        if allowed_channels and str(message.channel.id) not in allowed_channels:
            return
        
        # Check if user has credits
        if not await self.use_credit(message.guild.id, message.author.id):
            # No credits left
            embed = discord.Embed(
                title="❌ Kredi Limiti Aşıldı",
                description="AI sohbet kredileriniz tükendi!",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Nasıl Kredi Kazanılır?",
                value="[Top.gg'de oy vererek](https://top.gg/bot/your-bot-id/vote) her gün 5 kredi kazanabilirsiniz.",
                inline=False
            )
            return await message.reply(embed=embed)
        
        # Typing indicator while processing
        async with message.channel.typing():
            try:
                # Check if streaming is enabled
                streaming = server_config.get("streaming", self.streaming_responses)
                
                if streaming:
                    # Send initial message that we'll edit
                    response_message = await message.reply("*AI düşünüyor...*")
                    
                    # Get streaming response
                    response = await self.call_perplexity_api(message.content, message.guild.id, streaming=True)
                    
                    # Process the streaming response
                    full_response = ""
                    current_chunk = ""
                    last_update = time.time()
                    
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8').strip("data: "))
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0]["delta"]
                                    if "content" in delta:
                                        full_response += delta["content"]
                                        current_chunk += delta["content"]
                                        
                                        # Update message every 1.5 seconds or when chunk gets large
                                        current_time = time.time()
                                        if current_time - last_update > 1.5 or len(current_chunk) > 50:
                                            # Trim the message if it's getting too long for Discord
                                            display_response = full_response
                                            if len(display_response) > 1950:
                                                display_response = full_response[-1950:] + "..."
                                                
                                            await response_message.edit(content=display_response)
                                            last_update = current_time
                                            current_chunk = ""
                            except Exception as e:
                                logger.error(f"Error processing streaming chunk: {e}")
                    
                    # Final update with the complete response
                    # Break the response into multiple messages if too long
                    if len(full_response) > 2000:
                        chunks = [full_response[i:i+1990] for i in range(0, len(full_response), 1990)]
                        await response_message.edit(content=chunks[0])
                        
                        for chunk in chunks[1:]:
                            await message.channel.send(chunk)
                    else:
                        await response_message.edit(content=full_response)
                else:
                    # Non-streaming mode
                    response_text = await self.call_perplexity_api(message.content, message.guild.id)
                    
                    # Split long responses
                    if len(response_text) > 2000:
                        chunks = [response_text[i:i+1990] for i in range(0, len(response_text), 1990)]
                        for i, chunk in enumerate(chunks):
                            if i == 0:
                                await message.reply(chunk)
                            else:
                                await message.channel.send(chunk)
                    else:
                        await message.reply(response_text)
            
            except ValueError as ve:
                await message.reply(f"❌ Hata: {str(ve)}")
            except Exception as e:
                logger.error(f"Error in AI chat: {e}")
                await message.reply("❌ AI yanıtı alınırken bir hata oluştu. Lütfen daha sonra tekrar deneyin.")

    @commands.hybrid_group(name="ai", description="AI sohbet ve ayarları")
    async def ai(self, ctx):
        """AI sohbet komutları"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🤖 AI Sohbet Yardımı",
                description="AI ile sohbet etmek için botun mesajına yanıt verin veya aşağıdaki komutları kullanın.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Komutlar",
                value=(
                    "`/ai ask [soru]` - AI'ya soru sorun\n"
                    "`/ai credits` - Kalan kredilerinizi görün\n"
                    "`/ai settings` - AI ayarlarını yapılandırın (Admin)"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Kredi Sistemi",
                value="Her AI yanıtı 1 kredi harcamanızı gerektirir. Krediler günlük olarak yenilenebilir.",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    @ai.command(name="credits", description="Kalan AI kredilerinizi görün")
    async def credits(self, ctx):
        """Kalan AI kredilerinizi görün ve kredi kazanma yollarını öğrenin"""
        # Get user credits
        credits = await self.get_user_credits(ctx.guild.id, ctx.author.id)
        
        # Get server config for credit settings
        server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(ctx.guild.id)})
        
        default_credits = server_config.get("default_credits", self.default_credits) if server_config else self.default_credits
        max_credits = server_config.get("max_credits", self.default_max_credits) if server_config else self.default_max_credits
        reset_daily = server_config.get("daily_reset", self.default_daily_reset) if server_config else self.default_daily_reset
        
        # Create credits info embed
        embed = discord.Embed(
            title="💳 AI Sohbet Kredileri",
            description=f"**{ctx.author.display_name}**, mevcut AI sohbet kredileriniz: **{credits}**",
            color=discord.Color.blue()
        )
        
        # Add credit info
        embed.add_field(
            name="💸 Kredi Bilgileri",
            value=(
                f"\u2022 Her AI yanıtı **1 kredi** harcamanızı gerektirir\n"
                f"\u2022 Günlük başlangıç kredisi: **{default_credits}**\n"
                f"\u2022 Maksimum biriktirebileceğiniz kredi: **{max_credits}**\n"
                f"\u2022 Günlük sıfırlama: **{'Aktif' if reset_daily else 'Devre dışı'}**"
            ),
            inline=False
        )
        
        # Add how to earn more credits
        embed.add_field(
            name="💰 Nasıl Daha Fazla Kredi Kazanılır?",
            value=(
                "\u2022 [Top.gg'de oy vererek](https://top.gg/bot/your-bot-id/vote) **5 kredi** kazanabilirsiniz.\n"
                "\u2022 Sunucu yöneticileri size ekstra kredi verebilir.\n"
                "\u2022 Bot sahibine destek olarak özel avantajlar kazanabilirsiniz."
            ),
            inline=False
        )
        
        # Add footer with tip
        embed.set_footer(text="İpucu: AI ile sohbet etmek için botun herhangi bir mesajına yanıt verin.")
        
        await ctx.send(embed=embed, ephemeral=True)
    
    @ai.command(name="ask", description="AI'ya soru sorun")
    @app_commands.describe(soru="AI'ya sormak istediğiniz soru")
    async def ask(self, ctx, *, soru: str):
        """AI'ya direkt soru sorun"""
        # Check if user has credits
        if not await self.use_credit(ctx.guild.id, ctx.author.id):
            # No credits left
            embed = discord.Embed(
                title="❌ Kredi Limiti Aşıldı",
                description="AI sohbet kredileriniz tükendi!",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Nasıl Kredi Kazanılır?",
                value="[Top.gg'de oy vererek](https://top.gg/bot/your-bot-id/vote) her gün 5 kredi kazanabilirsiniz.",
                inline=False
            )
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Get server settings
        server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(ctx.guild.id)})
        
        # Typing indicator while processing
        async with ctx.typing():
            try:
                # Check if streaming is enabled
                streaming = server_config.get("streaming", self.streaming_responses) if server_config else self.streaming_responses
                
                if streaming:
                    # Send initial message that we'll edit
                    await ctx.defer()
                    response_message = await ctx.send("*AI düşünüyor...*")
                    
                    # Get streaming response
                    response = await self.call_perplexity_api(soru, ctx.guild.id, streaming=True)
                    
                    # Process the streaming response
                    full_response = ""
                    current_chunk = ""
                    last_update = time.time()
                    
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8').strip("data: "))
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0]["delta"]
                                    if "content" in delta:
                                        full_response += delta["content"]
                                        current_chunk += delta["content"]
                                        
                                        # Update message every 1.5 seconds or when chunk gets large
                                        current_time = time.time()
                                        if current_time - last_update > 1.5 or len(current_chunk) > 50:
                                            # Trim the message if it's getting too long for Discord
                                            display_response = full_response
                                            if len(display_response) > 1950:
                                                display_response = full_response[-1950:] + "..."
                                                
                                            await response_message.edit(content=display_response)
                                            last_update = current_time
                                            current_chunk = ""
                            except Exception as e:
                                logger.error(f"Error processing streaming chunk: {e}")
                    
                    # Final update with the complete response
                    # Break the response into multiple messages if too long
                    if len(full_response) > 2000:
                        chunks = [full_response[i:i+1990] for i in range(0, len(full_response), 1990)]
                        await response_message.edit(content=chunks[0])
                        
                        for chunk in chunks[1:]:
                            await ctx.send(chunk)
                    else:
                        await response_message.edit(content=full_response)
                else:
                    # Non-streaming mode
                    await ctx.defer()
                    response_text = await self.call_perplexity_api(soru, ctx.guild.id)
                    
                    # Split long responses
                    if len(response_text) > 2000:
                        chunks = [response_text[i:i+1990] for i in range(0, len(response_text), 1990)]
                        for i, chunk in enumerate(chunks):
                            if i == 0:
                                await ctx.send(chunk)
                            else:
                                await ctx.send(chunk)
                    else:
                        await ctx.send(response_text)
            
            except ValueError as ve:
                await ctx.send(f"❌ Hata: {str(ve)}", ephemeral=True)
            except Exception as e:
                logger.error(f"Error in AI chat: {e}")
                await ctx.send("❌ AI yanıtı alınırken bir hata oluştu. Lütfen daha sonra tekrar deneyin.", ephemeral=True)
    
    @ai.command(name="settings", description="AI sohbet ayarlarını yapılandırın")
    @commands.has_permissions(administrator=True)
    async def settings(self, ctx):
        """Configure AI chat settings for your server"""
        # Check if MongoDB is available
        if not await is_db_available():
            return await ctx.send(
                embed=create_embed("❌ Veritabanı bağlantısı kurulamadı. Lütfen daha sonra tekrar deneyin.", discord.Color.red()),
                ephemeral=True
            )
        
        # Get current settings
        server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(ctx.guild.id)})
        
        # Set default values if config doesn't exist
        if not server_config:
            server_config = {
                "guild_id": str(ctx.guild.id),
                "enabled": True,
                "streaming": self.streaming_responses,
                "default_credits": self.default_credits,
                "max_credits": self.default_max_credits,
                "daily_reset": self.default_daily_reset,
                "allowed_channels": []
            }
            await self.mongo_db.perplexity_config.insert_one(server_config)
        
        # Create settings embed
        embed = discord.Embed(
            title="🤖 AI Sohbet Ayarları",
            description="Sunucunuz için AI sohbet sistemini yapılandırın.",
            color=discord.Color.blue()
        )
        
        # Display current settings
        embed.add_field(
            name="💳 Kredi Ayarları",
            value=f"Başlangıç Kredisi: **{server_config.get('default_credits', self.default_credits)}**\n"
                  f"Maksimum Kredi: **{server_config.get('max_credits', self.default_max_credits)}**\n"
                  f"Günlük Sıfırlama: **{'Aktif' if server_config.get('daily_reset', self.default_daily_reset) else 'Devre dışı'}**",
            inline=False
        )
        
        # API Key status
        api_key = server_config.get("api_key", None)
        embed.add_field(
            name="🔑 API Anahtarı",
            value=f"Durum: **{'Ayarlandı' if api_key else 'Ayarlanmadı (Varsayılan kullanılıyor)'}**",
            inline=False
        )
        
        # Streaming mode
        streaming = server_config.get("streaming", self.streaming_responses)
        embed.add_field(
            name="📡 Yanıt Modu",
            value=f"**{'Akan Yanıt Modu' if streaming else 'Tam Yanıt Modu'}**",
            inline=False
        )
        
        # AI Status
        enabled = server_config.get("enabled", True)
        embed.add_field(
            name="⚡ AI Durumu",
            value=f"**{'Aktif' if enabled else 'Devre dışı'}**",
            inline=False
        )
        
        # Channel restrictions
        allowed_channels = server_config.get("allowed_channels", [])
        channel_status = "Tüm kanallarda kullanılabilir"
        if allowed_channels:
            channel_count = len(allowed_channels)
            channel_status = f"**{channel_count}** kanalda kullanılabilir"
        
        embed.add_field(
            name="📰 Kanal İzinleri",
            value=channel_status,
            inline=False
        )
        
        # Create settings view
        view = PerplexitySettingsView(self.bot)
        
        # Send settings panel
        await ctx.send(embed=embed, view=view, ephemeral=True)

# Setup function
async def setup(bot):
    await bot.add_cog(PerplexityChat(bot))
    logger.info("Perplexity Chat cog loaded")
