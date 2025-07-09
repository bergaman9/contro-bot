"""
Custom Commands API endpoints for Contro Discord Bot
"""

from flask import Blueprint, jsonify, request
from ...core.config import get_config
from ...core.logger import get_logger
from ...core.database import get_database_manager
from ..middleware.auth import require_auth

custom_commands_bp = Blueprint('custom_commands', __name__)
logger = get_logger("custom_commands_api")


@custom_commands_bp.route('/<guild_id>', methods=['GET'])
@require_auth
async def get_guild_custom_commands(guild_id):
    """Get custom commands for a guild."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("custom_commands")
        
        commands = await collection.find({"guild_id": guild_id}).to_list(length=None)
        
        return jsonify({
            'success': True,
            'commands': commands
        })
        
    except Exception as e:
        logger.error(f"Failed to get custom commands for guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get custom commands'
        }), 500 