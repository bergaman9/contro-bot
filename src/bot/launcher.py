"""Bot launcher and initialization."""
import os
import sys
import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands

from .client import ControBot
from .constants import *
from src.utils.core.manager import initialize_manager, cleanup_manager
from src.utils.common.logger import setup_logger

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


class BotLauncher:
    """Handles bot initialization and startup."""
    
    def __init__(self):
        """Initialize the launcher."""
        self.bot = None
        
    async def setup_manager(self):
        """Setup central manager with database and views."""
        # Initialize central manager with the bot
        success = await initialize_manager(self.bot, db_mode="auto")
        if not success:
            raise RuntimeError("Failed to initialize central manager")
        
        logger.info("Central manager setup complete")
        
    async def load_extensions(self):
        """Load bot extensions/cogs."""
        # Define cogs to load - scan directory for actual cogs
        base_cogs = [
            'src.cogs.community.registration',
            'src.cogs.utility.ping',
            # Add more cogs as they're discovered
        ]
        
        # Try to auto-discover additional cogs
        cogs_dir = Path(__file__).parent.parent / 'cogs'
        if cogs_dir.exists():
            for category_dir in cogs_dir.iterdir():
                if category_dir.is_dir() and not category_dir.name.startswith('__'):
                    for cog_file in category_dir.iterdir():
                        if cog_file.is_file() and cog_file.suffix == '.py' and not cog_file.name.startswith('__'):
                            cog_path = f'src.cogs.{category_dir.name}.{cog_file.stem}'
                            if cog_path not in base_cogs:
                                base_cogs.append(cog_path)
        
        loaded_count = 0
        failed_count = 0
        
        for cog in base_cogs:
            try:
                await self.bot.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
                loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
                failed_count += 1
                
        logger.info(f"Cog loading complete: {loaded_count} loaded, {failed_count} failed")
                
    async def start(self):
        """Start the bot."""
        # Setup logging
        setup_logger()
        
        logger.info("Starting ControBot...")
        
        # Load configuration
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            raise ValueError("DISCORD_TOKEN environment variable not set")
        
        # Create bot instance
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        self.bot = ControBot(intents=intents)
        
        # Setup central manager (database + persistent views)
        await self.setup_manager()
        
        # Load extensions
        await self.load_extensions()
        
        # Start the bot
        try:
            await self.bot.start(token)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Bot crashed: {e}", exc_info=True)
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up...")
        
        if self.bot:
            await self.bot.close()
            
        # Cleanup central manager
        await cleanup_manager()
            
        logger.info("Cleanup complete")


def main():
    """Main entry point."""
    launcher = BotLauncher()
    
    try:
        asyncio.run(launcher.start())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 