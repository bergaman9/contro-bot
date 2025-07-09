"""
Levelling API endpoints for Contro Discord Bot
"""

from flask import Blueprint, jsonify, request
from ...core.config import get_config
from ...core.logger import get_logger
from ...core.database import get_database_manager
from ..middleware.auth import require_auth

levelling_bp = Blueprint('levelling', __name__)
logger = get_logger("levelling_api")


@levelling_bp.route('/<guild_id>/users', methods=['GET'])
@require_auth
async def get_guild_users(guild_id):
    """Get all users for a guild."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("leveling")
        
        users = await collection.find({"guild_id": guild_id}).to_list(length=None)
        
        return jsonify({
            'success': True,
            'users': users,
            'count': len(users)
        })
        
    except Exception as e:
        logger.error(f"Failed to get users for guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get users'
        }), 500


@levelling_bp.route('/<guild_id>/users/<user_id>', methods=['GET'])
@require_auth
async def get_user_level(guild_id, user_id):
    """Get user level information."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("leveling")
        
        user = await collection.find_one({
            "guild_id": guild_id,
            "user_id": user_id
        })
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'user': user
        })
        
    except Exception as e:
        logger.error(f"Failed to get user {user_id} for guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user'
        }), 500


@levelling_bp.route('/<guild_id>/leaderboard', methods=['GET'])
@require_auth
async def get_leaderboard(guild_id):
    """Get guild leaderboard."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("leveling")
        
        leaderboard = await collection.find(
            {"guild_id": guild_id}
        ).sort("xp", -1).limit(10).to_list(length=None)
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard
        })
        
    except Exception as e:
        logger.error(f"Failed to get leaderboard for guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get leaderboard'
        }), 500 