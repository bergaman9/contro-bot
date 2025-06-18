"""Bot launcher and initialization logic."""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional
import argparse

import discord
from dotenv import load_dotenv

from .client import ControBot
from ..utils.common.logger import setup_logger, setup_discord_logger
from ..utils.common.errors import ConfigurationError


class BotLauncher:
    """Handles bot initialization and startup."""
    
    def __init__(self):
        self.bot: Optional[ControBot] = None
        self.logger = None
        
    def setup_environment(self):
        """Load environment variables and validate configuration."""
        # Load .env file
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Try to find .env in parent directories
            current_path = Path.cwd()
            while current_path != current_path.parent:
                env_file = current_path / ".env"
                if env_file.exists():
                    load_dotenv(env_file)
                    break
                current_path = current_path.parent
                
        # Validate required environment variables
        required_vars = ["DISCORD_TOKEN", "MONGODB_URI"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
            
    def setup_logging(self, debug: bool = False):
        """Configure logging for the bot."""
        log_level = "DEBUG" if debug else os.getenv("LOG_LEVEL", "INFO")
        
        # Set up main logger
        self.logger = setup_logger(
            name="contro",
            level=log_level,
            log_dir=os.getenv("LOG_DIR", "logs")
        )
        
        # Set up Discord.py logger
        setup_discord_logger()
        
        self.logger.info("Logging configured successfully")
        
    def parse_arguments(self) -> argparse.Namespace:
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(
            description="Contro Discord Bot",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging"
        )
        
        parser.add_argument(
            "--sync-commands",
            action="store_true",
            help="Sync application commands on startup"
        )
        
        parser.add_argument(
            "--test",
            action="store_true",
            help="Run in test mode (limited functionality)"
        )
        
        parser.add_argument(
            "--prefix",
            type=str,
            help="Override default command prefix"
        )
        
        return parser.parse_args()
        
    async def create_bot(self, args: argparse.Namespace) -> ControBot:
        """Create and configure the bot instance."""
        # Set up intents
        intents = discord.Intents.all()
        
        # Get prefix
        prefix = args.prefix or os.getenv("BOT_PREFIX", ">")
        
        # Create bot instance
        bot = ControBot(
            command_prefix=prefix,
            intents=intents,
            help_command=None,  # We'll use a custom help command
            case_insensitive=True,
            strip_after_prefix=True
        )
        
        # Set additional attributes
        bot.should_sync_commands = args.sync_commands
        bot.test_mode = args.test
        
        return bot
        
    async def start(self):
        """Start the bot."""
        try:
            # Parse arguments
            args = self.parse_arguments()
            
            # Set up environment
            self.setup_environment()
            
            # Set up logging
            self.setup_logging(debug=args.debug)
            
            self.logger.info("Starting Contro Bot...")
            
            # Create bot
            self.bot = await self.create_bot(args)
            
            # Get token
            token = os.getenv("DISCORD_TOKEN")
            if not token:
                raise ConfigurationError("Discord token not found")
                
            # Start bot
            await self.bot.start(token)
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Fatal error: {e}", exc_info=True)
            else:
                print(f"Fatal error: {e}")
            sys.exit(1)
        finally:
            if self.bot:
                await self.bot.close()
                
    def run(self):
        """Run the bot (blocking)."""
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            pass


def main():
    """Entry point for the bot."""
    launcher = BotLauncher()
    launcher.run()


if __name__ == "__main__":
    main() 