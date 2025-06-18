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
from ..database.connection import DatabaseConnection
from ..utils.common.logger import setup_logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


class BotLauncher:
    """Handles bot initialization and startup."""
    
    def __init__(self):
        """Initialize the launcher."""
        self.bot = None
        self.db = None
        
    async def setup_database(self):
        """Setup database connection."""
        # Get MongoDB connection string from environment
        mongo_uri = os.getenv('MONGODB_URI')
        if not mongo_uri:
            raise ValueError("MONGODB_URI environment variable not set")
        
        # Create database connection
        self.db = DatabaseConnection(
            connection_string=mongo_uri,
            database_name=os.getenv('MONGODB_DATABASE', 'contro_bot')
        )
        
        # Connect to database
        await self.db.connect()
        
        # Create indexes
        await self.db.create_indexes()
        
        logger.info("Database setup complete")
        
    async def load_extensions(self):
        """Load bot extensions/cogs."""
        # Define cogs to load
        cogs = [
            'src.cogs.utility.ping',
            # Add more cogs as they're created
        ]
        
        for cog in cogs:
            try:
                self.bot.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
                
    async def start(self):
        """Start the bot."""
        # Setup logging
        setup_logging()
        
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
        
        self.bot = ControBot(
            intents=intents,
            db=self.db
        )
        
        # Setup database
        await self.setup_database()
        
        # Pass database to bot
        self.bot.db = self.db
        
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
            
        if self.db:
            await self.db.disconnect()
            
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