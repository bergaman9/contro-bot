"""
Flask API application for Contro Discord Bot
Provides REST API endpoints for dashboard and external integrations
"""

import asyncio
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import threading
from typing import Optional

from src.core.config import get_config
from src.core.logger import setup_logging, get_logger
from src.core.database import get_database_manager
from src.core.cache import get_cache_manager
from .middleware.auth import auth_middleware
from .middleware.rate_limit import rate_limit_middleware
from .routes.giveaway_api import giveaway_bp


def create_app() -> Flask:
    """Create and configure Flask application."""
    config = get_config()
    
    # Setup logging
    setup_logging()
    logger = get_logger("api")
    
    # Create Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.api.secret_key
    
    # Configure CORS
    CORS(app, origins=config.api.cors_origins)
    
    # Register middleware
    app.before_request(auth_middleware)
    app.before_request(rate_limit_middleware)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register routes
    from .routes import initialize_all_apis
    # Note: routes will be registered when bot is available
    app.register_blueprint(giveaway_bp, url_prefix="/api/giveaway")
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        try:
            return jsonify({
                'status': 'healthy',
                'service': 'contro-api',
                'version': '2.0.0',
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    logger.info("Flask application created successfully")
    return app


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the Flask app."""
    
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Handle HTTP exceptions."""
        response = {
            'error': {
                'code': error.code,
                'message': error.description,
                'type': 'HTTP_ERROR'
            }
        }
        return jsonify(response), error.code
    
    @app.errorhandler(Exception)
    def handle_generic_error(error):
        """Handle generic exceptions."""
        logger = get_logger("api")
        logger.error(f"Unhandled exception: {error}")
        
        response = {
            'error': {
                'code': 500,
                'message': 'Internal server error',
                'type': 'INTERNAL_ERROR'
            }
        }
        return jsonify(response), 500


async def initialize_services():
    """Initialize database and cache connections."""
    logger = get_logger("api")
    
    try:
        # Initialize database
        db_manager = await get_database_manager()
        await db_manager.create_indexes()
        logger.info("Database initialized successfully")
        
        # Initialize cache
        cache_manager = await get_cache_manager()
        logger.info("Cache initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


def run_api():
    """Run the API server."""
    config = get_config()
    logger = get_logger("api")
    
    if not config.api.enabled:
        logger.info("API is disabled in configuration")
        return
    
    try:
        # Initialize services
        asyncio.run(initialize_services())
        
        # Create and run Flask app
        app = create_app()
        
        logger.info(f"Starting API server on {config.api.host}:{config.api.port}")
        app.run(
            host=config.api.host,
            port=config.api.port,
            debug=config.debug,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        raise


# For direct execution
if __name__ == "__main__":
    run_api() 