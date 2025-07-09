#!/usr/bin/env python3
"""
Contro Discord Bot - Modern Main Entry Point with Application Manager

This is the new, refactored main entry point that uses a central application manager
to start both the Discord bot and the API server in a clean, organized manner.

Usage:
    python main.py dev          # Development mode
    python main.py prod         # Production mode
    python main.py api-only     # Start only API server
    python main.py bot-only     # Start only Discord bot
"""

import os
import sys
import asyncio
import argparse
import signal
from pathlib import Path
from typing import Optional
import logging

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

# Import application manager
from src.core.application import initialize_application, shutdown_application

logging.getLogger('pymongo').setLevel(logging.WARNING)

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Contro Discord Bot")
    parser.add_argument("mode", 
                       choices=["dev", "prod", "api-only", "bot-only"],
                       help="Mode to run the application in")
    
    args = parser.parse_args()
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        asyncio.create_task(shutdown_application())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize application
        app_manager = await initialize_application(args.mode)
        
        # Start services based on mode
        start_bot = args.mode not in ['api-only']
        start_api = args.mode not in ['bot-only']
        
        await app_manager.start_services(start_bot=start_bot, start_api=start_api)
        
    except Exception as e:
        print(f"Application error: {e}")
        await shutdown_application()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 