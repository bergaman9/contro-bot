"""
Authentication middleware for API endpoints
"""

from functools import wraps
from flask import request, jsonify, current_app
import os
import logging

logger = logging.getLogger(__name__)

def require_auth(f):
    """Decorator to require authentication for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get API key from headers
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')
        
        if not api_key:
            return jsonify({
                'error': 'Missing API key',
                'message': 'Please provide X-API-Key header'
            }), 401
        
        # Remove 'Bearer ' prefix if present
        if api_key.startswith('Bearer '):
            api_key = api_key[7:]
        
        # Check against configured API keys
        valid_keys = [
            os.getenv('GUILDS_API_KEY'),
            os.getenv('ADMIN_API_KEY'),
            os.getenv('AUTHORIZATION')
        ]
        
        # Filter out None values
        valid_keys = [key for key in valid_keys if key]
        
        if not valid_keys:
            logger.warning("No API keys configured for authentication")
            return jsonify({
                'error': 'Server misconfiguration',
                'message': 'Authentication not properly configured'
            }), 500
        
        if api_key not in valid_keys:
            logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check authentication
        auth_result = require_auth(lambda: None)()
        if auth_result:  # If auth failed, return the error
            return auth_result
        
        # Additional admin checks can be added here
        admin_key = os.getenv('AUTHORIZATION')
        provided_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')
        
        if provided_key and provided_key.startswith('Bearer '):
            provided_key = provided_key[7:]
        
        if provided_key != admin_key:
            return jsonify({
                'error': 'Admin access required',
                'message': 'This endpoint requires administrator privileges'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_user_from_token(token: str) -> dict:
    """Extract user information from token"""
    # This is a simple implementation
    # In production, you might want to use JWT or other token formats
    
    admin_id = os.getenv('ADMIN_USER_ID')
    admin_token = os.getenv('AUTHORIZATION')
    
    if token == admin_token and admin_id:
        return {
            'user_id': admin_id,
            'is_admin': True,
            'permissions': ['read', 'write', 'admin']
        }
    
    # For guild API keys, return limited permissions
    if token == os.getenv('GUILDS_API_KEY'):
        return {
            'user_id': 'api_user',
            'is_admin': False,
            'permissions': ['read']
        }
    
    return {
        'user_id': 'anonymous',
        'is_admin': False,
        'permissions': []
    } 