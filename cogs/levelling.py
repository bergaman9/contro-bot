import discord
from discord.ext import commands, tasks
import os
import logging
import datetime
import asyncio
from typing import Optional

from utils.core.formatting import create_embed
from utils.database.connection import initialize_mongodb
from utils.community.turkoyto.xp_manager import XPManager, XP_VOICE_PER_MINUTE
from utils.community.turkoyto.card_renderer import create_level_card, get_level_scheme, scheme_to_discord_color

logger = logging.getLogger('levelling')

class Levelling(commands.Cog):
    """General levelling system that can be configured per guild"""
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = None
        self.setup_database()
        
        self.voice_time_tracker = {}  # Track users in voice channels
        
        # Initialize the XP manager
        self.xp_manager = XPManager()
        
        # Start checking voice activity
        self.check_voice_activity.start()
        
        # Create necessary directories
        os.makedirs("data/Temp", exist_ok=True)
        
        logger.info("Levelling cog initialized")

    def setup_database(self):
        """Setup database connections"""
        try:
            # Get async database from bot if available
            if hasattr(self.bot, 'async_db') and self.bot.async_db:
                self.mongo_db = self.bot.async_db
                logger.info("Using bot's async database connection")
                # Update XP manager immediately if we have the DB
                if self.xp_manager:
                    self.xp_manager.set_mongo_db(self.mongo_db)
            else:
                # Schedule database initialization for when bot is ready
                asyncio.create_task(self.delayed_database_setup())
                logger.info("Scheduled delayed database setup")
        except Exception as e:
            logger.error(f"Error setting up database: {e}")

    async def delayed_database_setup(self):
        """Setup database after bot is ready"""
        try:
            await self.bot.wait_until_ready()
            
            # Try to get database from bot first
            if hasattr(self.bot, 'async_db') and self.bot.async_db is not None:
                self.mongo_db = self.bot.async_db
                logger.info("Got async database from bot after ready")
            else:
                # Try to initialize directly
                try:
                    self.mongo_db = initialize_mongodb()
                    if self.mongo_db is not None:
                        logger.info("Initialized MongoDB connection directly")
                    else:
                        logger.error("Failed to initialize MongoDB connection")
                except Exception as e:
                    logger.error(f"Error initializing MongoDB: {e}")
            
            # Update XP manager with database
            if self.mongo_db is not None and self.xp_manager:
                self.xp_manager.set_mongo_db(self.mongo_db)
                logger.info("Updated XP manager with database connection")
                
        except Exception as e:
            logger.error(f"Error in delayed database setup: {e}")

    async def ensure_database(self):
        """Ensure database connection is available"""
        if self.mongo_db is None:
            # Try to get from bot first
            if hasattr(self.bot, 'async_db') and self.bot.async_db is not None:
                self.mongo_db = self.bot.async_db
                logger.info("Retrieved database from bot")
            else:
                # Try to initialize
                try:
                    self.mongo_db = initialize_mongodb()
                    if self.mongo_db is not None:
                        logger.info("Database connection established for Levelling")
                    else:
                        logger.error("Failed to get database connection")
                except Exception as e:
                    logger.error(f"Error ensuring database: {e}")
            
            # Update XP manager if we got a connection
            if self.mongo_db is not None and self.xp_manager:
                self.xp_manager.set_mongo_db(self.mongo_db)
                
        return self.mongo_db

    async def get_guild_settings(self, guild_id):
        """Get levelling settings for a guild"""
        try:
            await self.ensure_database()
            if self.mongo_db is None:
                return {}
                
            settings = await self.mongo_db.levelling_settings.find_one({"guild_id": int(guild_id)})
            if settings is None:
                # Return default settings
                return {
                    "enabled": True,
                    "message_xp_enabled": True,
                    "voice_xp_enabled": True,
                    "level_up_notifications": True,
                    "level_up_channel_id": None,
                    "xp_multiplier": 1.0,
                    "voice_xp_multiplier": 1.0,
                    "cooldown_seconds": 60,
                    "max_level": 100
                }
            return settings
        except Exception as e:
            logger.error(f"Error getting guild settings: {e}")
            return {}

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        try:
            self.check_voice_activity.cancel()
            logger.info("Levelling cog unloaded and tasks stopped")
        except Exception as e:
            logger.error(f"Error during cog unload: {e}")

    @tasks.loop(minutes=1)
    async def check_voice_activity(self):
        """Check and reward XP for users in voice channels"""
        try:
            logger.debug("Running voice activity check")
            users_processed = 0
            users_awarded = 0
            
            for guild in self.bot.guilds:
                # Check if levelling is enabled for this guild
                settings = await self.get_guild_settings(guild.id)
                if not settings.get("enabled", True) or not settings.get("voice_xp_enabled", True):
                    continue
                
                for vc in guild.voice_channels:
                    for member in vc.members:
                        # Skip AFK members and bots
                        if not hasattr(member, 'voice') or not member.voice:
                            continue
                        
                        if member.voice.afk or member.bot:
                            continue
                            
                        # Skip muted members (optional)
                        if member.voice.self_mute and member.voice.self_deaf:
                            continue
                        
                        users_processed += 1
                        
                        # Track time in voice
                        if member.id not in self.voice_time_tracker:
                            self.voice_time_tracker[member.id] = datetime.datetime.now()
                            logger.debug(f"Started tracking voice time for {member.name} ({member.id})")
                            continue  # Skip this iteration since we just started tracking
                        
                        # Calculate time spent in voice
                        time_now = datetime.datetime.now()
                        time_diff = time_now - self.voice_time_tracker[member.id]
                        minutes = time_diff.total_seconds() / 60
                        
                        # Award XP for voice activity
                        if minutes >= 1:
                            voice_multiplier = settings.get("voice_xp_multiplier", 1.0)
                            xp_gain = int(await self.xp_manager.calculate_voice_xp(minutes) * voice_multiplier)
                            try:
                                user_data = await self.xp_manager.add_xp(
                                    member, 
                                    xp_gain, 
                                    "voice", 
                                    self.send_level_up_notification if settings.get("level_up_notifications", True) else None
                                )
                                
                                if user_data:
                                    logger.info(f"Awarded {xp_gain} XP to {member.name} for {minutes:.1f} minutes in voice. New total: {user_data.get('xp', 0)}")
                                    users_awarded += 1
                                else:
                                    logger.warning(f"Voice XP calculated but not added to database for {member.name}")
                                    
                            except Exception as e:
                                logger.error(f"Error adding voice XP to database for {member.name}: {e}")
                                continue
                                
                            # Reset the timer
                            self.voice_time_tracker[member.id] = time_now
            
            if users_processed > 0:
                logger.info(f"Voice activity check completed. Processed {users_processed} users, awarded XP to {users_awarded} users.")
            
        except Exception as e:
            logger.error(f"Voice XP error: {e}", exc_info=True)

    @check_voice_activity.before_loop
    async def before_voice_check(self):
        """Wait until the bot is ready before starting the loop"""
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message):
        """Process messages and award XP based on content"""
        # Skip if message is from a bot or not in a guild
        if message.author.bot or not message.guild:
            return
        
        try:
            # Check if levelling is enabled for this guild
            settings = await self.get_guild_settings(message.guild.id)
            if not settings.get("enabled", True) or not settings.get("message_xp_enabled", True):
                return
            
            # Get the member who sent the message
            member = message.author
            
            # Check if user is on XP cooldown
            cooldown = settings.get("cooldown_seconds", 60)
            if self.xp_manager.is_on_cooldown(member.id):
                return
            
            # Calculate XP based on message content
            base_xp = await self.xp_manager.calculate_message_xp(message)
            xp_multiplier = settings.get("xp_multiplier", 1.0)
            xp_gain = int(base_xp * xp_multiplier)
            
            logger.info(f"Calculated {xp_gain} XP for message from {member.name} ({member.id})")
            
            # Add XP to the user
            if xp_gain > 0:
                try:
                    user_data = await self.xp_manager.add_xp(
                        member, 
                        xp_gain, 
                        "message", 
                        self.send_level_up_notification if settings.get("level_up_notifications", True) else None
                    )
                    
                    if user_data:
                        logger.info(f"Successfully awarded {xp_gain} XP to {member.name} (ID: {member.id}). New total: {user_data.get('xp', 0)}")
                    else:
                        logger.warning(f"XP was calculated but not added to database for {member.name} (ID: {member.id})")
                except Exception as e:
                    logger.error(f"Error adding XP to database: {e}", exc_info=True)
                    # We'll return here to avoid setting cooldown on failed XP additions
                    return
                
                # Set cooldown to prevent XP farming
                self.xp_manager.set_cooldown(member.id)
            else:
                logger.debug(f"No XP awarded to {member.name} for message - calculated XP was {xp_gain}")
            
        except Exception as e:
            logger.error(f"Error processing message for XP: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates"""
        try:
            # Skip bots
            if member.bot:
                return
            
            # Check if levelling is enabled for this guild
            settings = await self.get_guild_settings(member.guild.id)
            if not settings.get("enabled", True) or not settings.get("voice_xp_enabled", True):
                return
                
            # If user disconnected or moved to AFK
            if before.channel and (not after.channel or after.afk):
                # User disconnected, record the voice time
                if member.id in self.voice_time_tracker:
                    time_spent = datetime.datetime.now() - self.voice_time_tracker[member.id]
                    minutes = time_spent.total_seconds() / 60
                    
                    # Update voice minutes in database if significant time spent
                    if minutes >= 1:
                        logger.info(f"User {member.name} spent {minutes:.1f} minutes in voice before disconnecting.")
                        
                        # Add voice minutes to database
                        try:
                            # Use XP manager to handle this
                            voice_multiplier = settings.get("voice_xp_multiplier", 1.0)
                            voice_xp = int(await self.xp_manager.calculate_voice_xp(minutes) * voice_multiplier)
                            await self.xp_manager.add_xp(
                                member, 
                                voice_xp, 
                                "voice_exit", 
                                self.send_level_up_notification if settings.get("level_up_notifications", True) else None
                            )
                        except Exception as e:
                            logger.error(f"Error updating voice minutes for {member.name}: {e}")
                    
                    # Remove user from tracker
                    del self.voice_time_tracker[member.id]
            
            # If user joined a voice channel and is not in tracker yet
            elif after.channel and not after.afk and member.id not in self.voice_time_tracker:
                self.voice_time_tracker[member.id] = datetime.datetime.now()
                logger.info(f"Started tracking voice time for {member.name} ({member.id})")
                
        except Exception as e:
            logger.error(f"Error in voice state update: {e}", exc_info=True)

    async def send_level_up_notification(self, member, user_data):
        """Send a notification when user levels up"""
        try:
            settings = await self.get_guild_settings(member.guild.id)
            if not settings.get("level_up_notifications", True):
                return
                
            new_level = user_data.get('level', 0)
            
            # Get level up channel or use a default channel
            channel_id = settings.get("level_up_channel_id")
            channel = None
            
            if channel_id:
                channel = member.guild.get_channel(int(channel_id))
            
            # If no specific channel is set, try to find a general channel
            if not channel:
                # Try to find a general/chat/levelling channel
                for ch in member.guild.text_channels:
                    if any(name in ch.name.lower() for name in ['general', 'chat', 'level', 'rank']):
                        channel = ch
                        break
                
                # If still no channel found, use the first available text channel
                if not channel and member.guild.text_channels:
                    channel = member.guild.text_channels[0]
            
            if channel:
                # Get level scheme for colors
                scheme = get_level_scheme(new_level)
                embed_color = scheme_to_discord_color(scheme)
                
                embed = discord.Embed(
                    title="🎉 Level Up!",
                    description=f"{member.mention} reached **Level {new_level}**!",
                    color=embed_color
                )
                
                embed.add_field(
                    name="Current XP", 
                    value=f"**{user_data.get('xp', 0):,}**", 
                    inline=True
                )
                
                embed.add_field(
                    name="Next Level XP", 
                    value=f"**{user_data.get('next_level_xp', 0):,}**", 
                    inline=True
                )
                
                if member.avatar:
                    embed.set_thumbnail(url=member.avatar.url)
                
                await channel.send(embed=embed)
                logger.info(f"Sent level up notification for {member.name} to level {new_level}")
            else:
                logger.warning(f"No channel found to send level up notification for {member.name}")
                
        except Exception as e:
            logger.error(f"Error sending level up notification: {e}", exc_info=True)

    @commands.hybrid_command(name="level", aliases=["rank"], description="Show user's level card")
    async def level(self, ctx, member: discord.Member = None):
        """
        Show user's level card.
        
        Parameters
        ----------
        member: discord.Member
            Optional - User whose level card to show. If not specified, shows command user's card.
        """
        try:
            # Check if levelling is enabled
            settings = await self.get_guild_settings(ctx.guild.id)
            if not settings.get("enabled", True):
                await ctx.send("Levelling system is disabled in this server.", ephemeral=True)
                return
            
            # If no member is provided, use the command invoker
            if member is None:
                member = ctx.author

            # Let the user know we're processing their request
            if hasattr(ctx, 'interaction') and ctx.interaction is not None:
                await ctx.defer()
            else:
                await ctx.send("Level card is being prepared...", delete_after=3)

            # Check MongoDB connection
            if self.mongo_db is None:
                logger.error("MongoDB is not initialized in Levelling cog")
                # Try to re-initialize
                self.mongo_db = initialize_mongodb()
                # Also update XP manager's connection
                self.xp_manager.mongo_db = self.mongo_db
            
            # Use XPManager to create the level card
            card_path = await self.xp_manager.create_and_render_level_card(
                self.bot,
                member,
                guild=ctx.guild
            )

            if card_path:
                # Get the filename from the path
                output_filename = os.path.basename(card_path)
                
                # Create a file for Discord
                file = discord.File(card_path, filename=output_filename)
                
                # Send only the file without embed
                await ctx.send(file=file)
                
                # Clean up the temporary file
                try:
                    os.remove(card_path)
                    logger.info(f"Removed temporary card file: {card_path}")
                except OSError as e:
                    logger.error(f"Error removing temporary card file {card_path}: {e}")
            else:
                await ctx.send("An error occurred while creating the level card.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in level command for user {member.id if member else 'None'}: {e}", exc_info=True)
            await ctx.send("An error occurred while showing the level card.", ephemeral=True)

    @commands.hybrid_command(name="levelinfo", aliases=["levelstats"], description="Show detailed level information")
    async def levelinfo(self, ctx, member: discord.Member = None):
        """
        Show detailed level information for a user.
        
        Parameters
        ----------
        member: discord.Member
            Optional - User whose information to show. If not specified, shows command user's info.
        """
        try:
            # Check if levelling is enabled
            settings = await self.get_guild_settings(ctx.guild.id)
            if not settings.get("enabled", True):
                await ctx.send("Levelling system is disabled in this server.", ephemeral=True)
                return
            
            # If no member is provided, use the command invoker
            if member is None:
                member = ctx.author

            # Let the user know we're processing their request
            if hasattr(ctx, 'interaction') and ctx.interaction is not None:
                await ctx.defer()
            
            # Get user data for embedding
            user_data = await self.xp_manager.prepare_level_card_data(member, ctx.guild)
            
            # Get accent color for embed
            scheme = get_level_scheme(user_data.get('level', 0))
            embed_color = scheme_to_discord_color(scheme)
            
            # Create embed with user stats
            embed = discord.Embed(
                title=f"{member.display_name}'s Level Stats",
                color=embed_color
            )
            
            # Add user stats fields
            embed.add_field(
                name="Level", 
                value=f"**{user_data.get('level', 0)}**", 
                inline=True
            )
            
            embed.add_field(
                name="Rank", 
                value=f"**#{user_data.get('rank', 'N/A') if user_data.get('rank', 0) > 0 else 'N/A'}**", 
                inline=True
            )
            
            # XP progress
            current_xp = user_data.get('xp', 0)
            next_level_xp = user_data.get('next_level_xp', 1000)
            total_xp = user_data.get('total_xp', current_xp)
            
            embed.add_field(
                name="XP Progress", 
                value=f"**{current_xp:,}** / **{next_level_xp:,}**", 
                inline=True
            )
            
            embed.add_field(
                name="Total XP", 
                value=f"**{total_xp:,}**", 
                inline=True
            )
            
            embed.add_field(
                name="Messages", 
                value=f"**{user_data.get('messages', 0):,}**", 
                inline=True
            )
            
            embed.add_field(
                name="Voice Time", 
                value=f"**{user_data.get('total_voice_time', 0):.1f}** minutes", 
                inline=True
            )
            
            # Set thumbnail to member's avatar
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            
            # Set footer
            embed.set_footer(text=f"Levelling System", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            
            # Send the embed
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in levelinfo command for user {member.id if member else 'None'}: {e}", exc_info=True)
            await ctx.send("An error occurred while displaying user information.", ephemeral=True)

    @commands.hybrid_command(name="leaderboard", aliases=["lb", "top"], description="Show the server leaderboard")
    async def leaderboard(self, ctx, limit: int = 10):
        """
        Show the server leaderboard.
        
        Parameters
        ----------
        limit: int
            Number of users to show (max 25)
        """
        try:
            # Check if levelling is enabled
            settings = await self.get_guild_settings(ctx.guild.id)
            if not settings.get("enabled", True):
                await ctx.send("Levelling system is disabled in this server.", ephemeral=True)
                return
            
            # Limit the results
            limit = min(max(limit, 1), 25)
            
            if hasattr(ctx, 'interaction') and ctx.interaction is not None:
                await ctx.defer()
            
            # Get top users
            top_users = await self.xp_manager.get_top_users(ctx.guild.id, limit)
            
            if not top_users:
                await ctx.send("No users found in the leaderboard.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"🏆 {ctx.guild.name} Leaderboard",
                description=f"Top {len(top_users)} users by XP",
                color=discord.Color.gold()
            )
            
            leaderboard_text = ""
            for i, user_data in enumerate(top_users, 1):
                user_id = user_data.get("user_id")
                try:
                    user = ctx.guild.get_member(int(user_id))
                    if user:
                        name = user.display_name
                    else:
                        name = f"User {user_id}"
                except:
                    name = f"User {user_id}"
                
                level = user_data.get("level", 0)
                xp = user_data.get("xp", 0)
                
                # Add medal emojis for top 3
                if i == 1:
                    emoji = "🥇"
                elif i == 2:
                    emoji = "🥈"
                elif i == 3:
                    emoji = "🥉"
                else:
                    emoji = f"{i}."
                
                leaderboard_text += f"{emoji} **{name}** - Level {level} ({xp:,} XP)\n"
            
            embed.description = leaderboard_text
            
            if ctx.guild.icon:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}", exc_info=True)
            await ctx.send("An error occurred while showing the leaderboard.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Levelling(bot))
