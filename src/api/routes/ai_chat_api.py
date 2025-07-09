"""
AI Chat API endpoints for Contro Discord Bot
"""

from flask import Blueprint, jsonify, request
from ...core.config import get_config
from ...core.logger import get_logger
from ...core.database import get_database_manager
from ..middleware.auth import require_auth

ai_chat_bp = Blueprint('ai_chat', __name__)
logger = get_logger("ai_chat_api")


@ai_chat_bp.route('/<guild_id>', methods=['GET'])
@require_auth
async def get_guild_ai_chat(guild_id):
    """Get AI chat settings for a guild."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("ai_chat")
        
        settings = await collection.find_one({"guild_id": guild_id})
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        logger.error(f"Failed to get AI chat settings for guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get AI chat settings'
        }), 500 