"""
Commands API routes for Contro Discord Bot
Provides endpoints for command management and execution
"""

from flask import Blueprint, jsonify, request
from ...core.application import get_application_manager
from ...core.logger import get_logger

commands_bp = Blueprint('commands', __name__)
logger = get_logger("commands_api")


@commands_bp.route('/', methods=['GET'])
async def get_commands():
    """Get all available commands."""
    try:
        app_manager = await get_application_manager()
        bot = app_manager.get_bot()
        
        if not bot:
            return jsonify({'error': 'Bot not available'}), 503
        
        commands = []
        for command in bot.commands:
            commands.append({
                'name': command.name,
                'description': command.help or 'No description',
                'usage': command.usage or f'{command.name}',
                'aliases': command.aliases
            })
        
        return jsonify({
            'commands': commands,
            'total': len(commands)
        })
        
    except Exception as e:
        logger.error(f"Error getting commands: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@commands_bp.route('/<command_name>', methods=['GET'])
async def get_command(command_name):
    """Get specific command information."""
    try:
        app_manager = await get_application_manager()
        bot = app_manager.get_bot()
        
        if not bot:
            return jsonify({'error': 'Bot not available'}), 503
        
        command = bot.get_command(command_name)
        if not command:
            return jsonify({'error': 'Command not found'}), 404
        
        return jsonify({
            'name': command.name,
            'description': command.help or 'No description',
            'usage': command.usage or f'{command.name}',
            'aliases': command.aliases,
            'enabled': command.enabled,
            'hidden': command.hidden
        })
        
    except Exception as e:
        logger.error(f"Error getting command {command_name}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@commands_bp.route('/stats', methods=['GET'])
async def get_command_stats():
    """Get command usage statistics."""
    try:
        app_manager = await get_application_manager()
        db = app_manager.get_db_manager()
        
        if not db:
            return jsonify({'error': 'Database not available'}), 503
        
        # Get command stats from database
        collection = db.get_collection("command_stats")
        stats = await collection.find().to_list(length=100)
        
        return jsonify({
            'stats': stats,
            'total_commands': len(stats)
        })
        
    except Exception as e:
        logger.error(f"Error getting command stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500
