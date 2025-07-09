"""
Rate limiting middleware for Flask API
"""

from flask import request, jsonify
from datetime import datetime, timedelta
from collections import defaultdict
import time

from ...core.config import get_config


# Simple in-memory rate limiter
_rate_limit_store = defaultdict(list)


def rate_limit_middleware():
    """Rate limiting middleware for API requests."""
    config = get_config()
    
    # Get client IP
    client_ip = request.remote_addr
    
    # Get current time
    now = time.time()
    
    # Clean old entries
    _rate_limit_store[client_ip] = [
        timestamp for timestamp in _rate_limit_store[client_ip]
        if now - timestamp < config.api.rate_limit_window
    ]
    
    # Check if limit exceeded
    if len(_rate_limit_store[client_ip]) >= config.api.rate_limit:
        return jsonify({
            'error': 'Rate limit exceeded',
            'retry_after': config.api.rate_limit_window
        }), 429
    
    # Add current request
    _rate_limit_store[client_ip].append(now)
    
    return None


def rate_limit(limit: int, window: int = 60):
    """Decorator for custom rate limiting."""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            now = time.time()
            
            # Clean old entries
            _rate_limit_store[client_ip] = [
                timestamp for timestamp in _rate_limit_store[client_ip]
                if now - timestamp < window
            ]
            
            # Check if limit exceeded
            if len(_rate_limit_store[client_ip]) >= limit:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': window
                }), 429
            
            # Add current request
            _rate_limit_store[client_ip].append(now)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Predefined rate limiters for common use cases
def rate_limit_strict(f):
    """Strict rate limiting: 10 requests per minute"""
    return rate_limit(limit=10, window=60)(f)

def rate_limit_moderate(f):
    """Moderate rate limiting: 100 requests per hour"""
    return rate_limit(limit=100, window=3600)(f)

def rate_limit_lenient(f):
    """Lenient rate limiting: 1000 requests per hour"""
    return rate_limit(limit=1000, window=3600)(f)

def rate_limit_api_key(f):
    """Rate limiting per API key: 500 requests per hour"""
    return rate_limit(limit=500, window=3600)(f) 