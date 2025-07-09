"""
Custom Status API endpoints for Contro Discord Bot
"""

from flask import Blueprint, jsonify, request
from ...core.config import get_config
from ...core.logger import get_logger
from ...core.database import get_database_manager
from ..middleware.auth import require_auth

custom_status_bp = Blueprint('custom_status', __name__)
logger = get_logger("custom_status_api")


@custom_status_bp.route('/<guild_id>', methods=['GET'])
@require_auth
async def get_guild_custom_status(guild_id):
    """Get custom status settings for a guild."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("custom_status")
        
        settings = await collection.find_one({"guild_id": guild_id})
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        logger.error(f"Failed to get custom status settings for guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get custom status settings'
        }), 500 