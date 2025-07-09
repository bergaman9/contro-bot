"""
Byebye API endpoints for Contro Discord Bot
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import asyncio
from typing import Dict, Any
import logging
import discord
from ...core.database import get_database_manager
from ...core.config import get_config
from ...core.logger import get_logger
from ...core.database import get_database_manager
from ..middleware.auth import require_auth

# Create blueprint
byebye_api = Blueprint('byebye_api', __name__, url_prefix='/api/byebye')
logger = get_logger("byebye_api")

# Initialize bot reference
bot_instance = None

def initialize_byebye_api(bot):
    """Initialize the byebye API with bot reference"""
    global bot_instance
    bot_instance = bot

@byebye_api.route('/settings/<guild_id>', methods=['GET'])
@require_auth
async def get_guild_byebye(guild_id):
    """Get byebye settings for a guild."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("byebye")
        
        settings = await collection.find_one({"guild_id": guild_id})
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        logger.error(f"Failed to get byebye settings for guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get byebye settings'
        }), 500

@byebye_api.route('/settings/<guild_id>', methods=['POST'])
def update_byebye_settings(guild_id: str):
    """Update byebye settings for a guild"""
    try:
        if not bot_instance:
            return jsonify({"error": "Bot not initialized"}), 500

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Get guild
        guild = bot_instance.get_guild(int(guild_id))
        if not guild:
            return jsonify({"error": "Guild not found"}), 404

        # Update settings in database
        result = asyncio.run(update_byebye_settings_in_db(guild_id, data))
        
        return jsonify({
            "success": True,
            "data": result,
            "message": "ByeBye settings updated successfully"
        })

    except Exception as e:
        logging.error(f"Error updating byebye settings: {e}")
        return jsonify({"error": "Internal server error"}), 500

@byebye_api.route('/test/<guild_id>', methods=['POST'])
def test_byebye_message(guild_id: str):
    """Send a test byebye message"""
    try:
        if not bot_instance:
            return jsonify({"error": "Bot not initialized"}), 500

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Get guild
        guild = bot_instance.get_guild(int(guild_id))
        if not guild:
            return jsonify({"error": "Guild not found"}), 404

        # Send test message
        result = asyncio.run(send_test_byebye_message(guild, data))
        
        return jsonify({
            "success": True,
            "data": result,
            "message": "Test byebye message sent successfully"
        })

    except Exception as e:
        logging.error(f"Error sending test byebye message: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Database functions
async def get_byebye_settings_from_db(guild_id: str) -> Dict[str, Any]:
    """Get byebye settings from database"""
    try:
        db = await get_database()
        collection = db.get_collection('byebye')
        
        settings = await collection.find_one({"guild_id": guild_id})
        if settings:
            # Convert ObjectId to string for JSON serialization
            settings['_id'] = str(settings['_id'])
        
        return settings or {}
    except Exception as e:
        logging.error(f"Database error getting byebye settings: {e}")
        return {}

async def update_byebye_settings_in_db(guild_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update byebye settings in database"""
    try:
        db = await get_database()
        collection = db.get_collection('byebye')
        
        # Add timestamp
        data['last_updated'] = datetime.utcnow()
        
        # Upsert the document
        result = await collection.find_one_and_update(
            {"guild_id": guild_id},
            {"$set": data},
            upsert=True,
            return_document=True
        )
        
        if result:
            result['_id'] = str(result['_id'])
        
        return result or {}
    except Exception as e:
        logging.error(f"Database error updating byebye settings: {e}")
        return {}

async def send_test_byebye_message(guild, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Send a test byebye message using the provided settings"""
    try:
        # Get test channel
        channel_id = settings.get('byebye_channel_id')
        if not channel_id:
            return {"error": "No byebye channel configured"}
        
        channel = guild.get_channel(int(channel_id))
        if not channel:
            return {"error": "ByeBye channel not found"}
        
        # Create test user data
        test_user = {
            "id": 123456789,
            "name": "TestUser",
            "display_name": "Test User"
        }
        
        # Format message
        message_content = format_byebye_message(settings, test_user, guild)
        
        # Send message
        if settings.get('background_url'):
            # Send with image
            embed = create_byebye_embed(settings, test_user, guild)
            await channel.send(content=message_content, embed=embed)
        else:
            # Send text only
            await channel.send(content=message_content)
        
        # Send DM if enabled
        if settings.get('byebye_dm_enabled') and settings.get('byebye_dm_message'):
            dm_message = format_byebye_dm_message(settings, test_user, guild)
            # Note: We can't actually send DM to a test user, so we'll just log it
            logging.info(f"Would send DM to test user: {dm_message}")
        
        return {
            "channel_id": channel_id,
            "channel_name": channel.name,
            "message_sent": True,
            "dm_enabled": settings.get('byebye_dm_enabled', False)
        }
        
    except Exception as e:
        logging.error(f"Error sending test byebye message: {e}")
        return {"error": str(e)}

def format_byebye_message(settings: Dict[str, Any], user: Dict[str, Any], guild) -> str:
    """Format byebye message with variables"""
    message = settings.get('description', '')
    
    # Replace variables
    message = message.replace('{user}', user['name'])
    message = message.replace('{server}', guild.name)
    message = message.replace('{member_count}', str(guild.member_count))
    message = message.replace('{count}', str(guild.member_count))
    
    return message

def format_byebye_dm_message(settings: Dict[str, Any], user: Dict[str, Any], guild) -> str:
    """Format byebye DM message with variables"""
    message = settings.get('byebye_dm_message', '')
    
    # Replace variables
    message = message.replace('{user}', user['name'])
    message = message.replace('{server}', guild.name)
    message = message.replace('{member_count}', str(guild.member_count))
    message = message.replace('{count}', str(guild.member_count))
    
    return message

def create_byebye_embed(settings: Dict[str, Any], user: Dict[str, Any], guild) -> discord.Embed:
    """Create byebye embed"""
    embed = discord.Embed()
    
    # Set title
    title = settings.get('byebye_text', 'GÜLE GÜLE!')
    embed.title = title
    
    # Set description
    description = format_byebye_message(settings, user, guild)
    embed.description = description
    
    # Set color
    color = settings.get('color', 16711680)  # Default red
    embed.color = color
    
    # Set image if background URL is provided
    background_url = settings.get('background_url')
    if background_url:
        embed.set_image(url=background_url)
    
    # Set footer
    embed.set_footer(text=f"{guild.name} • {guild.member_count} üye")
    
    return embed 