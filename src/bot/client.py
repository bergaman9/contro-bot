"""Enhanced Discord bot client."""
import discord
from discord.ext import commands
from typing import Optional, Dict, Any, List
import logging
import aiohttp
from datetime import datetime

from .constants import *
from ..database.connection import DatabaseConnection
from ..services import GuildService, UserService, MemberService

logger = logging.getLogger(__name__)


class ControBot(commands.Bot):
    """Enhanced Discord bot with additional functionality."""
    
    def __init__(self, *args, db: Optional[DatabaseConnection] = None, **kwargs):
        """Initialize the bot.
        
        Args:
            db: Database connection instance
            *args: Positional arguments for commands.Bot
            **kwargs: Keyword arguments for commands.Bot
        """
        # Set default command prefix if not provided
        if 'command_prefix' not in kwargs:
            kwargs['command_prefix'] = self.get_prefix
            
        super().__init__(*args, **kwargs)
        
        # Core attributes
        self.db = db
        self.session: Optional[aiohttp.ClientSession] = None
        self.start_time = datetime.utcnow()
        
        # Services
        self.guild_service: Optional[GuildService] = None
        self.user_service: Optional[UserService] = None
        self.member_service: Optional[MemberService] = None
        
        # Cache
        self._prefix_cache: Dict[int, str] = {}
        
    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("Running setup hook...")
        
        # Create aiohttp session
        self.session = aiohttp.ClientSession()
        
        # Initialize services if database is available
        if self.db:
            self.guild_service = GuildService(self.db)
            self.user_service = UserService(self.db)
            self.member_service = MemberService(self.db)
            
            logger.info("Services initialized")
        
        # Sync commands if needed
        if getattr(self, 'should_sync_commands', False):
            logger.info("Syncing application commands...")
            await self.sync_commands()
            
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"Bot ready! Logged in as {self.user} ({self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | /help"
        )
        await self.change_presence(activity=activity)
        
    async def on_connect(self):
        """Called when the bot connects to Discord."""
        logger.info("Connected to Discord")
        
    async def on_disconnect(self):
        """Called when the bot disconnects from Discord."""
        logger.warning("Disconnected from Discord")
        
    async def on_resumed(self):
        """Called when the bot resumes a session."""
        logger.info("Resumed Discord session")
        
    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a guild."""
        logger.info(f"Joined guild: {guild.name} ({guild.id})")
        
        # Ensure guild exists in database
        if self.guild_service:
            try:
                await self.guild_service.ensure_guild_exists(guild)
                await self.guild_service.update_guild_info(guild)
            except Exception as e:
                logger.error(f"Error setting up guild {guild.id}: {e}")
                
        # Update status
        await self.update_status()
        
    async def on_guild_remove(self, guild: discord.Guild):
        """Called when the bot leaves a guild."""
        logger.info(f"Left guild: {guild.name} ({guild.id})")
        
        # Update status
        await self.update_status()
        
    async def get_prefix(self, message: discord.Message) -> List[str]:
        """Get the prefix for a guild."""
        # DMs always use default prefix
        if not message.guild:
            return [DEFAULT_PREFIX]
            
        # Check cache first
        if message.guild.id in self._prefix_cache:
            prefix = self._prefix_cache[message.guild.id]
        else:
            # Get from database
            if self.guild_service:
                try:
                    prefix = await self.guild_service.get_prefix(message.guild.id)
                    self._prefix_cache[message.guild.id] = prefix
                except Exception as e:
                    logger.error(f"Error getting prefix for guild {message.guild.id}: {e}")
                    prefix = DEFAULT_PREFIX
            else:
                prefix = DEFAULT_PREFIX
                
        # Return list with prefix and mention
        return commands.when_mentioned_or(prefix)(self, message)
        
    async def update_status(self):
        """Update bot status."""
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | /help"
        )
        await self.change_presence(activity=activity)
        
    async def close(self):
        """Clean up bot resources."""
        logger.info("Shutting down bot...")
        
        # Close aiohttp session
        if self.session:
            await self.session.close()
            
        # Clean up services
        if self.guild_service:
            await self.guild_service.cleanup()
        if self.user_service:
            await self.user_service.cleanup()
        if self.member_service:
            await self.member_service.cleanup()
            
        # Call parent close
        await super().close()
        
    def get_uptime(self) -> str:
        """Get bot uptime as a formatted string."""
        delta = datetime.utcnow() - self.start_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds or not parts:
            parts.append(f"{seconds}s")
            
        return " ".join(parts)
        
    async def is_owner(self, user: discord.User) -> bool:
        """Check if a user is a bot owner."""
        # Use built-in owner check
        if await super().is_owner(user):
            return True
            
        # Check additional owner IDs from constants
        return user.id in OWNER_IDS
        
    async def sync_commands(self, guild_id: Optional[int] = None):
        """Sync application commands.
        
        Args:
            guild_id: Guild ID to sync to (None for global)
        """
        if guild_id:
            guild = self.get_guild(guild_id)
            if guild:
                await self.tree.sync(guild=guild)
                logger.info(f"Synced commands to guild {guild_id}")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally") 