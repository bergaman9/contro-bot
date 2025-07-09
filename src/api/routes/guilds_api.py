"""
Guilds API endpoints for Contro Discord Bot
"""

from flask import Blueprint, jsonify, request
from ...core.config import get_config
from ...core.logger import get_logger
from ...core.database import get_database_manager
from ..middleware.auth import require_auth

guilds_bp = Blueprint('guilds', __name__)
logger = get_logger("guilds_api")


@guilds_bp.route('/', methods=['GET'])
@require_auth
async def get_guilds():
    """Get all guilds."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("guilds")
        
        guilds = await collection.find({}).to_list(length=None)
        
        return jsonify({
            'success': True,
            'guilds': guilds,
            'count': len(guilds)
        })
        
    except Exception as e:
        logger.error(f"Failed to get guilds: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get guilds'
        }), 500


@guilds_bp.route('/<guild_id>', methods=['GET'])
@require_auth
async def get_guild(guild_id):
    """Get a specific guild."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("guilds")
        
        guild = await collection.find_one({"guild_id": guild_id})
        
        if not guild:
            return jsonify({
                'success': False,
                'error': 'Guild not found'
            }), 404
        
        return jsonify({
            'success': True,
            'guild': guild
        })
        
    except Exception as e:
        logger.error(f"Failed to get guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get guild'
        }), 500


@guilds_bp.route('/<guild_id>', methods=['PUT'])
@require_auth
async def update_guild(guild_id):
    """Update a guild."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("guilds")
        
        result = await collection.update_one(
            {"guild_id": guild_id},
            {"$set": data}
        )
        
        if result.matched_count == 0:
            return jsonify({
                'success': False,
                'error': 'Guild not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Guild updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to update guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to update guild'
        }), 500
