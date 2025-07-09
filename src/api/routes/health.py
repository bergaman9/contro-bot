from flask import Flask, jsonify
import psutil
import time
import logging
from datetime import timedelta
from .commands_api import commands_api, initialize_commands_api, cleanup_rate_limits

app = Flask(__name__)
app.register_blueprint(commands_api)

# Global variable to hold the bot instance
bot_instance = None
# Track the start time of the API/bot
start_time = None

# Setup logging
logger = logging.getLogger('ping_api')

def initialize_api(bot):
    global bot_instance, start_time
    bot_instance = bot
    # Set the start time when the API is initialized
    start_time = time.time()
    # Initialize commands API with the bot instance
    initialize_commands_api(bot)
    # Set up periodic cleanup task if in a production environment
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        # Run cleanup every hour
        scheduler.add_job(cleanup_rate_limits, 'interval', hours=1)
        scheduler.start()
        logger.info("Rate limit cleanup scheduler started")
    except ImportError:
        logger.warning("APScheduler not available, rate limit cleanup will not run automatically")
    except Exception as e:
        logger.error(f"Failed to start cleanup scheduler: {e}")

@app.route('/api/ping', methods=['GET'])
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
