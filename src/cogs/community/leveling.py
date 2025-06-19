import discord
from discord.ext import commands, tasks
import os
import logging
import datetime
import asyncio
from typing import Optional

from src.utils.core.formatting import create_embed
from src.utils.database.connection import initialize_mongodb, initialize_async_mongodb
from src.utils.community.turkoyto.xp_manager import XPManager, XP_VOICE_PER_MINUTE
from src.utils.community.turkoyto.card_renderer import create_level_card, get_level_scheme, scheme_to_discord_color

logger = logging.getLogger('levelling')

class Levelling(commands.Cog):
    """General levelling system that can be configured per guild"""
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = None
        self.voice_time_tracker = {}  # Track users in voice channels
        
        # Initialize the XP manager first
        try:
            self.xp_manager = XPManager()
            logger.info("XP Manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize XP Manager: {e}")
            self.xp_manager = None
        
        # Setup database after XP manager is initialized
        self.setup_database()
        
        # Start checking voice activity
        self.check_voice_activity.start()
        
        # Create necessary directories
        os.makedirs("data/Temp", exist_ok=True)
        
        logger.info("Levelling cog initialized")

    def setup_database(self):
        """Setup database connections"""
        try:
            # Get async database from bot if available
            if hasattr(self.bot, 'async_db') and self.bot.async_db is not None:
                self.mongo_db = self.bot.async_db
                logger.info("Using bot's async database connection")
                # Update XP manager immediately if we have the DB
                if hasattr(self, 'xp_manager') and self.xp_manager:
                    self.xp_manager.set_mongo_db(self.mongo_db)
            else:
                # Initialize XP manager without database initially
                logger.info("Database connection not available yet, will set up later")
                
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
                    from src.utils.database.db_manager import db_manager
                    self.mongo_db = db_manager.get_database()
                    if self.mongo_db is not None:
                        logger.info("Initialized MongoDB connection directly")
                    else:
                        logger.error("Failed to initialize MongoDB connection")
                except Exception as e:
                    logger.error(f"Error initializing MongoDB: {e}")
            
            # Update XP manager with database
            if self.mongo_db is not None and hasattr(self, 'xp_manager') and self.xp_manager:
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
                    from src.utils.database.db_manager import db_manager
                    self.mongo_db = db_manager.get_database()
                    if self.mongo_db is not None:
                        logger.info("Database connection established for Levelling")
                    else:
                        logger.error("Failed to get database connection")
                except Exception as e:
                    logger.error(f"Error ensuring database: {e}")
            
            # Update XP manager if we got a connection
            if self.mongo_db is not None and hasattr(self, 'xp_manager') and self.xp_manager:
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
                self.mongo_db = await initialize_async_mongodb()
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

    @commands.hybrid_group(name="leaderboard", aliases=["lb"], description="Show server leaderboards")
    async def leaderboard(self, ctx):
        """Show server leaderboards"""
        if ctx.invoked_subcommand is None:
            # Default to level leaderboard
            await self.level_leaderboard(ctx)

    @leaderboard.command(name="level", aliases=["xp"], description="Show XP leaderboard")
    async def level_leaderboard(self, ctx):
        """Show the XP/level leaderboard"""
        try:
            # Check if leveling is enabled
            settings = await self.get_guild_settings(ctx.guild.id)
            if not settings.get('enabled', True):
                embed = discord.Embed(
                    title="❌ Leveling Disabled",
                    description="The leveling system is disabled in this server.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)

            # Get top users by XP
            guild_id = str(ctx.guild.id)
            top_users = list(self.levels_collection.find(
                {"guild_id": guild_id}
            ).sort("xp", -1).limit(10))

            if not top_users:
                embed = discord.Embed(
                    title="📊 Level Leaderboard",
                    description="No users have earned XP yet!",
                    color=discord.Color.blue()
                )
                return await ctx.send(embed=embed)

            embed = discord.Embed(
                title=f"📊 {ctx.guild.name} - Level Leaderboard",
                description="Top 10 users by XP",
                color=discord.Color.gold()
            )

            leaderboard_text = ""
            for i, user_data in enumerate(top_users, 1):
                user = ctx.guild.get_member(int(user_data['user_id']))
                if user:
                    level = user_data.get('level', 1)
                    xp = user_data.get('xp', 0)
                    
                    # Medal emojis for top 3
                    medal = ""
                    if i == 1:
                        medal = "🥇"
                    elif i == 2:
                        medal = "🥈"
                    elif i == 3:
                        medal = "🥉"
                    
                    leaderboard_text += f"{medal} **{i}.** {user.mention} - Level {level} ({xp:,} XP)\n"

            embed.description = leaderboard_text
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            embed.timestamp = discord.utils.utcnow()

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in level leaderboard: {e}")
            await ctx.send("An error occurred while fetching the leaderboard.")

    @leaderboard.command(name="invites", description="Show invites leaderboard")
    async def invites_leaderboard(self, ctx):
        """Show the invites leaderboard"""
        try:
            # Get invite stats from MongoDB
            mongo_db = self.bot.get_cog("InviteTracker").mongo_db if self.bot.get_cog("InviteTracker") else None
            
            if not mongo_db:
                embed = discord.Embed(
                    title="❌ Invite Tracking Unavailable",
                    description="The invite tracking system is not available.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)

            # Get top inviters from invite_stats collection
            guild_id = ctx.guild.id
            cursor = mongo_db.invite_stats.find({"guild_id": guild_id}).sort("total_invites", -1).limit(10)
            
            top_inviters = []
            async for invite_data in cursor:
                top_inviters.append(invite_data)

            if not top_inviters:
                embed = discord.Embed(
                    title="🎯 Invites Leaderboard",
                    description="No invite data available yet!",
                    color=discord.Color.blue()
                )
                return await ctx.send(embed=embed)

            embed = discord.Embed(
                title=f"🎯 {ctx.guild.name} - Invites Leaderboard",
                description="Top 10 inviters",
                color=discord.Color.green()
            )

            leaderboard_text = ""
            for i, invite_data in enumerate(top_inviters, 1):
                user_id = invite_data.get('user_id')
                user = ctx.guild.get_member(user_id)
                if user:
                    # Calculate total invites
                    regular = invite_data.get('regular_invites', 0)
                    bonus = invite_data.get('bonus_invites', 0)
                    left = invite_data.get('left_invites', 0)
                    fake = invite_data.get('fake_invites', 0)
                    total = regular + bonus - left - fake
                    
                    # Medal emojis for top 3
                    medal = ""
                    if i == 1:
                        medal = "🥇"
                    elif i == 2:
                        medal = "🥈"
                    elif i == 3:
                        medal = "🥉"
                    
                    leaderboard_text += f"{medal} **{i}.** {user.mention} - {total} invites "
                    leaderboard_text += f"({regular} regular, {bonus} bonus, {left} left)\n"

            embed.description = leaderboard_text
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            embed.timestamp = discord.utils.utcnow()

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in invites leaderboard: {e}")
            await ctx.send("An error occurred while fetching the leaderboard.")

async def setup(bot):
    await bot.add_cog(Levelling(bot))
