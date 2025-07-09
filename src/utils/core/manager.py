"""
Central Manager for Discord Bot
Handles database connections, persistent views, and other core functionality
"""
import asyncio
import logging
import os
from typing import Optional, Dict, List, Any, Union, TYPE_CHECKING
import discord
from discord.ext import commands

# Type checking imports
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase as AsyncDatabase
    from pymongo.database import Database as SyncDatabase

logger = logging.getLogger('core.manager')

class BotManager:
    """Central manager for bot functionality"""
    
    def __init__(self, bot: commands.Bot = None):
        self.bot = bot
        self._async_db: Optional["AsyncDatabase"] = None
        self._sync_db: Optional["SyncDatabase"] = None
        self._persistent_views: Dict[str, discord.ui.View] = {}
        self._view_classes: Dict[str, type] = {}
        self._is_initialized = False
        self._db_connection_mode = "auto"  # "auto", "async", "sync"
        
    async def initialize(self, bot: commands.Bot = None, db_mode: str = "auto") -> bool:
        """Initialize the manager with database and views"""
        if bot:
            self.bot = bot
            
        self._db_connection_mode = db_mode
        
        try:
            # Initialize database connection
            await self._initialize_database()
            
            # Register view classes
            self._register_view_classes()
            
            # Load persistent views
            await self._load_persistent_views()
            
            self._is_initialized = True
            logger.info("Bot manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize bot manager: {e}", exc_info=True)
            return False
    
    async def _initialize_database(self):
        """Initialize database connection based on mode"""
        if self._db_connection_mode in ["auto", "async"]:
            try:
                from ..database.connection import initialize_async_mongodb
                self._async_db = await initialize_async_mongodb()
                logger.info("Async MongoDB connection established")
                return
            except Exception as e:
                logger.warning(f"Async MongoDB failed: {e}")
                if self._db_connection_mode == "async":
                    raise
        
        if self._db_connection_mode in ["auto", "sync"]:
            try:
                from ..database.connection import initialize_mongodb
                self._sync_db = initialize_mongodb()
                logger.info("Sync MongoDB connection established")
            except Exception as e:
                logger.error(f"Sync MongoDB failed: {e}")
                if self._db_connection_mode == "sync":
                    raise
    
    def _register_view_classes(self):
        """Register persistent view classes"""
        try:
            # Register view classes that need to be persistent
            from ...cogs.community.registration import RegisterButton
            self._view_classes['RegisterButton'] = RegisterButton
            
            # Add other persistent view classes here as needed
            # self._view_classes['TicketButton'] = TicketButton
            # self._view_classes['GiveawayView'] = GiveawayView
            
            logger.info(f"Registered {len(self._view_classes)} view classes")
            
        except Exception as e:
            logger.error(f"Failed to register view classes: {e}", exc_info=True)
    
    async def _load_persistent_views(self):
        """Load and add persistent views to the bot"""
        if not self.bot:
            logger.warning("Bot not available, skipping persistent view loading")
            return
            
        try:
            # Load RegisterButton
            if 'RegisterButton' in self._view_classes:
                register_view = self._view_classes['RegisterButton']()
                self.bot.add_view(register_view)
                self._persistent_views['register'] = register_view
                logger.info("Loaded RegisterButton persistent view")
            
            # Add other persistent views here
            
            logger.info(f"Loaded {len(self._persistent_views)} persistent views")
            
        except Exception as e:
            logger.error(f"Failed to load persistent views: {e}", exc_info=True)
    
    def get_database(self, prefer_async: bool = None) -> Union["AsyncDatabase", "SyncDatabase", None]:
        """Get database connection, preferring async if available"""
        if prefer_async is None:
            prefer_async = self._db_connection_mode != "sync"
            
        if prefer_async and self._async_db:
            return self._async_db
        elif self._sync_db:
            return self._sync_db
        elif self._async_db:
            return self._async_db
        else:
            logger.warning("No database connection available")
            return None
    
    async def get_async_database(self) -> Optional["AsyncDatabase"]:
        """Get async database connection, initialize if needed"""
        if self._async_db is None:
            try:
                from ..database.connection import initialize_async_mongodb
                self._async_db = await initialize_async_mongodb()
            except Exception as e:
                logger.error(f"Failed to get async database: {e}")
                return None
        return self._async_db
    
    def get_sync_database(self) -> Optional["SyncDatabase"]:
        """Get sync database connection, initialize if needed"""
        if self._sync_db is None:
            try:
                from ..database.connection import initialize_mongodb
                self._sync_db = initialize_mongodb()
            except Exception as e:
                logger.error(f"Failed to get sync database: {e}")
                return None
        return self._sync_db
    
    def add_persistent_view(self, name: str, view: discord.ui.View) -> bool:
        """Add a persistent view to the bot"""
        if not self.bot:
            logger.warning("Bot not available, cannot add persistent view")
            return False
            
        try:
            self.bot.add_view(view)
            self._persistent_views[name] = view
            logger.info(f"Added persistent view: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add persistent view {name}: {e}")
            return False
    
    def remove_persistent_view(self, name: str) -> bool:
        """Remove a persistent view from the bot"""
        if name not in self._persistent_views:
            logger.warning(f"Persistent view {name} not found")
            return False
            
        try:
            view = self._persistent_views[name]
            if self.bot:
                self.bot.remove_view(view)
            del self._persistent_views[name]
            logger.info(f"Removed persistent view: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove persistent view {name}: {e}")
            return False
    
    def get_persistent_view(self, name: str) -> Optional[discord.ui.View]:
        """Get a persistent view by name"""
        return self._persistent_views.get(name)
    
    def list_persistent_views(self) -> List[str]:
        """List all registered persistent views"""
        return list(self._persistent_views.keys())
    
    async def reload_persistent_views(self) -> bool:
        """Reload all persistent views"""
        try:
            # Remove existing views
            for name in list(self._persistent_views.keys()):
                self.remove_persistent_view(name)
            
            # Reload views
            await self._load_persistent_views()
            logger.info("Persistent views reloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload persistent views: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Close database connections
            if self._async_db:
                try:
                    from ..database.connection import close_async_mongodb
                    await close_async_mongodb()
                except Exception as e:
                    logger.error(f"Failed to close async database: {e}")
            
            # Clear persistent views
            self._persistent_views.clear()
            self._view_classes.clear()
            
            logger.info("Bot manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized"""
        return self._is_initialized
    
    @property
    def has_async_db(self) -> bool:
        """Check if async database is available"""
        return self._async_db is not None
    
    @property
    def has_sync_db(self) -> bool:
        """Check if sync database is available"""
        return self._sync_db is not None

# Global manager instance
_bot_manager: Optional[BotManager] = None

def get_manager() -> BotManager:
    """Get the global bot manager instance"""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = BotManager()
    return _bot_manager

async def initialize_manager(bot: commands.Bot, db_mode: str = "auto") -> bool:
    """Initialize the global bot manager"""
    manager = get_manager()
    return await manager.initialize(bot, db_mode)

def get_database(prefer_async: bool = None) -> Union["AsyncDatabase", "SyncDatabase", None]:
    """Get database connection from manager"""
    manager = get_manager()
    return manager.get_database(prefer_async)

async def get_async_database() -> Optional["AsyncDatabase"]:
    """Get async database connection from manager"""
    manager = get_manager()
    return await manager.get_async_database()

def get_sync_database() -> Optional["SyncDatabase"]:
    """Get sync database connection from manager"""
    manager = get_manager()
    return manager.get_sync_database()

def add_persistent_view(name: str, view: discord.ui.View) -> bool:
    """Add persistent view via manager"""
    manager = get_manager()
    return manager.add_persistent_view(name, view)

def remove_persistent_view(name: str) -> bool:
    """Remove persistent view via manager"""
    manager = get_manager()
    return manager.remove_persistent_view(name)

async def cleanup_manager():
    """Cleanup the global manager"""
    global _bot_manager
    if _bot_manager:
        await _bot_manager.cleanup()
        _bot_manager = None 