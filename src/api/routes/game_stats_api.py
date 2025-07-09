"""
Game Stats API endpoints for Contro Discord Bot
"""

from flask import Blueprint, jsonify, request
from ...core.config import get_config
from ...core.logger import get_logger
from ...core.database import get_database_manager
from ..middleware.auth import require_auth

game_stats_bp = Blueprint('game_stats', __name__)
logger = get_logger("game_stats_api")


@game_stats_bp.route('/<guild_id>', methods=['GET'])
@require_auth
async def get_guild_game_stats(guild_id):
    """Get game stats for a guild."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("game_stats")
        
        stats = await collection.find({"guild_id": guild_id}).to_list(length=None)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Failed to get game stats for guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get game stats'
        }), 500 