"""
Central Application Manager for Contro Discord Bot
Manages all services (bot, API, database, cache) from a single point
"""

import asyncio
import threading
import os
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from .config import get_config, reload_config
from .logger import setup_logging, get_logger, LoggerMixin
from .database import get_database_manager, close_database, get_sync_database_manager
from .cache import get_cache_manager, close_cache


class ApplicationManager(LoggerMixin):
    """Central manager for all application services."""
    
    def __init__(self):
        self.config = None
        self.bot = None
        self.api_app = None
        self.db_manager = None
        self.sync_db_manager = None
        self.cache_manager = None
        self._initialized = False
        self._shutdown_event = threading.Event()
        
    async def initialize(self, mode: str = "development") -> None:
        """Initialize all application services."""
        if self._initialized:
            return
            
        self.logger.info(f"Initializing Contro Application in {mode} mode")
        
        try:
            # Setup configuration
            await self._setup_config(mode)
            
            # Setup logging
            setup_logging()
            
            # Initialize database
            await self._setup_database()
            
            # Initialize cache
            await self._setup_cache()
            
            # Initialize bot
            await self._setup_bot()
            
            # Initialize API
            await self._setup_api()
            
            self._initialized = True
            self.logger.info("Application initialization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            await self.shutdown()
            raise
    
    async def _setup_config(self, mode: str) -> None:
        """Setup configuration."""
        import os
        # Map 'dev' to 'development' for config
        env_mode = 'development' if mode == 'dev' else mode
        os.environ['ENVIRONMENT'] = env_mode
        os.environ['DEBUG'] = 'true' if mode == 'dev' else 'false'
        # Reload configuration with mode
        self.config = reload_config(env_mode)
        self.config.environment = env_mode
        self.config.debug = mode == 'dev'
        self.config.logging.level = 'DEBUG' if mode == 'dev' else 'INFO'
    
    async def _setup_database(self) -> None:
        """Setup database connection."""
        self.logger.info("Setting up database connection...")
        self.db_manager = await get_database_manager()
        self.sync_db_manager = get_sync_database_manager()
        await self.db_manager.create_indexes()
        self.logger.info("Database setup completed")
    
    async def _setup_cache(self) -> None:
        """Setup cache connection."""
        self.logger.info("Setting up cache connection...")
        self.cache_manager = await get_cache_manager()
        self.logger.info("Cache setup completed")
    
    async def _setup_bot(self) -> None:
        """Setup Discord bot."""
        self.logger.info("Setting up Discord bot...")
        from src.bot.client import create_bot
        # Pass config object directly, not model_dump() to preserve methods
        self.bot = await create_bot(self.config)
        self.logger.info("Discord bot setup completed")
    
    async def _setup_api(self) -> None:
        """Setup Flask API."""
        self.logger.info("Setting up Flask API...")
        from src.api.app import create_app
        self.api_app = create_app()
        self.logger.info("Flask API setup completed")
    
    async def start_services(self, start_bot: bool = True, start_api: bool = True) -> None:
        """Start all services."""
        if not self._initialized:
            await self.initialize()
        
        self.logger.info("Starting application services...")
        
        # Start API in separate thread if enabled
        if start_api and self.config.api.enabled:
            self._start_api_thread()
        
        # Start bot if enabled
        if start_bot:
            await self._start_bot()
    
    def _start_api_thread(self) -> None:
        """Start API server in a separate thread."""
        # Railway PORT desteği
        api_port = int(os.environ.get('PORT', os.environ.get('API_PORT', self.config.api.port)))
        self.config.api.port = api_port

        def run_api():
            try:
                self.api_app.run(
                    host=self.config.api.host,
                    port=api_port,
                    debug=False,
                    threaded=True
                )
            except Exception as e:
                self.logger.error(f"API server error: {e}")
                self._shutdown_event.set()

        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        self.logger.info(f"API server started on {self.config.api.host}:{api_port}")
    
    async def _start_bot(self) -> None:
        """Start Discord bot."""
        try:
            self.logger.info("Starting Discord bot...")
            discord_token = self.config.get_discord_token()
            
            if not discord_token:
                raise ValueError("No Discord token found for current environment")
            await self.bot.start(discord_token)
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Bot error: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown all services gracefully."""
        self.logger.info("Shutting down application...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Close bot
        if self.bot:
            await self.bot.close()
        
        # Close database
        await close_database()
        
        # Close cache
        await close_cache()
        
        self._initialized = False
        self.logger.info("Application shutdown completed")
    
    def get_bot(self):
        """Get the Discord bot instance."""
        return self.bot
    
    def get_api_app(self):
        """Get the Flask API app instance."""
        return self.api_app
    
    def get_db_manager(self):
        """Get the database manager instance."""
        return self.db_manager
    
    def get_sync_db_manager(self):
        """Get the sync database manager instance."""
        return self.sync_db_manager
    
    def get_cache_manager(self):
        """Get the cache manager instance."""
        return self.cache_manager
    
    def get_config(self):
        """Get the configuration instance."""
        return self.config
    
    def is_initialized(self) -> bool:
        """Check if application is initialized."""
        return self._initialized
    
    def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        self._shutdown_event.wait()


# Global application manager instance
_app_manager: Optional[ApplicationManager] = None


async def get_application_manager() -> ApplicationManager:
    """Get the global application manager instance."""
    global _app_manager
    if _app_manager is None:
        _app_manager = ApplicationManager()
    return _app_manager


async def initialize_application(mode: str = "development") -> ApplicationManager:
    """Initialize the global application manager."""
    app_manager = await get_application_manager()
    await app_manager.initialize(mode)
    return app_manager


async def shutdown_application() -> None:
    """Shutdown the global application manager."""
    global _app_manager
    if _app_manager:
        await _app_manager.shutdown()
        _app_manager = None


@asynccontextmanager
async def application_context(mode: str = "development"):
    """Context manager for application lifecycle."""
    app_manager = await initialize_application(mode)
    try:
        yield app_manager
    finally:
        await shutdown_application() 