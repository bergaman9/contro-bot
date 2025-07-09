"""Logging configuration for the Discord bot."""
import os
import logging
from logging.handlers import RotatingFileHandler
import traceback
from datetime import datetime
import sys

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure the main logger
logger = logging.getLogger('discord_bot')
logger.setLevel(logging.INFO)

# Current date for log file naming
current_date = datetime.now().strftime('%Y-%m-%d')
log_file = os.path.join(LOGS_DIR, f"bot_{current_date}.log")

# File handler with rotation (10 MB max size, keep 5 backup files)
file_handler = RotatingFileHandler(
    log_file, 
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Formatter for timestamps and log levels
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Make LOGS_DIR accessible to the logger instance
logger.LOGS_DIR = LOGS_DIR

def log_exception(exc_type, exc_value, exc_traceback):
    """Log uncaught exceptions to both console and file"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't log keyboard interrupts
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))

# Set the exception hook
sys.excepthook = log_exception

def setup_logging():
    """Setup additional logging configurations"""
    # Discord.py logger
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)
    discord_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, f"discord_{current_date}.log"),
        maxBytes=10*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    discord_handler.setFormatter(formatter)
    discord_logger.addHandler(discord_handler)
    discord_logger.addHandler(console_handler)

    return logger
