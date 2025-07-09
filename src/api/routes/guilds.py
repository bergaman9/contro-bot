from flask import Blueprint, jsonify, request
import os
import sys
from dotenv import load_dotenv
import discord
from ...core.database import get_database_manager

# Add the parent directory to sys.path to import from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()
GUILDS_API_KEY = os.getenv("GUILDS_API_KEY", "default_key_please_change")  # Get API key from environment variables

guilds_api = Blueprint('guilds_api', __name__)
bot_instance = None
mongo_db = None

async def initialize_guilds_api(bot):
    """Initialize the guilds API with a bot instance"""
    global bot_instance, mongo_db
    bot_instance = bot
    db_manager = await get_database_manager()
    mongo_db = db_manager.database

def check_auth(request):
    """Check if the request has valid authorization"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {GUILDS_API_KEY}":
        return False
    return True

@guilds_api.route('/api/guilds', methods=['GET'])
def get_guilds():
    if not bot_instance:
        return jsonify({"error": "Bot instance not initialized"}), 500
    
    guilds_data = []
    
    for guild in bot_instance.guilds:
        guilds_data.append({
            "id": str(guild.id),
            "name": guild.name,
            "member_count": guild.member_count,
            "icon_url": str(guild.icon.url) if guild.icon else None,
            "owner_id": str(guild.owner_id),
            "region": "Turkey",  # This is a placeholder since Discord removed regions
            "created_at": guild.created_at.isoformat()
        })
    
    return jsonify({"guilds": guilds_data})

@guilds_api.route('/api/guilds/<guild_id>', methods=['GET'])
def get_guild(guild_id):
    if not bot_instance:
        return jsonify({"error": "Bot instance not initialized"}), 500
    
    guild = bot_instance.get_guild(int(guild_id))
    
    if not guild:
        return jsonify({"error": "Guild not found"}), 404
    
    # Get additional data from MongoDB if available
    guild_config = mongo_db["register"].find_one({"guild_id": int(guild_id)})
    logging_config = mongo_db["logger"].find_one({"guild_id": int(guild_id)})
    
    guild_data = {
        "id": str(guild.id),
        "name": guild.name,
        "member_count": guild.member_count,
        "icon_url": str(guild.icon.url) if guild.icon else None,
        "owner_id": str(guild.owner_id),
        "region": "Turkey",  # Placeholder
        "created_at": guild.created_at.isoformat(),
        "text_channels": len(guild.text_channels),
        "voice_channels": len(guild.voice_channels),
        "roles": len(guild.roles),
        "emojis": len(guild.emojis),
        "features": guild.features,
        "has_registration_setup": guild_config is not None,
        "has_logging_setup": logging_config is not None
    }
    
    return jsonify(guild_data)
