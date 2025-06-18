"""Flask application factory."""

from flask import Flask, jsonify
from flask_cors import CORS
import logging
from typing import Optional

from .routes import commands, guilds, health, stats
from .middleware.auth import auth_middleware
from .middleware.rate_limit import rate_limit_middleware
from ..utils.common.logger import setup_logger


def create_app(config_name: str = "development") -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(f"config.{config_name}")
    
    # Set up CORS
    CORS(app, origins=app.config.get("CORS_ORIGINS", ["*"]))
    
    # Set up logging
    logger = setup_logger(
        name="contro.api",
        level=app.config.get("LOG_LEVEL", "INFO")
    )
    app.logger = logger
    
    # Register middleware
    app.before_request(auth_middleware)
    app.before_request(rate_limit_middleware)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register blueprints
    app.register_blueprint(health.bp, url_prefix="/health")
    app.register_blueprint(commands.bp, url_prefix="/api/commands")
    app.register_blueprint(guilds.bp, url_prefix="/api/guilds")
    app.register_blueprint(stats.bp, url_prefix="/api/stats")
    
    # Root route
    @app.route("/")
    def index():
        return jsonify({
            "name": "Contro Bot API",
            "version": "2.0.0",
            "status": "online"
        })
    
    return app


def register_error_handlers(app: Flask):
    """Register error handlers for the application."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "error": "Bad Request",
            "message": str(error)
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "error": "Unauthorized",
            "message": "Authentication required"
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "error": "Forbidden",
            "message": "You don't have permission to access this resource"
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found"
        }), 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Please try again later."
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal error: {error}")
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }), 500 