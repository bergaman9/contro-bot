"""
Authentication middleware for Flask API
"""

from flask import request, jsonify
from functools import wraps
import jwt
from datetime import datetime, timedelta

from ...core.config import get_config


def auth_middleware():
    """Authentication middleware for API requests."""
    # Skip auth for health check and public endpoints
    public_endpoints = [
        'health_check', 
        'static',
        'ping',
        'index'
    ]
    
    # Skip auth for public endpoints
    if request.endpoint in public_endpoints:
        return None
    
    # Skip auth for giveaway public endpoints
    if request.path.startswith('/api/giveaway/') and request.method in ['POST', 'GET']:
        giveaway_public_endpoints = ['join', 'leave', 'active']
        for endpoint in giveaway_public_endpoints:
            if endpoint in request.path:
                return None
    
    # Get token from header
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'No authorization header'}), 401
    
    try:
        # Extract token from "Bearer <token>"
        token = auth_header.split(' ')[1]
        
        # Verify token
        config = get_config()
        payload = jwt.decode(token, config.security.jwt_secret, algorithms=['HS256'])
        
        # Add user info to request
        request.user = payload
        
    except (IndexError, jwt.InvalidTokenError) as e:
        print(f"JWT decode error: {e}")
        print(f"Token: {token}")
        print(f"Secret: {config.security.jwt_secret}")
        return jsonify({'error': 'Invalid token'}), 401
    
    return None


def require_auth(f):
    """Decorator to require authentication for endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authentication required'}), 401
        
        try:
            token = auth_header.split(' ')[1]
            config = get_config()
            payload = jwt.decode(token, config.security.jwt_secret, algorithms=['HS256'])
            request.user = payload
        except (IndexError, jwt.InvalidTokenError) as e:
            print(f"JWT decode error: {e}")
            print(f"Token: {token}")
            print(f"Secret: {config.security.jwt_secret}")
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def generate_token(user_id: str, expires_in: int = 3600) -> str:
    """Generate JWT token for user."""
    config = get_config()
    
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow()
    }
    
    return jwt.encode(payload, config.security.jwt_secret, algorithm='HS256') 