"""
Rate limiting middleware for API endpoints
"""

import time
from functools import wraps
from flask import request, jsonify, g
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.clients = defaultdict(lambda: deque())
        self.cleanup_interval = 60  # Clean up old entries every 60 seconds
        self.last_cleanup = time.time()
    
    def is_allowed(self, identifier: str, limit: int, window: int) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limit
        
        Args:
            identifier: Client identifier (IP, API key, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        now = time.time()
        
        # Cleanup old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup(now)
            self.last_cleanup = now
        
        # Get client's request history
        requests = self.clients[identifier]
        
        # Remove old requests outside the window
        while requests and requests[0] <= now - window:
            requests.popleft()
        
        # Check if limit is exceeded
        current_count = len(requests)
        
        if current_count >= limit:
            # Calculate when the oldest request will expire
            reset_time = int(requests[0] + window) if requests else int(now + window)
            remaining = 0
        else:
            # Add current request
            requests.append(now)
            remaining = limit - current_count - 1
            reset_time = int(now + window)
        
        rate_limit_info = {
            'limit': limit,
            'remaining': remaining,
            'reset': reset_time,
            'window': window
        }
        
        return current_count < limit, rate_limit_info
    
    def _cleanup(self, now: float):
        """Remove old entries to prevent memory leaks"""
        for identifier in list(self.clients.keys()):
            requests = self.clients[identifier]
            # Remove requests older than 1 hour
            while requests and requests[0] <= now - 3600:
                requests.popleft()
            
            # Remove empty deques
            if not requests:
                del self.clients[identifier]

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(limit: int = 100, window: int = 3600, per: str = 'ip'):
    """
    Rate limiting decorator
    
    Args:
        limit: Maximum requests allowed
        window: Time window in seconds (default: 1 hour)
        per: Rate limit per 'ip', 'api_key', or 'user'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Determine identifier based on 'per' parameter
            if per == 'ip':
                identifier = request.remote_addr or 'unknown'
            elif per == 'api_key':
                api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '')
                if api_key.startswith('Bearer '):
                    api_key = api_key[7:]
                identifier = f"api_key:{api_key[:10]}" if api_key else f"ip:{request.remote_addr}"
            elif per == 'user':
                # Extract user from token (requires auth middleware to run first)
                user_id = getattr(g, 'user_id', None) or request.remote_addr
                identifier = f"user:{user_id}"
            else:
                identifier = request.remote_addr or 'unknown'
            
            # Check rate limit
            is_allowed, rate_info = rate_limiter.is_allowed(identifier, limit, window)
            
            if not is_allowed:
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {limit} per {window} seconds',
                    'retry_after': rate_info['reset'] - int(time.time())
                })
                
                # Add rate limit headers
                response.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
                response.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                response.headers['X-RateLimit-Reset'] = str(rate_info['reset'])
                response.headers['Retry-After'] = str(rate_info['reset'] - int(time.time()))
                
                return response, 429
            
            # Add rate limit headers to successful responses
            response = f(*args, **kwargs)
            
            # Handle both response objects and tuples
            if isinstance(response, tuple):
                response_obj, status_code = response
                if hasattr(response_obj, 'headers'):
                    response_obj.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
                    response_obj.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                    response_obj.headers['X-RateLimit-Reset'] = str(rate_info['reset'])
                return response_obj, status_code
            else:
                if hasattr(response, 'headers'):
                    response.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
                    response.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                    response.headers['X-RateLimit-Reset'] = str(rate_info['reset'])
                return response
        
        return decorated_function
    return decorator

# Predefined rate limiters for common use cases
def rate_limit_strict(f):
    """Strict rate limiting: 10 requests per minute"""
    return rate_limit(limit=10, window=60, per='ip')(f)

def rate_limit_moderate(f):
    """Moderate rate limiting: 100 requests per hour"""
    return rate_limit(limit=100, window=3600, per='ip')(f)

def rate_limit_lenient(f):
    """Lenient rate limiting: 1000 requests per hour"""
    return rate_limit(limit=1000, window=3600, per='ip')(f)

def rate_limit_api_key(f):
    """Rate limiting per API key: 500 requests per hour"""
    return rate_limit(limit=500, window=3600, per='api_key')(f) 