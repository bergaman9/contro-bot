from flask import Flask, jsonify

def create_api_app(bot):
    """Create and configure the Flask app with all API routes"""
    # Create new Flask app
    app = Flask(__name__)
    
    # Store bot instance for API routes to access
    app.bot_instance = bot
    app.start_time = bot.startTime if hasattr(bot, 'startTime') else None
    
    # Import API controllers here to avoid circular imports
    from .commands_api import commands_api, initialize_commands_api
    from .guilds_api import guilds_api, initialize_guilds_api
    
    # Initialize APIs with bot reference
    initialize_commands_api(bot)
    initialize_guilds_api(bot)
    
    # Register blueprints
    app.register_blueprint(commands_api)
    app.register_blueprint(guilds_api)
    
    # Basic routes
    @app.route('/')
    def index():
        return jsonify({
            "status": "online", 
            "message": "Contro Bot API is running",
            "endpoints": ["/api/ping", "/api/commands", "/api/guilds"]
        })
    
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

# This function is used in main.py
def initialize_all_apis(bot):
    """Create and return the configured Flask app"""
    return create_api_app(bot)
