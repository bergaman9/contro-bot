"""
Giveaway API endpoints for public dashboard access
Handles giveaway creation, management, and winner selection
"""

from flask import Blueprint, jsonify, request
from typing import Optional, Dict, Any, List
import asyncio
import logging
from datetime import datetime
import random
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import discord

from ...core.logger import get_logger
from ...core.database import get_database_manager
from ...utils.database.db_manager import db_manager
from ..middleware.auth import require_auth

giveaway_bp = Blueprint('giveaway', __name__)
logger = get_logger("giveaway_api")


@giveaway_bp.route('/create', methods=['POST'])
@require_auth
def create_giveaway():
    """Create a new giveaway via API."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['guild_id', 'title', 'prize', 'channel_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Get database connection (sync)
        load_dotenv()
        mongo_uri = os.getenv("MONGO_DB") or os.getenv("MONGODB_URI")
        if not mongo_uri:
            return jsonify({
                'success': False,
                'error': 'MongoDB URI not configured'
            }), 500
        
        try:
            client = MongoClient(mongo_uri)
            db_name = os.getenv("DB_NAME") or os.getenv("DB", "contro-bot-db")
            db = client[db_name]
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to connect to database: {e}'
            }), 500
        
        # Create giveaway document
        giveaway_data = {
            'guild_id': data['guild_id'],
            'title': data['title'],
            'prize': data['prize'],
            'description': data.get('description', ''),
            'end_time': data.get('end_time', datetime.now().timestamp() + 86400),  # Default 24 hours
            'winner_count': data.get('winner_count', 1),
            'channel_id': data['channel_id'],
            'message_id': None,  # Will be set when bot creates the message
            'participants': [],
            'winners': [],
            'ended': False,
            'requirements': data.get('requirements', {
                'level_required': 0,
                'role_required': '',
                'invite_required': 0,
                'message_required': 0
            }),
            'embed_color': data.get('embed_color', '#FF6B9D'),
            'button_text': data.get('button_text', 'Join Giveaway'),
            'auto_end': data.get('auto_end', True),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Insert into database (sync)
        result = db['giveaways'].insert_one(giveaway_data)
        
        # Return success, Discord message will be handled by the bot background task
        return jsonify({
            'success': True,
            'data': {
                'giveaway_id': str(result.inserted_id),
                'message_id': None,
                'channel_id': data['channel_id']
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating giveaway: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to create giveaway: {e}'
        }), 500


@giveaway_bp.route('/<giveaway_id>/end', methods=['POST'])
@require_auth
def end_giveaway(giveaway_id: str):
    """End a giveaway and select winners."""
    try:
        data = request.get_json()
        
        # Get database connection (sync)
        from pymongo import MongoClient
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        mongo_uri = os.getenv("MONGO_DB") or os.getenv("MONGODB_URI")
        if not mongo_uri:
            return jsonify({
                'success': False,
                'error': 'MongoDB URI not configured'
            }), 500
        
        try:
            client = MongoClient(mongo_uri)
            db_name = os.getenv("DB_NAME") or os.getenv("DB", "contro-bot-db")
            db = client[db_name]
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to connect to database: {e}'
            }), 500
        
        # Find the giveaway
        from bson import ObjectId
        giveaway = db['giveaways'].find_one({'_id': ObjectId(giveaway_id)})
        
        if not giveaway:
            return jsonify({
                'success': False,
                'error': 'Giveaway not found'
            }), 404
        
        if giveaway.get('ended', False):
            return jsonify({
                'success': False,
                'error': 'Giveaway is already ended'
            }), 400
        
        # Get participants
        participants = giveaway.get('participants', [])
        
        # Select winners
        winners = []
        winner_count = giveaway.get('winner_count', 1)
        
        if participants:
            # Shuffle participants and select winners
            shuffled = list(participants)
            random.shuffle(shuffled)
            winners = shuffled[:min(winner_count, len(shuffled))]
        
        # Update giveaway
        db['giveaways'].update_one(
            {'_id': ObjectId(giveaway_id)},
            {
                '$set': {
                    'ended': True,
                    'ended_at': datetime.now(),
                    'winners': winners,
                    'final_participant_count': len(participants)
                }
            }
        )
        
        return jsonify({
            'success': True,
            'data': {
                'giveaway_id': giveaway_id,
                'winners': winners,
                'participant_count': len(participants)
            }
        })
        
    except Exception as e:
        logger.error(f"Error ending giveaway: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to end giveaway: {e}'
        }), 500


@giveaway_bp.route('/<giveaway_id>/join', methods=['POST'])
def join_giveaway(giveaway_id: str):
    """Join a giveaway."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id'
            }), 400
        
        # Get database connection (sync)
        from pymongo import MongoClient
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        mongo_uri = os.getenv("MONGO_DB") or os.getenv("MONGODB_URI")
        if not mongo_uri:
            return jsonify({
                'success': False,
                'error': 'MongoDB URI not configured'
            }), 500
        
        try:
            client = MongoClient(mongo_uri)
            db_name = os.getenv("DB_NAME") or os.getenv("DB", "contro-bot-db")
            db = client[db_name]
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to connect to database: {e}'
            }), 500
        
        # Find the giveaway
        from bson import ObjectId
        giveaway = db['giveaways'].find_one({'_id': ObjectId(giveaway_id)})
        
        if not giveaway:
            return jsonify({
                'success': False,
                'error': 'Giveaway not found'
            }), 404
        
        if giveaway.get('ended', False):
            return jsonify({
                'success': False,
                'error': 'Giveaway has already ended'
            }), 400
        
        # Check if user is already participating
        participants = giveaway.get('participants', [])
        if any(p.get('user_id') == user_id for p in participants):
            return jsonify({
                'success': False,
                'error': 'You are already participating in this giveaway'
            }), 400
        
        # Add user to participants
        participant_data = {
            'user_id': user_id,
            'joined_at': datetime.now()
        }
        
        db['giveaways'].update_one(
            {'_id': ObjectId(giveaway_id)},
            {'$push': {'participants': participant_data}}
        )
        
        return jsonify({
            'success': True,
            'message': 'Successfully joined the giveaway'
        })
        
    except Exception as e:
        logger.error(f"Error joining giveaway: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to join giveaway: {e}'
        }), 500


@giveaway_bp.route('/<giveaway_id>/leave', methods=['POST'])
def leave_giveaway(giveaway_id: str):
    """Leave a giveaway."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id'
            }), 400
        
        # Get database connection (sync)
        from pymongo import MongoClient
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        mongo_uri = os.getenv("MONGO_DB") or os.getenv("MONGODB_URI")
        if not mongo_uri:
            return jsonify({
                'success': False,
                'error': 'MongoDB URI not configured'
            }), 500
        
        try:
            client = MongoClient(mongo_uri)
            db_name = os.getenv("DB_NAME") or os.getenv("DB", "contro-bot-db")
            db = client[db_name]
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to connect to database: {e}'
            }), 500
        
        # Find the giveaway
        from bson import ObjectId
        giveaway = db['giveaways'].find_one({'_id': ObjectId(giveaway_id)})
        
        if not giveaway:
            return jsonify({
                'success': False,
                'error': 'Giveaway not found'
            }), 404
        
        if giveaway.get('ended', False):
            return jsonify({
                'success': False,
                'error': 'Giveaway has already ended'
            }), 400
        
        # Remove user from participants
        db['giveaways'].update_one(
            {'_id': ObjectId(giveaway_id)},
            {'$pull': {'participants': {'user_id': user_id}}}
        )
        
        return jsonify({
            'success': True,
            'message': 'Successfully left the giveaway'
        })
        
    except Exception as e:
        logger.error(f"Error leaving giveaway: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to leave giveaway: {e}'
        }), 500


@giveaway_bp.route('/<giveaway_id>/reroll', methods=['POST'])
@require_auth
def reroll_giveaway(giveaway_id: str):
    """Reroll a giveaway to select new winners."""
    try:
        data = request.get_json()
        
        # Get database connection (sync)
        from pymongo import MongoClient
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        mongo_uri = os.getenv("MONGO_DB") or os.getenv("MONGODB_URI")
        if not mongo_uri:
            return jsonify({
                'success': False,
                'error': 'MongoDB URI not configured'
            }), 500
        
        try:
            client = MongoClient(mongo_uri)
            db_name = os.getenv("DB_NAME") or os.getenv("DB", "contro-bot-db")
            db = client[db_name]
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to connect to database: {e}'
            }), 500
        
        # Find the giveaway
        from bson import ObjectId
        giveaway = db['giveaways'].find_one({'_id': ObjectId(giveaway_id)})
        
        if not giveaway:
            return jsonify({
                'success': False,
                'error': 'Giveaway not found'
            }), 404
        
        if not giveaway.get('ended', False):
            return jsonify({
                'success': False,
                'error': 'Giveaway has not ended yet'
            }), 400
        
        # Get participants
        participants = giveaway.get('participants', [])
        
        # Select new winners
        winners = []
        winner_count = giveaway.get('winner_count', 1)
        
        if participants:
            # Shuffle participants and select winners
            shuffled = list(participants)
            random.shuffle(shuffled)
            winners = shuffled[:min(winner_count, len(shuffled))]
        
        # Update giveaway with new winners
        db['giveaways'].update_one(
            {'_id': ObjectId(giveaway_id)},
            {
                '$set': {
                    'winners': winners,
                    'rerolled_at': datetime.now()
                }
            }
        )
        
        return jsonify({
            'success': True,
            'data': {
                'giveaway_id': giveaway_id,
                'winners': winners,
                'participant_count': len(participants)
            }
        })
        
    except Exception as e:
        logger.error(f"Error rerolling giveaway: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to reroll giveaway: {e}'
        }), 500


@giveaway_bp.route('/<guild_id>/active', methods=['GET'])
def get_active_giveaways(guild_id: str):
    """Get active giveaways for a guild."""
    try:
        # Get database connection (sync)
        from pymongo import MongoClient
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        mongo_uri = os.getenv("MONGO_DB") or os.getenv("MONGODB_URI")
        if not mongo_uri:
            return jsonify({
                'success': False,
                'error': 'MongoDB URI not configured'
            }), 500
        
        try:
            client = MongoClient(mongo_uri)
            db_name = os.getenv("DB_NAME") or os.getenv("DB", "contro-bot-db")
            db = client[db_name]
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to connect to database: {e}'
            }), 500
        
        # Find active giveaways
        giveaways = list(db['giveaways'].find({
            'guild_id': guild_id,
            'ended': False
        }).limit(100))
        
        # Convert ObjectId to string for JSON serialization
        for giveaway in giveaways:
            giveaway['_id'] = str(giveaway['_id'])
            giveaway['created_at'] = giveaway['created_at'].isoformat()
            giveaway['updated_at'] = giveaway['updated_at'].isoformat()
        
        return jsonify({
            'success': True,
            'data': {
                'giveaways': giveaways,
                'count': len(giveaways)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting active giveaways: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to get active giveaways: {e}'
        }), 500


def create_giveaway_embed(giveaway_data: Dict[str, Any]):
    """Create Discord embed for giveaway."""
    import discord
    
    embed = discord.Embed(
        title=f"🎉 {giveaway_data['title']}",
        description=giveaway_data.get('description', ''),
        color=int(giveaway_data.get('embed_color', '#FF6B9D').replace('#', ''), 16)
    )
    
    embed.add_field(
        name="🏆 Prize",
        value=giveaway_data['prize'],
        inline=True
    )
    
    embed.add_field(
        name="👥 Participants",
        value=str(len(giveaway_data.get('participants', []))),
        inline=True
    )
    
    embed.add_field(
        name="🎯 Winners",
        value=str(giveaway_data.get('winner_count', 1)),
        inline=True
    )
    
    end_time = datetime.fromtimestamp(giveaway_data.get('end_time', 0))
    embed.add_field(
        name="⏰ Ends At",
        value=f"<t:{int(end_time.timestamp())}:F>",
        inline=False
    )
    
    embed.set_footer(text="Click the button below to participate!")
    
    return embed


def create_ended_giveaway_embed(giveaway_data: Dict[str, Any], winners: List[Dict[str, Any]]):
    """Create Discord embed for ended giveaway."""
    import discord
    
    embed = discord.Embed(
        title=f"🎉 {giveaway_data['title']} - ENDED",
        description="This giveaway has ended!",
        color=int(giveaway_data.get('embed_color', '#FF6B9D').replace('#', ''), 16)
    )
    
    embed.add_field(
        name="🏆 Prize",
        value=giveaway_data['prize'],
        inline=True
    )
    
    embed.add_field(
        name="👥 Total Participants",
        value=str(len(giveaway_data.get('participants', []))),
        inline=True
    )
    
    if winners:
        winner_mentions = [f"<@{winner['user_id']}>" for winner in winners]
        embed.add_field(
            name="🎊 Winners",
            value=", ".join(winner_mentions),
            inline=False
        )
    else:
        embed.add_field(
            name="🎊 Winners",
            value="No participants",
            inline=False
        )
    
    embed.set_footer(text="Giveaway ended")
    
    return embed


def create_giveaway_view():
    """Create Discord view for giveaway buttons."""
    import discord
    
    view = discord.ui.View(timeout=None)
    
    join_button = discord.ui.Button(
        label="Join Giveaway",
        style=discord.ButtonStyle.primary,
        custom_id="join_giveaway"
    )
    
    participants_button = discord.ui.Button(
        label="Participants",
        style=discord.ButtonStyle.secondary,
        custom_id="show_participants"
    )
    
    view.add_item(join_button)
    view.add_item(participants_button)
    
    return view 