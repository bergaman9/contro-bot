"""
Giveaways API endpoints for Contro Discord Bot
"""

from flask import Blueprint, jsonify, request
from ...core.config import get_config
from ...core.logger import get_logger
from ...core.database import get_database_manager
from ..middleware.auth import require_auth

giveaways_bp = Blueprint('giveaways', __name__)
logger = get_logger("giveaways_api")


@giveaways_bp.route('/<guild_id>', methods=['GET'])
@require_auth
async def get_guild_giveaways(guild_id):
    """Get giveaways for a guild."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("giveaways")
        
        giveaways = await collection.find({"guild_id": guild_id}).to_list(length=None)
        
        return jsonify({
            'success': True,
            'giveaways': giveaways
        })
        
    except Exception as e:
        logger.error(f"Failed to get giveaways for guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get giveaways'
        }), 500 