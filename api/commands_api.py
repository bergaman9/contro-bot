from flask import Blueprint, jsonify, request
import json
import os
import discord
import time
import logging

commands_api = Blueprint('commands_api', __name__)
bot_instance = None

# Rate limiting configuration - stricter limits to prevent Discord API rate limits
request_history = {}  # {ip: [timestamps...]}
RATE_LIMIT = 10  # Reduced number of allowed requests
RATE_WINDOW = 3600  # Time window in seconds (1 hour instead of 1 minute)

# Cache configuration
commands_cache = None
last_cache_update = 0
CACHE_TTL = 1800  # Cache time-to-live in seconds (30 minutes)

# Setup logging
logger = logging.getLogger('commands_api')

def initialize_commands_api(bot):
    global bot_instance
    bot_instance = bot
    # Pre-populate the cache on init if possible
    try:
        refresh_commands_cache()
    except Exception as e:
        logger.error(f"Failed to initialize commands cache: {e}")

def refresh_commands_cache():
    """Refresh the commands cache if needed"""
    global commands_cache, last_cache_update
    
    current_time = time.time()
    
    # Return early if cache is still valid
    if commands_cache and (current_time - last_cache_update) < CACHE_TTL:
        return commands_cache
        
    # Generate fresh data
    commands_cache = generate_command_data()
    last_cache_update = current_time
    logger.info(f"Commands cache refreshed, next update in {CACHE_TTL} seconds")
    return commands_cache

@commands_api.route('/api/commands', methods=['GET'])
def get_commands():
    # Implement stricter rate limiting
    client_ip = request.remote_addr
    current_time = time.time()
    
    if client_ip not in request_history:
        request_history[client_ip] = []
    
    # Clean old requests outside the window
    request_history[client_ip] = [ts for ts in request_history[client_ip] 
                                  if current_time - ts < RATE_WINDOW]
    
    # Check if limit exceeded
    if len(request_history[client_ip]) >= RATE_LIMIT:
        oldest_request = min(request_history[client_ip])
        reset_time = oldest_request + RATE_WINDOW
        retry_after = int(reset_time - current_time)
        
        # Log rate limit hit
        logger.warning(f"Rate limit exceeded for IP {client_ip}, retry after {retry_after}s")
        
        return jsonify({
            "error": "Rate limit exceeded",
            "retry_after": retry_after,
            "limit": RATE_LIMIT,
            "window": f"{RATE_WINDOW/3600} hours"
        }), 429
    
    # Add current request to history
    request_history[client_ip].append(current_time)
    
    try:
        # Use cached data if available and not expired
        command_data = refresh_commands_cache()
        if command_data:
            return jsonify(command_data)
        else:
            return jsonify({"error": "Failed to retrieve command data"}), 500
            
    except Exception as e:
        logger.error(f"Error serving command data: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

def generate_command_data():
    """Generate command data dynamically from the bot's commands with error handling"""
    try:
        command_data = {}
        
        # Read from commands.json as a fallback or base
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'commands.json')
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    command_data = json.load(file)
                    logger.debug("Loaded base command data from commands.json")
            except Exception as e:
                logger.error(f"Failed to read commands.json: {e}")
        
        # If bot is available, update with live data
        if bot_instance:
            for command in bot_instance.commands:
                try:
                    cog_name = command.cog_name.lower() if command.cog_name else "uncategorized"
                    
                    # Skip deprecated or special cogs if needed
                    # if cog_name in ["deprecated_cog_name"]:
                    #     continue
                        
                    if cog_name not in command_data:
                        command_data[cog_name] = []
                    
                    # Determine permissions dynamically
                    permissions = []
                    if command.checks:
                        for check in command.checks:
                            if hasattr(check, "__name__"):
                                permissions.append(check.__name__)
                            elif hasattr(check, "__qualname__"):
                                permissions.append(check.__qualname__)
                            else:
                                permissions.append("custom_check")
                    else:
                        permissions.append("@everyone")
                    
                    # Check for specific permission requirements
                    if hasattr(command, "default_permissions"):
                        perms = discord.Permissions(command.default_permissions)
                        permissions.extend([perm for perm, value in perms if value])
                    
                    command_info = {
                        "name": command.name,
                        "description": command.description or "No description available",
                        "permissions": permissions
                    }
                    
                    # Check if command already exists and update it
                    existing_command = next((cmd for cmd in command_data[cog_name] if cmd["name"] == command.name), None)
                    if existing_command:
                        existing_command.update(command_info)
                    else:
                        command_data[cog_name].append(command_info)
                except Exception as e:
                    logger.error(f"Error processing command {getattr(command, 'name', 'unknown')}: {e}")
        
        # Remove any deprecated categories if they exist
        deprecated_categories = ["bionluk"]  # Keep this for any future deprecated cogs
        for category in deprecated_categories:
            if category in command_data:
                del command_data[category]
            
        return command_data
    
    except Exception as e:
        logger.error(f"Error generating command data: {e}")
        return {"error": str(e)}

# Cleanup function to periodically purge old rate limit records
def cleanup_rate_limits():
    """Remove old rate limit entries to prevent memory leaks"""
    try:
        current_time = time.time()
        count_before = len(request_history)
        
        # Remove IPs with no recent requests
        for ip in list(request_history.keys()):
            # First clean old timestamps for this IP
            request_history[ip] = [ts for ts in request_history[ip] 
                                  if current_time - ts < RATE_WINDOW]
            
            # If no timestamps remain, remove the IP entirely
            if not request_history[ip]:
                del request_history[ip]
                
        count_after = len(request_history)
        if count_before > count_after:
            logger.info(f"Rate limit cleanup: removed {count_before - count_after} inactive IPs")
            
    except Exception as e:
        logger.error(f"Error during rate limit cleanup: {e}")
