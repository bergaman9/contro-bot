from flask import Blueprint, jsonify
import psutil
import time
import logging
from datetime import timedelta

ping_api = Blueprint('ping_api', __name__)

# Global variable to hold the bot instance
bot_instance = None
# Track the start time of the API/bot
start_time = None

# Setup logging
logger = logging.getLogger('ping_api')

def initialize_ping_api(bot):
    global bot_instance, start_time
    bot_instance = bot
    # Set the start time when the API is initialized
    start_time = time.time()
    logger.info("Ping API initialized")

@ping_api.route('/api/ping', methods=['GET'])
def ping():
    try:
        if not bot_instance:
            return jsonify({"error": "Bot instance not initialized"}), 500

        # Get basic metrics with error handling
        try:
            latency = round(bot_instance.latency * 1000)  # latency in ms
        except Exception as e:
            logger.warning(f"Couldn't get latency: {e}")
            latency = -1  # Indicate unknown latency
            
        try:
            # Use interval=None to get immediate value without blocking
            cpu_percent = psutil.cpu_percent(interval=None)
        except Exception as e:
            logger.warning(f"Couldn't get CPU usage: {e}")
            cpu_percent = -1
            
        try:
            ram_percent = psutil.virtual_memory().percent
        except Exception as e:
            logger.warning(f"Couldn't get RAM usage: {e}")
            ram_percent = -1
            
        uptime = str(timedelta(seconds=int(round(time.time() - start_time))))
        
        # These operations shouldn't block or cause issues
        active_servers = len(bot_instance.guilds)
        active_users = sum(g.member_count for g in bot_instance.guilds)
        active_commands = len(bot_instance.commands)

        return jsonify({
            "latency_ms": latency,
            "cpu_usage_percent": cpu_percent,
            "ram_usage_percent": ram_percent,
            "uptime": uptime,
            "active_servers": active_servers,
            "active_users": active_users,
            "active_commands": active_commands,
            "hosting_region": "Turkey",
            "hosting_provider": "Raspberry Pi 5"
        })
        
    except Exception as e:
        logger.error(f"Error in ping endpoint: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# Legacy functions for compatibility
def initialize_api(bot):
    """Legacy function for compatibility"""
    return initialize_ping_api(bot)

# Remove the Flask app creation since we're using Blueprint
app = None
