"""
API routes for Contro Discord Bot
Registers all API endpoints and blueprints
"""

from flask import Flask, jsonify
from .commands_api import commands_bp
from .guilds import guilds_api as guilds_bp
from .levelling_api import levelling_bp
from .autorole_api import autorole_api as autorole_bp
from .welcome_api import welcome_api as welcome_bp
from .byebye_api import byebye_api as byebye_bp
from .game_stats_api import game_stats_bp
from .game_logs_api import game_logs_bp
from .tickets_api import tickets_bp
from .giveaways_api import giveaways_bp
from .giveaway_api import giveaway_bp
from .ai_chat_api import ai_chat_bp
from .custom_commands_api import custom_commands_bp
from .custom_status_api import custom_status_bp

def create_api_app(bot):
    """Create and configure the Flask app with all API routes"""
    # Create new Flask app
    app = Flask(__name__)
    
    # Store bot instance for API routes to access
    app.bot_instance = bot
    app.start_time = bot.startTime if hasattr(bot, 'startTime') else None
    
    # Import API controllers here to avoid circular imports
    from .commands_api import commands_bp
    from .guilds import guilds_api as guilds_bp
    from .levelling_api import levelling_bp
    from .autorole_api import autorole_api as autorole_bp
    from .welcome_api import welcome_api as welcome_bp
    from .byebye_api import byebye_api as byebye_bp
    from .game_stats_api import game_stats_bp
    from .game_logs_api import game_logs_bp
    from .tickets_api import tickets_bp
    from .giveaways_api import giveaways_bp
    from .giveaway_api import giveaway_bp
    from .ai_chat_api import ai_chat_bp
    from .custom_commands_api import custom_commands_bp
    from .custom_status_api import custom_status_bp
    
    # Initialize APIs with bot reference
    initialize_commands_api(bot)
    initialize_guilds_api(bot)
    initialize_levelling_api(bot)
    initialize_autorole_api(bot)
    initialize_welcome_api(bot)
    initialize_byebye_api(bot)
    initialize_game_stats_api(bot)
    initialize_game_logs_api(bot)
    initialize_tickets_api(bot)
    initialize_giveaways_api(bot)
    initialize_giveaway_api(bot)
    initialize_ai_chat_api(bot)
    initialize_custom_commands_api(bot)
    initialize_custom_status_api(bot)
    
    # Register blueprints
    app.register_blueprint(commands_bp, url_prefix='/api/commands')
    app.register_blueprint(guilds_bp, url_prefix='/api/guilds')
    app.register_blueprint(levelling_bp, url_prefix='/api/levelling')
    app.register_blueprint(autorole_bp, url_prefix='/api/autorole')
    app.register_blueprint(welcome_bp, url_prefix='/api/welcome')
    app.register_blueprint(byebye_bp, url_prefix='/api/byebye')
    app.register_blueprint(game_stats_bp, url_prefix='/api/game-stats')
    app.register_blueprint(game_logs_bp, url_prefix='/api/game-logs')
    app.register_blueprint(tickets_bp, url_prefix='/api/tickets')
    app.register_blueprint(giveaways_bp, url_prefix='/api/giveaways')
    app.register_blueprint(giveaway_bp, url_prefix='/api/giveaway')
    app.register_blueprint(ai_chat_bp, url_prefix='/api/ai-chat')
    app.register_blueprint(custom_commands_bp, url_prefix='/api/custom-commands')
    app.register_blueprint(custom_status_bp, url_prefix='/api/custom-status')
    
    # Root endpoint
    @app.route('/')
    def index():
        return {
            'message': 'Contro Discord Bot API',
            'version': '2.0.0',
            'status': 'running',
            'endpoints': {
                'commands': '/api/commands',
                'guilds': '/api/guilds',
                'levelling': '/api/levelling',
                'autorole': '/api/autorole',
                'welcome': '/api/welcome',
                'byebye': '/api/byebye',
                'game-stats': '/api/game-stats',
                'game-logs': '/api/game-logs',
                'tickets': '/api/tickets',
                'giveaways': '/api/giveaways',
                'giveaway': '/api/giveaway',
                'ai-chat': '/api/ai-chat',
                'custom-commands': '/api/custom-commands',
                'custom-status': '/api/custom-status'
            }
        }
    
    # Add ping endpoint directly in the main app
    @app.route('/api/ping', methods=['GET'])
    def ping():
        import psutil
        import time
        from datetime import timedelta
        
        if not app.bot_instance:
            return jsonify({"error": "Bot instance not initialized"}), 500

        # Count only main commands (simpler approach)
        text_cmd_count = len(app.bot_instance.commands)
        app_cmd_count = 0
        try:
            # Count top-level slash commands from command tree
            app_commands = app.bot_instance.tree.get_commands()
            app_cmd_count = len(app_commands)
        except Exception as e:
            print(f"Error counting commands: {e}")
        
        # Total number of commands (only main commands)
        active_commands = text_cmd_count + app_cmd_count

        latency = round(app.bot_instance.latency * 1000)  # latency in ms
        cpu_percent = psutil.cpu_percent(interval=1)
        ram_percent = psutil.virtual_memory().percent
        uptime = str(timedelta(seconds=int(round(time.time() - app.start_time)))) if app.start_time else "unknown"
        active_servers = len(app.bot_instance.guilds)
        active_users = sum(guild.member_count for guild in app.bot_instance.guilds)

        return jsonify({
            "latency_ms": latency,
            "cpu_usage_percent": cpu_percent,
            "ram_usage_percent": ram_percent,
            "uptime": uptime,
            "active_servers": active_servers,
            "active_users": active_users,
            "active_commands": active_commands,
            "command_details": {
                "text_commands": text_cmd_count,
                "slash_commands": app_cmd_count
            },
            "hosting_region": "Turkey",
            "hosting_provider": "Raspberry Pi 5"
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found", "status": 404}), 404
        
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error", "status": 500}), 500
    
    return app

# Initialize functions for each API
def initialize_commands_api(bot):
    """Initialize commands API with bot reference"""
    from .commands_api import initialize_commands_api as init_func
    init_func(bot)

def initialize_guilds_api(bot):
    """Initialize guilds API with bot reference"""
    from .guilds import initialize_guilds_api as init_func
    init_func(bot)

def initialize_levelling_api(bot):
    """Initialize levelling API with bot reference"""
    from .levelling_api import initialize_levelling_api as init_func
    init_func(bot)

def initialize_autorole_api(bot):
    """Initialize autorole API with bot reference"""
    from .autorole_api import initialize_autorole_api as init_func
    init_func(bot)

def initialize_welcome_api(bot):
    """Initialize welcome API with bot reference"""
    from .welcome_api import initialize_welcome_api as init_func
    init_func(bot)

def initialize_byebye_api(bot):
    """Initialize byebye API with bot reference"""
    from .byebye_api import initialize_byebye_api as init_func
    init_func(bot)

def initialize_game_stats_api(bot):
    """Initialize game stats API with bot reference"""
    from .game_stats_api import initialize_game_stats_api as init_func
    init_func(bot)

def initialize_game_logs_api(bot):
    """Initialize game logs API with bot reference"""
    from .game_logs_api import initialize_game_logs_api as init_func
    init_func(bot)

def initialize_tickets_api(bot):
    """Initialize tickets API with bot reference"""
    from .tickets_api import initialize_tickets_api as init_func
    init_func(bot)

def initialize_giveaways_api(bot):
    """Initialize giveaways API with bot reference"""
    from .giveaways_api import initialize_giveaways_api as init_func
    init_func(bot)

def initialize_giveaway_api(bot):
    """Initialize giveaway API with bot reference"""
    # Giveaway API doesn't need special initialization
    pass

def initialize_ai_chat_api(bot):
    """Initialize AI chat API with bot reference"""
    from .ai_chat_api import initialize_ai_chat_api as init_func
    init_func(bot)

def initialize_custom_commands_api(bot):
    """Initialize custom commands API with bot reference"""
    from .custom_commands_api import initialize_custom_commands_api as init_func
    init_func(bot)

def initialize_custom_status_api(bot):
    """Initialize custom status API with bot reference"""
    from .custom_status_api import initialize_custom_status_api as init_func
    init_func(bot)

# This function is used in main.py
def initialize_all_apis(bot):
    """Create and return the configured Flask app"""
    return create_api_app(bot)
