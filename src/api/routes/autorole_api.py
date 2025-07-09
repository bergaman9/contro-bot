"""
Autorole API endpoints for Contro Discord Bot
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, List
import logging
from ...core.database import get_database_manager
from ...core.config import get_config
from ...core.logger import get_logger
from ...core.database import get_database_manager
from ..middleware.auth import require_auth

# Create blueprint
autorole_api = Blueprint('autorole_api', __name__, url_prefix='/api/autorole')
logger = get_logger("autorole_api")

# Initialize bot reference
bot_instance = None

async def initialize_autorole_api(bot):
    """Initialize the autorole API with bot reference"""
    global bot_instance
    bot_instance = bot

@autorole_api.route('/settings/<guild_id>', methods=['GET'])
@require_auth
async def get_guild_autorole(guild_id):
    """Get autorole settings for a guild."""
    try:
        db_manager = await get_database_manager()
        collection = db_manager.get_collection("autorole")
        
        settings = await collection.find_one({"guild_id": guild_id})
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        logger.error(f"Failed to get autorole settings for guild {guild_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get autorole settings'
        }), 500

@autorole_api.route('/settings/<guild_id>', methods=['POST'])
def update_autorole_settings(guild_id: str):
    """Update autorole settings for a guild"""
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
        result = asyncio.run(update_autorole_settings_in_db(guild_id, data))
        
        return jsonify({
            "success": True,
            "data": result,
            "message": "Settings updated successfully"
        })

    except Exception as e:
        logging.error(f"Error updating autorole settings: {e}")
        return jsonify({"error": "Internal server error"}), 500

@autorole_api.route('/rules/<guild_id>', methods=['GET'])
def get_autorole_rules(guild_id: str):
    """Get autorole rules for a guild"""
    try:
        if not bot_instance:
            return jsonify({"error": "Bot not initialized"}), 500

        # Get guild
        guild = bot_instance.get_guild(int(guild_id))
        if not guild:
            return jsonify({"error": "Guild not found"}), 404

        # Get rules from database
        rules = asyncio.run(get_autorole_rules_from_db(guild_id))
        
        return jsonify({
            "success": True,
            "data": rules
        })

    except Exception as e:
        logging.error(f"Error getting autorole rules: {e}")
        return jsonify({"error": "Internal server error"}), 500

@autorole_api.route('/rules/<guild_id>', methods=['POST'])
def create_autorole_rule(guild_id: str):
    """Create a new autorole rule"""
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

        # Create rule in database
        result = asyncio.run(create_autorole_rule_in_db(guild_id, data))
        
        return jsonify({
            "success": True,
            "data": result,
            "message": "Rule created successfully"
        })

    except Exception as e:
        logging.error(f"Error creating autorole rule: {e}")
        return jsonify({"error": "Internal server error"}), 500

@autorole_api.route('/analytics/<guild_id>', methods=['GET'])
def get_autorole_analytics(guild_id: str):
    """Get autorole analytics for a guild"""
    try:
        if not bot_instance:
            return jsonify({"error": "Bot not initialized"}), 500

        # Get guild
        guild = bot_instance.get_guild(int(guild_id))
        if not guild:
            return jsonify({"error": "Guild not found"}), 404

        # Get analytics from database
        analytics = asyncio.run(get_autorole_analytics_from_db(guild_id))
        
        return jsonify({
            "success": True,
            "data": analytics
        })

    except Exception as e:
        logging.error(f"Error getting autorole analytics: {e}")
        return jsonify({"error": "Internal server error"}), 500

@autorole_api.route('/assign/<guild_id>/<user_id>', methods=['POST'])
def manually_assign_roles(guild_id: str, user_id: str):
    """Manually assign autoroles to a user"""
    try:
        if not bot_instance:
            return jsonify({"error": "Bot not initialized"}), 500

        data = request.get_json() or {}
        role_ids = data.get('role_ids', [])

        # Get guild and member
        guild = bot_instance.get_guild(int(guild_id))
        if not guild:
            return jsonify({"error": "Guild not found"}), 404

        member = guild.get_member(int(user_id))
        if not member:
            return jsonify({"error": "Member not found"}), 404

        # Assign roles
        assigned_roles = asyncio.run(assign_autoroles_to_member(guild, member, role_ids))
        
        return jsonify({
            "success": True,
            "data": {
                "assigned_roles": assigned_roles,
                "user_id": user_id,
                "guild_id": guild_id
            },
            "message": f"Assigned {len(assigned_roles)} roles to {member.display_name}"
        })

    except Exception as e:
        logging.error(f"Error manually assigning roles: {e}")
        return jsonify({"error": "Internal server error"}), 500

@autorole_api.route('/status/<guild_id>', methods=['GET'])
def get_autorole_status(guild_id: str):
    """Get autorole system status for a guild"""
    try:
        if not bot_instance:
            return jsonify({"error": "Bot not initialized"}), 500

        # Get guild
        guild = bot_instance.get_guild(int(guild_id))
        if not guild:
            return jsonify({"error": "Guild not found"}), 404

        # Get status from database
        status = asyncio.run(get_autorole_status_from_db(guild_id))
        
        return jsonify({
            "success": True,
            "data": status
        })

    except Exception as e:
        logging.error(f"Error getting autorole status: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Database helper functions
async def get_autorole_settings_from_db(guild_id: str) -> Dict[str, Any]:
    """Get autorole settings from database"""
    try:
        db = await get_async_db()
        collection = db.get_collection('autorole_settings')
        
        settings = await collection.find_one({'guild_id': guild_id})
        if not settings:
            # Return default settings
            return {
                'guild_id': guild_id,
                'enabled': False,
                'default_role': None,
                'bot_role': None,
                'verification_role': None,
                'join_delay': 0,
                'require_verification': False,
                'auto_roles': [],
                'last_updated': datetime.utcnow()
            }
        
        return settings
    except Exception as e:
        logging.error(f"Database error getting autorole settings: {e}")
        return {}

async def update_autorole_settings_in_db(guild_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update autorole settings in database"""
    try:
        db = await get_async_db()
        collection = db.get_collection('autorole_settings')
        
        update_data = {
            **data,
            'guild_id': guild_id,
            'last_updated': datetime.utcnow()
        }
        
        result = await collection.find_one_and_update(
            {'guild_id': guild_id},
            {'$set': update_data},
            upsert=True,
            return_document=True
        )
        
        return result
    except Exception as e:
        logging.error(f"Database error updating autorole settings: {e}")
        raise

async def get_autorole_rules_from_db(guild_id: str) -> List[Dict[str, Any]]:
    """Get autorole rules from database"""
    try:
        db = await get_async_db()
        collection = db.get_collection('autorole_rules')
        
        rules = await collection.find({'guild_id': guild_id}).to_list(length=None)
        return rules
    except Exception as e:
        logging.error(f"Database error getting autorole rules: {e}")
        return []

async def create_autorole_rule_in_db(guild_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create autorole rule in database"""
    try:
        db = await get_async_db()
        collection = db.get_collection('autorole_rules')
        
        rule_data = {
            **data,
            'guild_id': guild_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        result = await collection.insert_one(rule_data)
        rule_data['_id'] = result.inserted_id
        
        return rule_data
    except Exception as e:
        logging.error(f"Database error creating autorole rule: {e}")
        raise

async def get_autorole_analytics_from_db(guild_id: str) -> Dict[str, Any]:
    """Get autorole analytics from database"""
    try:
        db = await get_async_db()
        
        # Get various analytics data
        settings_collection = db.get_collection('autorole_settings')
        logs_collection = db.get_collection('autorole_logs')
        
        # Get settings
        settings = await settings_collection.find_one({'guild_id': guild_id})
        
        # Get recent logs (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_logs = await logs_collection.find({
            'guild_id': guild_id,
            'created_at': {'$gte': thirty_days_ago}
        }).to_list(length=None)
        
        # Calculate statistics
        total_assignments = len(recent_logs)
        successful_assignments = len([log for log in recent_logs if log.get('success', False)])
        failed_assignments = total_assignments - successful_assignments
        
        # Group by role
        role_stats = {}
        for log in recent_logs:
            role_id = log.get('role_id')
            if role_id:
                if role_id not in role_stats:
                    role_stats[role_id] = {'assigned': 0, 'failed': 0}
                if log.get('success', False):
                    role_stats[role_id]['assigned'] += 1
                else:
                    role_stats[role_id]['failed'] += 1
        
        return {
            'total_assignments': total_assignments,
            'successful_assignments': successful_assignments,
            'failed_assignments': failed_assignments,
            'success_rate': (successful_assignments / total_assignments * 100) if total_assignments > 0 else 0,
            'role_statistics': role_stats,
            'recent_activity': recent_logs[-10:] if recent_logs else [],  # Last 10 activities
            'enabled': settings.get('enabled', False) if settings else False
        }
    except Exception as e:
        logging.error(f"Database error getting autorole analytics: {e}")
        return {}

async def assign_autoroles_to_member(guild, member, role_ids: List[str]) -> List[str]:
    """Assign autoroles to a member"""
    try:
        assigned_roles = []
        
        for role_id in role_ids:
            try:
                role = guild.get_role(int(role_id))
                if role and role not in member.roles:
                    await member.add_roles(role, reason="AutoRole: Manual assignment via API")
                    assigned_roles.append(role_id)
                    
                    # Log the assignment
                    await log_autorole_assignment(guild.id, member.id, role_id, True, "Manual assignment")
                    
            except Exception as e:
                logging.error(f"Error assigning role {role_id} to {member.id}: {e}")
                await log_autorole_assignment(guild.id, member.id, role_id, False, str(e))
        
        return assigned_roles
    except Exception as e:
        logging.error(f"Error in assign_autoroles_to_member: {e}")
        raise

async def get_autorole_status_from_db(guild_id: str) -> Dict[str, Any]:
    """Get autorole system status from database"""
    try:
        db = await get_async_db()
        
        settings_collection = db.get_collection('autorole_settings')
        rules_collection = db.get_collection('autorole_rules')
        
        # Get settings and rules
        settings = await settings_collection.find_one({'guild_id': guild_id})
        rules = await rules_collection.find({'guild_id': guild_id}).to_list(length=None)
        
        return {
            'enabled': settings.get('enabled', False) if settings else False,
            'total_rules': len(rules),
            'active_rules': len([r for r in rules if r.get('enabled', True)]),
            'has_default_role': bool(settings.get('default_role') if settings else None),
            'has_bot_role': bool(settings.get('bot_role') if settings else None),
            'last_updated': settings.get('last_updated') if settings else None
        }
    except Exception as e:
        logging.error(f"Database error getting autorole status: {e}")
        return {}

async def log_autorole_assignment(guild_id: int, user_id: int, role_id: str, success: bool, reason: str):
    """Log autorole assignment"""
    try:
        db = await get_async_db()
        collection = db.get_collection('autorole_logs')
        
        log_entry = {
            'guild_id': guild_id,
            'user_id': user_id,
            'role_id': role_id,
            'success': success,
            'reason': reason,
            'created_at': datetime.utcnow()
        }
        
        await collection.insert_one(log_entry)
    except Exception as e:
        logging.error(f"Error logging autorole assignment: {e}") 