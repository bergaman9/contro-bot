from flask import Blueprint, request, jsonify
from datetime import datetime
import asyncio
from typing import Dict, Any
import logging
import discord
from ...core.database import get_database_manager

# Create blueprint
welcome_api = Blueprint('welcome_api', __name__, url_prefix='/api/welcome')

# Initialize bot reference
bot_instance = None

def initialize_welcome_api(bot):
    """Initialize the welcome API with bot reference"""
    global bot_instance
    bot_instance = bot

@welcome_api.route('/settings/<guild_id>', methods=['GET'])
def get_welcome_settings(guild_id: str):
    """Get welcome settings for a guild"""
    try:
        if not bot_instance:
            return jsonify({"error": "Bot not initialized"}), 500

        # Get guild
        guild = bot_instance.get_guild(int(guild_id))
        if not guild:
            return jsonify({"error": "Guild not found"}), 404

        # Get welcome settings from database
        settings = asyncio.run(get_welcome_settings_from_db(guild_id))
        
        return jsonify({
            "success": True,
            "data": settings
        })

    except Exception as e:
        logging.error(f"Error getting welcome settings: {e}")
        return jsonify({"error": "Internal server error"}), 500

@welcome_api.route('/settings/<guild_id>', methods=['POST'])
def update_welcome_settings(guild_id: str):
    """Update welcome settings for a guild"""
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
        result = asyncio.run(update_welcome_settings_in_db(guild_id, data))
        
        return jsonify({
            "success": True,
            "data": result,
            "message": "Welcome settings updated successfully"
        })

    except Exception as e:
        logging.error(f"Error updating welcome settings: {e}")
        return jsonify({"error": "Internal server error"}), 500

@welcome_api.route('/test/<guild_id>', methods=['POST'])
def test_welcome_message(guild_id: str):
    """Send a test welcome message"""
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
        result = asyncio.run(send_test_welcome_message(guild, data))
        
        return jsonify({
            "success": True,
            "data": result,
            "message": "Test welcome message sent successfully"
        })

    except Exception as e:
        logging.error(f"Error sending test welcome message: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Database functions
async def get_welcome_settings_from_db(guild_id: str) -> Dict[str, Any]:
    """Get welcome settings from database"""
    try:
        db = await get_database()
        collection = db.get_collection('welcomer')
        
        settings = await collection.find_one({"guild_id": guild_id})
        if settings:
            # Convert ObjectId to string for JSON serialization
            settings['_id'] = str(settings['_id'])
        
        return settings or {}
    except Exception as e:
        logging.error(f"Database error getting welcome settings: {e}")
        return {}

async def update_welcome_settings_in_db(guild_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update welcome settings in database"""
    try:
        db = await get_database()
        collection = db.get_collection('welcomer')
        
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
        logging.error(f"Database error updating welcome settings: {e}")
        return {}

async def send_test_welcome_message(guild, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Send a test welcome message using the provided settings"""
    try:
        # Get test channel
        channel_id = settings.get('welcome_channel_id')
        if not channel_id:
            return {"error": "No welcome channel configured"}
        
        channel = guild.get_channel(int(channel_id))
        if not channel:
            return {"error": "Welcome channel not found"}
        
        # Create test user data
        test_user = {
            "id": 123456789,
            "name": "TestUser",
            "display_name": "Test User",
            "mention": "<@123456789>"
        }
        
        # Format message
        message_content = format_welcome_message(settings, test_user, guild)
        
        # Send message
        if settings.get('background_url'):
            # Send with image
            embed = create_welcome_embed(settings, test_user, guild)
            await channel.send(content=message_content, embed=embed)
        else:
            # Send text only
            await channel.send(content=message_content)
        
        # Send DM if enabled
        if settings.get('welcome_dm_enabled') and settings.get('welcome_dm_message'):
            dm_message = format_dm_message(settings, test_user, guild)
            # Note: We can't actually send DM to a test user, so we'll just log it
            logging.info(f"Would send DM to test user: {dm_message}")
        
        return {
            "channel_id": channel_id,
            "channel_name": channel.name,
            "message_sent": True,
            "dm_enabled": settings.get('welcome_dm_enabled', False)
        }
        
    except Exception as e:
        logging.error(f"Error sending test welcome message: {e}")
        return {"error": str(e)}

def format_welcome_message(settings: Dict[str, Any], user: Dict[str, Any], guild) -> str:
    """Format welcome message with variables"""
    message = settings.get('description', '')
    
    # Replace variables
    message = message.replace('{mention}', user['mention'])
    message = message.replace('{user}', user['name'])
    message = message.replace('{server}', guild.name)
    message = message.replace('{member_count}', str(guild.member_count))
    message = message.replace('{count}', str(guild.member_count))
    
    return message

def format_dm_message(settings: Dict[str, Any], user: Dict[str, Any], guild) -> str:
    """Format DM message with variables"""
    message = settings.get('welcome_dm_message', '')
    
    # Replace variables
    message = message.replace('{user}', user['name'])
    message = message.replace('{server}', guild.name)
    message = message.replace('{member_count}', str(guild.member_count))
    message = message.replace('{count}', str(guild.member_count))
    
    return message

def create_welcome_embed(settings: Dict[str, Any], user: Dict[str, Any], guild) -> discord.Embed:
    """Create welcome embed"""
    embed = discord.Embed()
    
    # Set title
    title = settings.get('welcome_text', 'HOŞ GELDİN!')
    embed.title = title
    
    # Set description
    description = format_welcome_message(settings, user, guild)
    embed.description = description
    
    # Set color
    color = settings.get('color', 16655871)  # Default purple
    embed.color = color
    
    # Set image if background URL is provided
    background_url = settings.get('background_url')
    if background_url:
        embed.set_image(url=background_url)
    
    # Set footer
    embed.set_footer(text=f"{guild.name} • {guild.member_count} üye")
    
    return embed 