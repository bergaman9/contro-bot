"""
Game Logs API endpoints for Contro Discord Bot
"""

from flask import Blueprint, jsonify, request
from ...core.config import get_config
from ...core.logger import get_logger
from ...core.database import get_database_manager
from ..middleware.auth import require_auth

game_logs_bp = Blueprint('game_logs', __name__)
logger = get_logger("game_logs_api")


@game_logs_bp.route('/<guild_id>', methods=['GET'])
@require_auth
async def get_guild_game_logs(guild_id):
    """Get game logs for a guild."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("game_logs")
        
        logs = await collection.find({"guild_id": guild_id}).to_list(length=None)
        
        return jsonify({
            'success': True,
            'logs': logs
        })
        
    except Exception as e:
        logger.error(f"Failed to get game logs for guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get game logs'
        }), 500 