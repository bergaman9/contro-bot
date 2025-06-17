import asyncio
import discord
from discord.ext import commands
import logging
import os
import sys
import traceback
import time
from datetime import datetime
import signal
import aiohttp
import argparse
import re
import requests
import threading
from typing import Optional
import json

from utils.core.formatting import create_embed
from utils.core.logger import logger, setup_logging, LOGS_DIR
from utils.core.config import ConfigManager
from api.ping_api import app, initialize_api
from api import initialize_all_apis
from utils.database import initialize_async_mongodb, get_async_db, close_async_mongodb, DummyAsyncDatabase
from utils.community.turkoyto.ticket_views import TicketButton, ServicesView

# Setup logging early
setup_logging()

# Early database connection will be initialized later in async context
logger.info("MongoDB will be initialized in async context")

# Global persistent view registry
PERSISTENT_VIEWS = []
PERSISTENT_VIEW_IDS = set()  # Track view IDs to prevent duplicates

# Add color utility functions at the beginning of the file after imports
class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    
    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

def print_colored(text, color=None, style=None, end="\n"):
    """Print text with ANSI color codes"""
    color_code = getattr(Colors, color.upper(), "") if color else ""
    style_code = getattr(Colors, style.upper(), "") if style else ""
    print(f"{style_code}{color_code}{text}{Colors.RESET}", end=end)

def print_banner(bot_type):
    """Print a stylish banner for the bot startup"""
    bot_color = {
        "MAIN": "green",
        "DEV": "yellow",
        "PREMIUM": "magenta"
    }.get(bot_type, "cyan")

    width = 59  # Total width of the banner
    
    print("\n")
    print_colored("╔═══════════════════════════════════════════════════════════╗", bot_color)
    print_colored("║                                                           ║", bot_color)
    
    # Center the main title
    title = "CONTRO DISCORD BOT"
    padding_title = (width - len(title) - 2) // 2  # -2 for the border chars
    print_colored(f"║{' ' * padding_title}{title}{' ' * (width - len(title) - padding_title)}║", bot_color, "bold")
    
    # Center the mode text
    mode_text = f"{bot_type} MODE"
    padding_mode = (width - len(mode_text) - 2) // 2
    print_colored(f"║{' ' * padding_mode}{mode_text}{' ' * (width - len(mode_text) - padding_mode)}║", bot_color, "bold")
    
    print_colored("║                                                           ║", bot_color)
    print_colored("╚═══════════════════════════════════════════════════════════╝", bot_color)
    print("\n")

# Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Contro Discord Bot")
    parser.add_argument("client_id", nargs="?", default="main", 
                        help="Client ID to use (main, dev, premium, or client name)")
    parser.add_argument("--list", action="store_true",
                        help="List available client configurations and exit")
    parser.add_argument("--no-api", action="store_true",
                        help="Don't start the API server")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode with additional logging")
    parser.add_argument("--skip-token-verification", action="store_true",
                        help="Skip Discord API token verification (use for debugging)")
    
    return parser.parse_args()

# List available client configurations
def list_clients(config_manager):
    print("\nAvailable client configurations:")
    print("=" * 50)
    
    # Get all available clients from config manager
    clients = config_manager.get_available_clients()
    
    if not clients:
        print("No client configurations found.")
    else:
        # Print header
        print(f"{'CLIENT ID':<15} {'NAME':<25} {'PREFIX':<10}")
        print("-" * 50)
        
        # Print each client's details
        for client_id in sorted(clients):
            name = config_manager.get_client_name(client_id)
            prefix = config_manager.get_prefix(client_id)
            print(f"{client_id:<15} {name:<25} {prefix:<10}")
    
    # Print usage information
    print("\nUsage: python main.py [client_id]")
    print("Special clients: main, dev, premium")
    print("Add --help for more options\n")
    sys.exit(0)

# Function to verify if a token is valid using Discord API
def verify_token(token, skip_api_check=False):
    """
    Perform validation of a Discord token
    
    Args:
        token: The Discord token to verify
        skip_api_check: If True, skips the API verification and only checks format
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check for common issues
    if not token:
        return False, "Token is empty or None"
    
    # Check for whitespace issues
    stripped_token = token.strip()
    if stripped_token != token:
        return False, "Token contains leading/trailing whitespace"
    
    # Basic format validation
    if len(token) < 50 or '.' not in token:
        return False, "Token is too short or doesn't contain required segments"
    
    # Check if token follows expected pattern (basic regex validation)
    token_pattern = re.compile(r'^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$')
    if not token_pattern.match(token):
        return False, "Token doesn't match expected format (should be three segments separated by periods)"
    
    # Skip API check if requested
    if skip_api_check:
        return True, "Token format validation passed (API check skipped as requested)"
    
    # Attempt API verification with retries
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            headers = {
                'Authorization': f'Bot {token}'
            }
            logger.debug(f"Verifying token with Discord API (attempt {attempt}/{max_retries})")
            response = requests.get('https://discord.com/api/v10/users/@me', headers=headers, timeout=5)
            
            if response.status_code == 200:
                return True, "Token verified with Discord API"
            elif response.status_code == 401:
                # No need to retry for auth failures
                token_preview = f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "[hidden]"
                return False, f"Token rejected by Discord API (unauthorized). Token preview: {token_preview}"
            elif response.status_code >= 500:
                # Server error, we should retry
                logger.warning(f"Discord API server error (status: {response.status_code}), retrying...")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return False, f"Discord API server error (status: {response.status_code}) after {max_retries} attempts"
            else:
                return False, f"Unexpected response from Discord API (status code: {response.status_code})"
                
        except requests.RequestException as e:
            logger.warning(f"API verification attempt {attempt} failed: {str(e)}")
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            # If all retries fail, we fall back to basic validation which already passed
            return True, f"Token format is valid but API verification failed after {max_retries} attempts: {str(e)}"
    
    # This should not be reached but just in case
    return True, "Token format validation passed but API verification inconclusive"

# Function to preload all common persistent views
def register_persistent_view(view):
    """Register a persistent view for early activation"""
    # Get a unique identifier for the view to prevent duplicates
    view_id = f"{view.__class__.__name__}:{id(view)}"
    
    if view_id in PERSISTENT_VIEW_IDS:
        logger.warning(f"Duplicate view registration attempted: {view.__class__.__name__}")
        return
        
    PERSISTENT_VIEWS.append(view)
    PERSISTENT_VIEW_IDS.add(view_id)
    logger.debug(f"Registered persistent view: {view.__class__.__name__} (ID: {view_id})")

# Set up global error handlers for the bot
def setup_error_handlers(bot):
    """Set up global error handlers for the bot"""
    @bot.event
    async def on_error(event, *args, **kwargs):
        """Global error handler for events"""
        logger.error(f"Error in event {event}", exc_info=True)
        
        # Log detailed error information if available
        if args:
            logger.error(f"Event args: {args}")
        if kwargs:
            logger.error(f"Event kwargs: {kwargs}")
    
    @bot.event
    async def on_command_error(ctx, error):
        """Global error handler for commands"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
            
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param}")
            
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Bad argument: {error}")
            
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(f"❌ You don't have permission to use this command.")
            
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"❌ I don't have the required permissions to execute this command.")
            
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏱️ This command is on cooldown. Try again in {error.retry_after:.1f} seconds.")
            
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(f"❌ You don't have permission to use this command.")
            
        else:
            # For unexpected errors, provide more detailed logging
            logger.error(f"Command error in {ctx.command}", exc_info=error)
            await ctx.send(f"❌ An error occurred: {str(error)}")
    
    logger.info("Global error handlers set up")

async def main():
    # Parse command line arguments
    global args
    args = parse_arguments()
    
    # Enable debug mode if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Create config manager
    config_manager = ConfigManager()
    
    # List clients and exit if requested
    if args.list:
        list_clients(config_manager)
    
    # Get client ID from arguments or default to main
    global client_id
    client_id = args.client_id.lower()
    
    # Check if client ID is valid
    if client_id not in config_manager.get_available_clients() and client_id not in ["main", "dev", "premium"]:
        print_colored(f"Error: Client ID '{client_id}' not found", "red")
        print("Available client IDs:")
        for cid in config_manager.get_available_clients():
            print(f"- {cid}")
        print("Or use one of: main, dev, premium")
        sys.exit(1)
    
    # Map client_id to config alias if needed
    client_id = {
        "main": config_manager.get_main_client(),
        "dev": config_manager.get_dev_client(),
        "premium": config_manager.get_premium_client()
    }.get(client_id, client_id)
    
    # Get client-specific settings
    token_env_var = f"CONTRO_{client_id.upper()}_TOKEN"
    token = os.getenv(token_env_var)
    token_source = token_env_var
    
    # If no token for this client, try generic token
    if not token:
        token = os.getenv("DISCORD_TOKEN")
        token_source = "DISCORD_TOKEN"
    
    # Fallback to generic token env var
    if not token:
        print_colored(f"❌ ERROR: No token found for client '{client_id}'", "red", "bold")
        print(f"Please set {token_env_var} or DISCORD_TOKEN in your environment or .env file")
        sys.exit(1)
    
    # Verify token
    if not args.skip_token_verification:
        is_valid, error_message = verify_token(token, False)
        if not is_valid:
            print_colored(f"❌ TOKEN VERIFICATION ERROR: {error_message}", "red", "bold")
            print(f"Please check your {token_source} environment variable")
            print("Use --skip-token-verification to bypass this check")
            sys.exit(1)
        else:
            print_colored("✅ Token verification passed", "green")
    
    # Print startup banner
    client_type = "MAIN" if client_id == config_manager.get_main_client() else "DEV" if client_id == config_manager.get_dev_client() else "PREMIUM" if client_id == config_manager.get_premium_client() else "CUSTOM"
    print_banner(client_type)
    
    # Get client-specific prefix
    prefix = config_manager.get_prefix(client_id)
    
    # Ensure help command is properly configured
    if client_id == "main":
        help_cmd = commands.DefaultHelpCommand()
    else:
        help_cmd = commands.DefaultHelpCommand()
    
    # Set up bot intents
    intents = discord.Intents.all()
    
    # Create bot instance with client-specific prefix
    bot = commands.Bot(
        command_prefix=prefix, 
        intents=intents,
        case_insensitive=True,
        help_command=help_cmd,
        strip_after_prefix=True, # This helps with prefixes like '>> '
    )
    
    # Get event loop
    loop = asyncio.get_event_loop()
    
    # Signal handlers
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}")
        loop.create_task(cleanup_and_exit())
        
    async def cleanup_and_exit():
        loop.stop()
    
    if sys.platform != 'win32':
        loop.add_signal_handler(signal.SIGINT, signal_handler, signal.SIGINT, None)
        loop.add_signal_handler(signal.SIGTERM, signal_handler, signal.SIGTERM, None)
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received, cleaning up...")
        # Signal API server to shutdown
        shutdown_event.set()
            
        # Close the bot connection and cleanup async database
        async def cleanup():
            try:
                await close_async_mongodb()
                logger.info("Async MongoDB connection closed")
                if hasattr(bot, 'is_closed') and not bot.is_closed():
                    await bot.close()
                    logger.info("Bot connection closed")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
        
        if not loop.is_closed():
            loop.create_task(cleanup())
            # Give cleanup tasks a chance to run before exiting
            loop.call_later(2, loop.stop)
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)
    
    # Store configuration manager and client ID on bot
    bot.config_manager = config_manager
    bot.client_id = client_id
    bot.startTime = time.time()  # Set bot start time for uptime calculations
    
    # Load bot version from version_config.json
    try:
        version_config_path = os.path.join(os.getcwd(), 'config', 'version_config.json')
        if os.path.exists(version_config_path):
            with open(version_config_path, 'r') as f:
                version_data = json.load(f)
                bot.version = version_data.get('version', '1.0.0')
                logger.info(f"Bot version loaded: {bot.version}")
                print_colored(f"✅ Bot version: {bot.version}", "green")
        else:
            bot.version = '1.0.0'
            logger.warning("Version config file not found, using default version")
    except Exception as e:
        bot.version = '1.0.0'
        logger.error(f"Error loading version: {e}")
    
    # Set up error handlers
    setup_error_handlers(bot)
    
    # Initialize MongoDB connection with better error handling
    try:
        # Add timeout to database initialization
        db = await asyncio.wait_for(initialize_async_mongodb(), timeout=15.0)
        if isinstance(db, DummyAsyncDatabase):
            logger.warning("Using fallback database mode - some features may not work correctly")
            print_colored("⚠️ MongoDB connection failed - using fallback mode", "yellow", "bold")
            print_colored("Some features may not work correctly", "yellow")
        else:
            logger.info("MongoDB connected successfully")
            print_colored("✅ MongoDB connected successfully", "green")
    except asyncio.TimeoutError:
        logger.error("MongoDB connection timed out after 15 seconds")
        print_colored("⚠️ MongoDB connection timed out - using fallback mode", "yellow", "bold")
        print_colored("Some features may not work correctly", "yellow")
        # Set fallback database
        db = DummyAsyncDatabase()
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB: {e}", exc_info=True)
        print_colored(f"⚠️ MongoDB connection error: {e}", "yellow", "bold")
        print_colored("Continuing with fallback database mode - some features may not work correctly", "yellow")
        # Set fallback database
        db = DummyAsyncDatabase()
    
    # Set the database on bot instance for cogs to access
    bot.async_db = db
    
    # Function to start the API server in a separate thread
    def start_api_server():
        def run_api():
            try:
                # Try importing required packages first
                try:
                    import flask
                    from werkzeug.serving import run_simple
                    import socket
                    import traceback  # Add for detailed error reporting
                except ImportError as e:
                    logger.error(f"API server required modules missing: {e}")
                    print_colored(f"⚠️ API server failed: Missing required modules - {e}", "red")
                    print_colored("Try installing dependencies: pip install flask werkzeug", "yellow")
                    return
                    
                # Initialize the API with the bot instance
                try:
                    logger.info("Creating API Flask app...")
                    flask_app = initialize_all_apis(bot)
                    
                    if not flask_app:
                        logger.error("API initialization failed - returned None")
                        print_colored("⚠️ API initialization failed - no app returned", "red")
                        return
                        
                    logger.info("API app created successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize API: {str(e)}")
                    print_colored(f"⚠️ API initialization error: {str(e)}", "red")
                    # Print full traceback for debugging
                    logger.error(traceback.format_exc())
                    return
                
                # Find available port
                port = 8000
                while port < 8100:  # Try ports up to 8099
                    try:
                        # Check if port is available
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(1)
                        result = sock.connect_ex(('127.0.0.1', port))
                        sock.close()
                        
                        if result != 0:  # Port is available
                            break
                        
                        port += 1
                    except:
                        port += 1
                
                if port >= 8100:
                    logger.error("Failed to find an available port")
                    print_colored("⚠️ API server failed: Couldn't find available port", "red")
                    return
                
                # Log that we're starting
                logger.info(f"Starting API server on port {port}...")
                print_colored(f"Starting API server on port {port}...", "cyan")
                
                # Start the Flask app with debugging disabled
                try:
                    flask_app.run(host='0.0.0.0', port=port, debug=False)
                    # Note: This will block, but since we're in a separate thread, it's OK
                except KeyboardInterrupt:
                    logger.info("API server stopped by keyboard interrupt")
                    print_colored("API server stopped by keyboard interrupt", "yellow")
                except Exception as e:
                    logger.error(f"API server error: {str(e)}")
                    print_colored(f"⚠️ API server error: {str(e)}", "red")
                    logger.error(traceback.format_exc())
                    
            except Exception as e:
                logger.error(f"Unhandled exception in API server: {str(e)}")
                print_colored(f"⚠️ API server fatal error: {str(e)}", "red")
                logger.error(traceback.format_exc())
        
        # Start in a daemon thread so it will be automatically terminated when main thread exits
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        return api_thread
    
    # Create a Flask server shutdown event for proper API server handling
    shutdown_event = threading.Event()
    
    # Start API server immediately if this is the main client (don't wait for on_ready)
    api_thread = None
    if not args.no_api and client_id == "main":
        try:
            logger.info("Starting API server immediately (main client only)")
            print_colored("Starting API server...", "cyan")
            api_thread = start_api_server()
            # Let's wait a brief moment to see if it starts correctly
            await asyncio.sleep(1)
            if api_thread and api_thread.is_alive():
                print_colored("✅ API server thread started", "green")
            else:
                print_colored("⚠️ API server thread failed to start", "red")
        except Exception as e:
            logger.error(f"Exception when starting API server: {e}")
            print_colored(f"⚠️ API server startup error: {e}", "red")
    elif not args.no_api and client_id != "main":
        print_colored("ℹ️ API server only runs in MAIN mode", "yellow")
    # No cleanup needed here
    
    # Preload persistent views on bot startup for immediate availability
    async def setup_persistent_views():
        # Bot hazır olana kadar bekle
        await bot.wait_until_ready()
        try:
            logger.info("Preloading persistent views...")
            PERSISTENT_VIEWS.clear()
            PERSISTENT_VIEW_IDS.clear()
            
            # Import ticket views
            try:
                from cogs.ticket import TicketButton, TicketCloseButtonView
                register_persistent_view(TicketButton())
                register_persistent_view(TicketCloseButtonView())
                logger.info("Ticket views preloaded")
            except Exception as e:
                logger.error(f"Error preloading ticket views: {e}")
            
            # Import giveaway views if available
            try:
                from cogs.giveaways import GiveawayView, GiveawayEditView
                register_persistent_view(GiveawayView(bot))
                register_persistent_view(GiveawayEditView(bot))
                logger.info("Giveaway views preloaded")
            except Exception as e:
                logger.error(f"Error preloading giveaway views: {e}")

            # Do NOT preload WelcomerConfigView/ByeByeConfigView globally, they require context
            
            # Import TurkOyto ticket views
            try:
                from utils.ticket_views import TicketButton, ServicesView
                register_persistent_view(TicketButton())
                register_persistent_view(ServicesView())
                logger.info("Ticket views preloaded")
            except ImportError:
                # Create dummy classes if module is missing
                logger.warning("Ticket views module not found, skipping")
                # We don't need to create dummy classes since we're just skipping registration
                pass
            except Exception as e:
                logger.error(f"Error preloading ticket views: {e}")
                
            # Import registration buttons if available
            try:
                # Try to import any registration buttons that need to be persistent
                from cogs.register import RegisterButton
                # Create a fresh instance of the button
                register_button = RegisterButton()
                register_persistent_view(register_button)
                logger.info("Registration views preloaded")
            except Exception as e:
                logger.error(f"Error preloading registration views: {e}")
                    
            # Register all preloaded views with the bot
            for view in PERSISTENT_VIEWS:
                # Only add views that are persistent (timeout=None and all items have custom_id)
                if getattr(view, "timeout", None) is None and all(
                    hasattr(item, "custom_id") and item.custom_id for item in getattr(view, "children", [])
                ):
                    bot.add_view(view)
                else:
                    logger.warning(f"Skipped non-persistent view: {view.__class__.__name__}")
                
            logger.info(f"Successfully preloaded {len(PERSISTENT_VIEWS)} persistent views")
        except Exception as e:
            logger.error(f"Error during view preloading: {e}")
    
    # Custom setup for the bot with optimized view loading
    @bot.event
    async def on_ready():
        logger.info(f"Bot is ready: {bot.user.name} ({bot.user.id})")
        
        # Start loading cogs in background
        asyncio.create_task(load_cogs())
        
        # Load persistent views early
        await setup_persistent_views()
        
        # Enhanced login information display with proper alignment
        width = 59  # Total width of the box
        
        print_colored("╔═══════════════════════════════════════════════════════════╗", "purple")
        
        # Login info line
        login_info = f"Logged in as: {bot.user.name} ({bot.user.id})"
        print_colored(f"║  {login_info.ljust(width - 2)}║", "purple")
        
        # Warning for name mismatch if needed
        expected_name = config_manager.get_client_name(client_id)
        if bot.user.name != expected_name:
            mismatch_text = f"WARNING: Bot name mismatch! Expected '{expected_name}'"
            print_colored(f"║  {mismatch_text.ljust(width - 2)}║", "purple")
        
        # Client mode line
        client_mode_text = f"CLIENT MODE: {client_id.upper()}"
        print_colored(f"║  {client_mode_text.ljust(width - 2)}║", "purple")
        
        # Prefix line
        prefix_text = f"Prefix: {prefix}"
        print_colored(f"║  {prefix_text.ljust(width - 2)}║", "purple")
        
        # Guild count line
        guild_text = f"Guild count: {len(bot.guilds)}"
        print_colored(f"║  {guild_text.ljust(width - 2)}║", "purple")
        
        print_colored("╚═══════════════════════════════════════════════════════════╝", "purple")
        
        # Set custom status for the bot in background to avoid blocking
        asyncio.create_task(set_bot_status())
    
    # Add global error handler for interactions
    @bot.event
    async def on_interaction(interaction):
        # This will be called for all interactions before they're passed to their handlers
        logger.debug(f"Interaction received: {interaction.type} from {interaction.user} (ID: {interaction.id})")
    
    @bot.event
    async def on_interaction_error(interaction, error):
        # This will be called when any interaction fails
        user_info = f"{interaction.user} (ID: {interaction.user.id})" if interaction.user else "Unknown user"
        
        # Get component info for debugging
        component_type = "Unknown"
        custom_id = "Unknown"
        
        try:
            if hasattr(interaction, 'data') and interaction.data:
                component_type = interaction.data.get('component_type', 'Unknown')
                custom_id = interaction.data.get('custom_id', 'Unknown')
        except Exception as e:
            logger.error(f"Error getting interaction data: {e}")
        
        # Log detailed error info
        logger.error(
            f"Interaction error: {error}\n"
            f"User: {user_info}\n"
            f"Guild: {interaction.guild.name if interaction.guild else 'DM'}\n"
            f"Type: {interaction.type}\n"
            f"Component: {component_type}\n"
            f"Custom ID: {custom_id}\n"
            f"Error: {error.__class__.__name__}: {str(error)}"
        )
        
        # Attempt to respond to the user if possible
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=create_embed(
                        description=f"❌ An error occurred: {str(error)}",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
        except Exception as respond_error:
            logger.error(f"Failed to respond to interaction error: {respond_error}")
    
    # Set bot status asynchronously to avoid blocking on_ready
    async def set_bot_status():
        # Set custom status for the bot
        if client_id == "dev":
            status_text = "maintenance mode"
            status = discord.Status.dnd
        elif client_id == "premium":
            status_text = f"{prefix}help | Premium features"
            status = discord.Status.online
        else:
            status_text = f"{prefix}help | /help"
            status = discord.Status.online
            
        await bot.change_presence(
            activity=discord.Game(name=status_text),
            status=status
        )
        logger.info(f"Bot status set to: {status_text}")

    # Add a manual resync command
    @bot.command(name="resync", help="Manually synchronize slash commands with Discord")
    @commands.is_owner()
    async def resync(ctx):
        try:
            logger.info("Manually syncing application commands...")
            synced = await bot.tree.sync()
            logger.info(f"Successfully synced {len(synced)} commands.")
            await ctx.send(f"✅ Successfully synced {len(synced)} commands.")
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")
            await ctx.send(f"❌ Failed to sync commands: {e}")

    # Add command to clear and reload persistent views
    @bot.command(name="reload_views", help="Clear and reload all persistent views")
    @commands.is_owner()
    async def reload_views(ctx):
        try:
            # Clear existing view tracking
            PERSISTENT_VIEWS.clear()
            PERSISTENT_VIEW_IDS.clear()
            
            # Note: We can't remove views from the bot directly,
            # but we can reload them which will supersede the old ones
            
            # Reload all views
            await setup_persistent_views()
            
            await ctx.send(
                embed=create_embed(
                    description=f"✅ Successfully reloaded {len(PERSISTENT_VIEWS)} persistent views.",
                    color=discord.Color.green()
                )
            )
        except Exception as e:
            logger.error(f"Error reloading views: {e}")
            await ctx.send(
                embed=create_embed(
                    description=f"❌ Failed to reload views: {str(e)}",
                    color=discord.Color.red()
                )
            )

    # --- COG MANAGEMENT COMMANDS ---

    @bot.command(name="load", help="Load a cog by name")
    @commands.is_owner()
    async def load_cog(ctx, cog: str):
        try:
            await bot.load_extension(f"cogs.{cog}")
            await ctx.send(f"✅ Loaded cog: `{cog}`")
        except Exception as e:
            await ctx.send(f"❌ Failed to load cog `{cog}`: {e}")

    @bot.command(name="unload", help="Unload a cog by name")
    @commands.is_owner()
    async def unload_cog(ctx, cog: str):
        try:
            await bot.unload_extension(f"cogs.{cog}")
            await ctx.send(f"✅ Unloaded cog: `{cog}`")
        except Exception as e:
            await ctx.send(f"❌ Failed to unload cog `{cog}`: {e}")

    @bot.command(name="reload", help="Reload a cog or special module (admin.py, admin_views, core/)")
    @commands.is_owner()
    async def reload_cog(ctx, cog: str = None):
        import importlib
        import sys
        import pathlib

        # Helper to reload a python module by path
        def reload_module_by_path(path):
            abs_path = os.path.abspath(path)
            module_name = None
            for name, module in sys.modules.items():
                if hasattr(module, "__file__") and module.__file__:
                    if os.path.abspath(module.__file__).startswith(abs_path):
                        module_name = name
                        break
            if module_name:
                importlib.reload(sys.modules[module_name])
                return True
            return False

        # Special reload for admin.py, admin_views, core/
        if cog in ("admin", "admin.py"):
            try:
                import importlib.util
                spec = importlib.util.find_spec("admin")
                if spec is None:
                    raise ImportError("admin.py not found")
                admin = importlib.import_module("admin")
                importlib.reload(admin)
                await ctx.send("✅ Reloaded `admin.py`")
            except Exception as e:
                await ctx.send(f"❌ Failed to reload `admin.py`: {e}")
            return
        elif cog == "admin_views":
            try:
                import importlib.util
                spec = importlib.util.find_spec("admin_views")
                if spec is None:
                    raise ImportError("admin_views.py not found")
                admin_views = importlib.import_module("admin_views")
                importlib.reload(admin_views)
                await ctx.send("✅ Reloaded `admin_views`")
            except Exception as e:
                await ctx.send(f"❌ Failed to reload `admin_views`: {e}")
            return
        elif cog == "core":
            core_dir = os.path.join(os.path.dirname(__file__), "core")
            reloaded = []
            failed = []
            for pyfile in pathlib.Path(core_dir).rglob("*.py"):
                rel_path = pyfile.relative_to(os.path.dirname(__file__)).as_posix().replace("/", ".")[:-3]
                try:
                    mod = importlib.import_module(rel_path)
                    importlib.reload(mod)
                    reloaded.append(rel_path)
                except Exception as e:
                    failed.append(f"{rel_path}: {e}")
            msg = f"✅ Reloaded core modules: {', '.join(reloaded)}"
            if failed:
                msg += f"\n❌ Failed: {', '.join(failed)}"
            await ctx.send(msg)
            return
        elif cog is None:
            await ctx.send("Please specify a cog/module to reload (e.g. `reload utility` or `reload core`)")
            return
        else:
            try:
                await bot.reload_extension(f"cogs.{cog}")
                await ctx.send(f"✅ Reloaded cog: `{cog}`")
            except Exception as e:
                await ctx.send(f"❌ Failed to reload cog `{cog}`: {e}")

    @bot.command(name="restart", help="Reload all cogs and core/admin modules without shutting down the bot")
    @commands.is_owner()
    async def restart(ctx):
        import importlib
        import sys
        import pathlib
        import time
        
        start_time = time.time()
        status_msg = await ctx.send("⏳ Restarting bot services... Please wait.")

        # Reload utils modules first
        utils_dir = os.path.join(os.path.dirname(__file__), "utils")
        utils_modules = []
        for pyfile in pathlib.Path(utils_dir).rglob("*.py"):
            if "__pycache__" in str(pyfile):
                continue
            rel_path = pyfile.relative_to(os.path.dirname(__file__)).as_posix().replace("/", ".")[:-3]
            try:
                mod = importlib.import_module(rel_path)
                importlib.reload(mod)
                utils_modules.append(rel_path)
            except Exception as e:
                logger.error(f"Failed to reload util module {rel_path}: {e}")
        
        # Unload all cogs first
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        cog_files = [f.stem for f in pathlib.Path(cogs_dir).glob("*.py") if f.stem != "__init__"]
        reloaded = []
        failed = []
        
        # First unload all cogs
        for cog in cog_files:
            try:
                if f"cogs.{cog}" in bot.extensions:
                    await bot.unload_extension(f"cogs.{cog}")
            except Exception as e:
                logger.error(f"Error unloading {cog}: {e}")

        # Then reload all cogs
        for cog in cog_files:
            try:
                await bot.load_extension(f"cogs.{cog}")
                reloaded.append(cog)
            except Exception as e:
                failed.append(f"{cog}: {e}")
                logger.error(f"Failed to reload cog {cog}: {e}")
        
        # Sync application commands
        try:
            await bot.tree.sync()
            logger.info("Command tree successfully synced")
        except Exception as e:
            logger.error(f"Error syncing command tree: {e}")
            failed.append(f"command_sync: {e}")

        # Reload admin.py
        try:
            import importlib.util
            spec = importlib.util.find_spec("admin")
            if spec is None:
                raise ImportError("admin.py not found")
            admin = importlib.import_module("admin")
            importlib.reload(admin)
            reloaded.append("admin.py")
        except Exception as e:
            failed.append(f"admin.py: {e}")

        # Reload admin_views
        try:
            import importlib.util
            spec = importlib.util.find_spec("admin_views")
            if spec is None:
                raise ImportError("admin_views.py not found")
            admin_views = importlib.import_module("admin_views")
            importlib.reload(admin_views)
            reloaded.append("admin_views")
        except Exception as e:
            failed.append(f"admin_views: {e}")

        # Reload core directory
        core_dir = os.path.join(os.path.dirname(__file__), "core")
        for pyfile in pathlib.Path(core_dir).rglob("*.py"):
            rel_path = pyfile.relative_to(os.path.dirname(__file__)).as_posix().replace("/", ".")[:-3]
            try:
                mod = importlib.import_module(rel_path)
                importlib.reload(mod)
                reloaded.append(rel_path)
            except Exception as e:
                failed.append(f"{rel_path}: {e}")

        msg = f"♻️ Restarted (reloaded): {', '.join(reloaded)}"
        if failed:
            msg += f"\n❌ Failed: {', '.join(failed)}"
        await ctx.send(msg)

    # Helper function to load cogs with improved parallel loading
    async def load_cogs():
        # Get enabled cogs for this client
        enabled_cogs = config_manager.get_enabled_cogs(client_id)
        
        logger.info(f"Loading {len(enabled_cogs)} cogs for {client_id} client")
        print_colored(f"Loading {len(enabled_cogs)} cogs: {', '.join(enabled_cogs)}", "cyan")
        
        # Check if we found any cogs to load
        if not enabled_cogs:
            logger.warning(f"No enabled cogs found for client '{client_id}'")
            print_colored(f"⚠️ No enabled cogs found for client '{client_id}'", "yellow")
            print_colored("Check config.json to ensure 'enabled_cogs' is correctly set", "yellow")
        
        # Use asyncio.gather to load cogs in parallel for faster startup
        async def load_cog(cog_name):
            try:
                # Check if cog is already loaded and remove it first
                if f"cogs.{cog_name}" in bot.extensions:
                    logger.warning(f"Cog {cog_name} already loaded, unloading first")
                    await bot.unload_extension(f"cogs.{cog_name}")
                
                await bot.load_extension(f"cogs.{cog_name}")
                logger.info(f"Loaded cog: {cog_name}")
                return True, cog_name
            except Exception as e:
                logger.error(f"Failed to load cog {cog_name}: {e}", exc_info=True)
                return False, cog_name

        # Load cogs in parallel
        results = await asyncio.gather(*[load_cog(cog) for cog in enabled_cogs], return_exceptions=False)
        
        # Count success/failures
        success_count = sum(1 for r in results if isinstance(r, tuple) and r[0])
        failed_count = len(enabled_cogs) - success_count
        
        logger.info(f"Cog loading complete: {success_count} loaded, {failed_count} failed")
        
        # Sync commands after cogs are loaded
        try:
            logger.info("Syncing application commands...")
            await bot.tree.sync()
            logger.info("Application commands synced successfully")
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")
    
    # Start the bot with the client-specific token
    try:
        print_colored(f"\nStarting {client_id.upper()} bot using {token_source}...", "cyan", "bold")
        logger.info(f"Starting {client_id} client with token from {token_source}...")
        # Start API server in background before connecting to Discord
        if not args.no_api and client_id == "main":
            try:
                logger.info("Starting API server immediately (main client only)")
                print_colored("Starting API server...", "cyan")
                api_thread = start_api_server()
            except Exception as e:
                logger.error(f"Exception when starting API server: {e}")
                print_colored(f"⚠️ API server startup error: {e}", "red")
                
        # Connect to Discord
        await bot.start(token)
    except discord.LoginFailure as e:
        logger.exception(f"Discord login failed: {e}")
        print_colored("\n⚠️  TOKEN ERROR: The Discord token is invalid or has been revoked.", "red", "bold")
        print(f"Error details: {str(e)}")
        print("\n📋 SOLUTION:")
        print("1. Go to Discord Developer Portal: https://discord.com/developers/applications")
        print("2. Select your bot application")
        print("3. Go to the 'Bot' tab")
        print("4. Click 'Reset Token' and copy the new token")
        print("5. Update your .env file with the fresh token")
        print(f"\nFor client '{client_id}', update: CONTRO_{client_id.upper()}_TOKEN=your_new_token")
    except Exception as e:
        logger.exception(f"Error starting bot: {e}")
        print_colored(f"\n⚠️ ERROR: Failed to start the bot: {str(e)}", "red", "bold")
    finally:
        logger.info("Bot shutdown complete")
        # Ensure any remaining tasks are properly closed
        if 'bot' in locals() and hasattr(bot, 'loop') and bot.loop.is_running():
            tasks = asyncio.all_tasks(bot.loop)
            for task in tasks:
                task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down due to keyboard interrupt...")
    except Exception as e:
        logger.critical(f"Fatal error in main loop: {str(e)}", exc_info=True)
        print(f"\n⚠️ FATAL ERROR: {str(e)}")
        import sys
        sys.exit(1)