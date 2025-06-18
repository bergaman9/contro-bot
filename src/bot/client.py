"""Custom Discord bot client with enhanced functionality."""

import discord
from discord.ext import commands
import logging
import aiohttp
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime

from ..database.connection import initialize_mongodb, get_async_db
from ..utils.common.logger import setup_logger
from ..utils.common.errors import BotError
from .constants import DEFAULT_PREFIX, BOT_VERSION


class ControBot(commands.Bot):
    """Enhanced Discord bot client with custom functionality."""
    
    def __init__(self, *args, **kwargs):
        # Set up intents
        intents = kwargs.pop("intents", discord.Intents.all())
        
        # Set up default prefix
        command_prefix = kwargs.pop("command_prefix", DEFAULT_PREFIX)
        
        # Initialize parent class
        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            *args,
            **kwargs
        )
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize attributes
        self.version = BOT_VERSION
        self.start_time = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.db = None
        self.persistent_views_loaded = False
        
        # Cog groups for organization
        self.cog_groups = {
            "admin": [],
            "moderation": [],
            "community": [],
            "fun": [],
            "utility": []
        }
        
    async def setup_hook(self):
        """Initialize bot components before starting."""
        self.logger.info("Setting up bot components...")
        
        # Create aiohttp session
        self.session = aiohttp.ClientSession()
        
        # Initialize database
        await self._setup_database()
        
        # Load cogs
        await self._load_cogs()
        
        # Load persistent views
        await self._load_persistent_views()
        
        # Sync commands if needed
        if hasattr(self, "should_sync_commands") and self.should_sync_commands:
            await self._sync_commands()
            
        self.logger.info("Bot setup completed!")
        
    async def on_ready(self):
        """Called when bot is ready."""
        self.start_time = datetime.utcnow()
        self.logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        self.logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{DEFAULT_PREFIX}help | {len(self.guilds)} servers"
            )
        )
        
    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a new guild."""
        self.logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Create default settings for the guild
        await self._create_default_guild_settings(guild.id)
        
        # Update presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{DEFAULT_PREFIX}help | {len(self.guilds)} servers"
            )
        )
        
    async def on_guild_remove(self, guild: discord.Guild):
        """Called when bot is removed from a guild."""
        self.logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")
        
        # Update presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{DEFAULT_PREFIX}help | {len(self.guilds)} servers"
            )
        )
        
    async def close(self):
        """Cleanup when bot is shutting down."""
        self.logger.info("Bot shutting down...")
        
        # Close aiohttp session
        if self.session:
            await self.session.close()
            
        # Close database connections
        # MongoDB motor client handles cleanup automatically
        
        # Call parent close
        await super().close()
        
    async def _setup_database(self):
        """Initialize database connection."""
        try:
            self.logger.info("Initializing database connection...")
            self.db = await get_async_db()
            self.logger.info("Database connection established!")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise BotError("Database connection failed")
            
    async def _load_cogs(self):
        """Load all cogs."""
        cog_mapping = {
            "admin": ["bot_management", "server_setup", "settings"],
            "moderation": ["actions", "automod", "logging"],
            "community": ["leveling", "registration", "welcome", "starboard"],
            "fun": ["games", "social", "random"],
            "utility": ["info", "tools", "reminders"]
        }
        
        loaded = 0
        failed = 0
        
        for category, cog_names in cog_mapping.items():
            for cog_name in cog_names:
                try:
                    await self.load_extension(f"src.cogs.{category}.{cog_name}")
                    self.cog_groups[category].append(cog_name)
                    loaded += 1
                    self.logger.info(f"Loaded cog: {category}.{cog_name}")
                except Exception as e:
                    failed += 1
                    self.logger.error(f"Failed to load cog {category}.{cog_name}: {e}")
                    
        self.logger.info(f"Cog loading complete: {loaded} loaded, {failed} failed")
        
    async def _load_persistent_views(self):
        """Load persistent views from database."""
        if self.persistent_views_loaded:
            return
            
        try:
            self.logger.info("Loading persistent views...")
            
            # Import view classes
            from ..utils.discord.views import (
                TicketCreateView,
                GiveawayView,
                RegisterButtonView,
                RoleSelectView
            )
            
            # Load ticket views
            ticket_messages = await self.db.ticket_messages.find({}).to_list(None)
            for msg_data in ticket_messages:
                view = TicketCreateView(self)
                self.add_view(view, message_id=int(msg_data["message_id"]))
                
            # Load giveaway views
            active_giveaways = await self.db.giveaways.find({"status": True}).to_list(None)
            for giveaway in active_giveaways:
                view = GiveawayView(self, giveaway["_id"])
                self.add_view(view, message_id=int(giveaway["message_id"]))
                
            self.persistent_views_loaded = True
            self.logger.info(f"Loaded {len(ticket_messages) + len(active_giveaways)} persistent views")
            
        except Exception as e:
            self.logger.error(f"Error loading persistent views: {e}")
            
    async def _sync_commands(self):
        """Sync application commands."""
        try:
            self.logger.info("Syncing application commands...")
            synced = await self.tree.sync()
            self.logger.info(f"Synced {len(synced)} application commands")
        except Exception as e:
            self.logger.error(f"Failed to sync commands: {e}")
            
    async def _create_default_guild_settings(self, guild_id: int):
        """Create default settings for a new guild."""
        default_settings = {
            "guild_id": str(guild_id),
            "prefix": DEFAULT_PREFIX,
            "language": "en",
            "features": {
                "leveling": True,
                "welcome": False,
                "logging": False,
                "automod": False
            },
            "created_at": datetime.utcnow()
        }
        
        await self.db.guild_settings.update_one(
            {"guild_id": str(guild_id)},
            {"$set": default_settings},
            upsert=True
        )
        
    def get_category_cogs(self, category: str) -> List[str]:
        """Get list of cogs in a category."""
        return self.cog_groups.get(category, []) 