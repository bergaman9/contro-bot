"""Logging configuration and utilities."""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logger(
    name: Optional[str] = None,
    level: str = "INFO",
    log_dir: str = "logs",
    console_output: bool = True,
    file_output: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up a logger with both console and file handlers.
    
    Args:
        name: Logger name (defaults to root logger)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        console_output: Whether to output to console
        file_output: Whether to output to file
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file_output:
        # Create log directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename with date
        log_filename = f"{name or 'bot'}_{datetime.now().strftime('%Y-%m-%d')}.log"
        log_file = log_path / log_filename
        
        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # Error file handler (separate file for errors only)
        error_filename = f"{name or 'bot'}_errors_{datetime.now().strftime('%Y-%m-%d')}.log"
        error_file = log_path / error_filename
        
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter to add context to log messages."""
    
    def process(self, msg, kwargs):
        """Add context information to log messages."""
        # Add any context from extra dict
        if self.extra:
            context_parts = []
            for key, value in self.extra.items():
                context_parts.append(f"{key}={value}")
            context = " ".join(context_parts)
            return f"[{context}] {msg}", kwargs
        return msg, kwargs


def setup_discord_logger():
    """Set up Discord.py's logger to reduce noise."""
    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(logging.WARNING)
    
    discord_http_logger = logging.getLogger("discord.http")
    discord_http_logger.setLevel(logging.WARNING)
    
    discord_gateway_logger = logging.getLogger("discord.gateway")
    discord_gateway_logger.setLevel(logging.WARNING) 