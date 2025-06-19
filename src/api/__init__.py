"""API module for the bot."""
from flask import Flask


def initialize_all_apis(bot):
    """Initialize all API routes with the bot instance."""
    # Create Flask app
    app = Flask(__name__)
    
    # Import and register blueprints
    from .routes.ping_api import ping_api, initialize_ping_api
    from .routes.commands_api import commands_api, initialize_commands_api
    from .routes.guilds_api import guilds_api, initialize_guilds_api
    
    # Initialize each API with bot instance
    initialize_ping_api(bot)
    initialize_commands_api(bot)
    initialize_guilds_api(bot)
    
    # Register blueprints
    app.register_blueprint(ping_api)
    app.register_blueprint(commands_api)
    app.register_blueprint(guilds_api)
    
    return app
