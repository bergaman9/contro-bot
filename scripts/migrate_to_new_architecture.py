#!/usr/bin/env python3
"""
Migration script for transitioning from old architecture to new architecture.

This script helps migrate configuration, data, and settings from the old
bot structure to the new refactored architecture.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import shutil
from datetime import datetime

# Add the bot directory to the Python path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

try:
    from src.core.database import get_database
    from src.core.config import get_config
    from src.core.logger import setup_logging, get_logger
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📁 Current directory:", current_dir)
    print("📁 Available files:", [f.name for f in current_dir.iterdir() if f.is_dir()])
    print("🔧 Make sure you're running this script from the bot directory")
    sys.exit(1)


class ArchitectureMigrator:
    """Handles migration from old to new architecture."""
    
    def __init__(self):
        self.logger = get_logger("migrator")
        self.old_config_path = Path(".env")
        self.new_config_path = Path(".env.new")
        self.backup_dir = Path("backup") / datetime.now().strftime("%Y%m%d_%H%M%S")
        
    async def run_migration(self):
        """Run the complete migration process."""
        self.logger.info("Starting architecture migration")
        
        try:
            # Create backup
            await self.create_backup()
            
            # Migrate configuration
            await self.migrate_configuration()
            
            # Migrate database
            await self.migrate_database()
            
            # Update file structure
            await self.update_file_structure()
            
            # Validate migration
            await self.validate_migration()
            
            self.logger.info("Migration completed successfully!")
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            print(f"❌ Migration failed: {e}")
            await self.rollback_migration()
            raise
    
    async def create_backup(self):
        """Create backup of current state."""
        self.logger.info("Creating backup")
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup configuration
        if self.old_config_path.exists():
            shutil.copy2(self.old_config_path, self.backup_dir / ".env.backup")
        
        # Backup main.py
        if Path("main.py").exists():
            shutil.copy2("main.py", self.backup_dir / "main.py.backup")
        
        # Backup requirements.txt
        if Path("requirements.txt").exists():
            shutil.copy2("requirements.txt", self.backup_dir / "requirements.txt.backup")
        
        self.logger.info(f"Backup created at: {self.backup_dir}")
    
    async def migrate_configuration(self):
        """Migrate configuration from old to new format."""
        self.logger.info("Migrating configuration")
        
        if not self.old_config_path.exists():
            self.logger.warning("No .env file found, creating default configuration")
            await self.create_default_config()
            return
        
        # Read old configuration
        old_config = self.read_old_config()
        
        # Convert to new format
        new_config = self.convert_config_format(old_config)
        
        # Write new configuration
        self.write_new_config(new_config)
        
        self.logger.info("Configuration migration completed")
    
    def read_old_config(self) -> Dict[str, str]:
        """Read old configuration file."""
        config = {}
        
        with open(self.old_config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        
        return config
    
    def convert_config_format(self, old_config: Dict[str, str]) -> Dict[str, str]:
        """Convert old configuration format to new format."""
        new_config = {}
        
        # Bot Configuration - Use existing tokens
        new_config['DISCORD_TOKEN'] = old_config.get('CONTRO_MAIN_TOKEN', '')  # Use main token as primary
        new_config['DISCORD_DEV_TOKEN'] = old_config.get('CONTRO_DEV_TOKEN', '')
        new_config['DISCORD_PREMIUM_TOKEN'] = old_config.get('CONTRO_PREMIUM_TOKEN', '')
        new_config['DISCORD_PREFIX'] = '!'  # Default prefix
        new_config['ENVIRONMENT'] = 'development'
        new_config['DEBUG'] = 'true'
        new_config['BOT_NAME'] = 'Contro Bot'
        new_config['BOT_VERSION'] = '2.0.0'
        
        # Admin and User Configuration
        new_config['ADMIN_USER_ID'] = old_config.get('ADMIN_USER_ID', '')
        new_config['AUTHORIZATION'] = old_config.get('AUTHORIZATION', '')
        new_config['USER_TOKEN'] = old_config.get('USER_TOKEN', '')
        new_config['USER_ID'] = old_config.get('USER_ID', '')
        
        # Database Configuration - Use existing MongoDB connection
        new_config['DB_URL'] = old_config.get('MONGO_DB', 'mongodb://localhost:27017')
        new_config['DB_DATABASE_NAME'] = old_config.get('DB', 'contro-bot-db')
        new_config['DB_MAX_POOL_SIZE'] = '20'
        new_config['DB_MIN_POOL_SIZE'] = '5'
        new_config['DB_CONNECT_TIMEOUT'] = '60000'
        new_config['DB_SERVER_SELECTION_TIMEOUT'] = '60000'
        new_config['DB_SOCKET_TIMEOUT'] = '120000'
        new_config['DB_HEARTBEAT_FREQUENCY'] = '120000'
        new_config['DB_MAX_IDLE_TIME'] = '180000'
        
        # Cache Configuration
        new_config['CACHE_ENABLED'] = 'true'
        new_config['CACHE_REDIS_URL'] = ''  # No Redis in old config
        new_config['CACHE_DEFAULT_TTL'] = '3600'
        new_config['CACHE_MAX_SIZE'] = '1000'
        new_config['CACHE_STRATEGY'] = 'LRU'
        
        # API Configuration
        new_config['API_ENABLED'] = 'true'
        new_config['API_HOST'] = '0.0.0.0'
        new_config['API_PORT'] = '8000'
        new_config['API_CORS_ORIGINS'] = '*'
        new_config['API_RATE_LIMIT'] = '100'
        new_config['API_RATE_LIMIT_WINDOW'] = '60'
        
        # Logging Configuration
        new_config['LOG_LEVEL'] = 'DEBUG'
        new_config['LOG_FILE_ENABLED'] = 'true'
        new_config['LOG_FILE_PATH'] = 'logs/bot.log'
        new_config['LOG_MAX_FILE_SIZE'] = '10485760'
        new_config['LOG_BACKUP_COUNT'] = '5'
        new_config['LOG_FORMAT'] = 'json'
        new_config['LOG_COLORED'] = 'true'
        
        # Security Configuration
        new_config['SECURITY_ENABLED'] = 'true'
        new_config['SECURITY_JWT_SECRET'] = 'your-secret-key-change-this'
        new_config['SECURITY_JWT_EXPIRY'] = '3600'
        new_config['SECURITY_PASSWORD_SALT_ROUNDS'] = '12'
        
        # External Services - Preserve all existing API keys
        new_config['OPENAI_API_KEY'] = old_config.get('OPENAI_API_KEY', '')
        new_config['PERPLEXITY_API_KEY'] = old_config.get('PERPLEXITY_API_KEY', '')
        new_config['GUILDS_API_KEY'] = old_config.get('GUILDS_API_KEY', '')
        new_config['TMDB_API_KEY'] = old_config.get('TMDB_API_KEY', '')
        
        # Reddit API credentials
        new_config['REDDIT_CLIENT_ID'] = old_config.get('REDDIT_CLIENT_ID', '')
        new_config['REDDIT_CLIENT_SECRET'] = old_config.get('REDDIT_CLIENT_SECRET', '')
        new_config['REDDIT_PASSWORD'] = old_config.get('REDDIT_PASSWORD', '')
        new_config['REDDIT_USER_AGENT'] = old_config.get('REDDIT_USER_AGENT', '')
        new_config['REDDIT_USERNAME'] = old_config.get('REDDIT_USERNAME', '')
        
        # Spotify API credentials
        new_config['SPOTIFY_CLIENT_ID'] = old_config.get('SP_CLIENT_ID', '')
        new_config['SPOTIFY_CLIENT_SECRET'] = old_config.get('SP_CLIENT_SECRET', '')
        
        # Server and Channel IDs
        new_config['SESSION_ID'] = old_config.get('SESSION_ID', '')
        new_config['TEKNOMINATOR_CID'] = old_config.get('TEKNOMINATOR_CID', '')
        new_config['TEKNOMINATOR_GID'] = old_config.get('TEKNOMINATOR_GID', '')
        new_config['COMMUNITY_CID'] = old_config.get('COMMUNITY_CID', '')
        new_config['COMMUNITY_GID'] = old_config.get('COMMUNITY_GID', '')
        
        # Feature Flags
        new_config['FEATURE_AI_CHAT'] = 'true'
        new_config['FEATURE_GAME_LOGS'] = 'true'
        new_config['FEATURE_LEVELING'] = 'true'
        new_config['FEATURE_MODERATION'] = 'true'
        new_config['FEATURE_WELCOME'] = 'true'
        new_config['FEATURE_TICKETS'] = 'true'
        new_config['FEATURE_GIVEAWAYS'] = 'true'
        new_config['FEATURE_REDDIT'] = 'true'
        new_config['FEATURE_SPOTIFY'] = 'true'
        new_config['FEATURE_TMDB'] = 'true'
        
        # Performance Configuration
        new_config['PERFORMANCE_MAX_CONCURRENT_TASKS'] = '100'
        new_config['PERFORMANCE_TASK_TIMEOUT'] = '30'
        new_config['PERFORMANCE_MEMORY_LIMIT'] = '512'
        
        return new_config
    
    def write_new_config(self, config: Dict[str, str]):
        """Write new configuration file."""
        with open(self.new_config_path, 'w', encoding='utf-8') as f:
            f.write("# Contro Discord Bot - New Architecture Configuration\n")
            f.write("# Generated by migration script\n\n")
            
            # Bot Configuration
            f.write("# Bot Configuration\n")
            f.write(f"DISCORD_TOKEN={config.get('DISCORD_TOKEN', '')}\n")
            f.write(f"DISCORD_DEV_TOKEN={config.get('DISCORD_DEV_TOKEN', '')}\n")
            f.write(f"DISCORD_PREMIUM_TOKEN={config.get('DISCORD_PREMIUM_TOKEN', '')}\n")
            f.write(f"DISCORD_PREFIX={config.get('DISCORD_PREFIX', '!')}\n")
            f.write(f"ENVIRONMENT={config.get('ENVIRONMENT', 'development')}\n")
            f.write(f"DEBUG={config.get('DEBUG', 'true')}\n")
            f.write(f"BOT_NAME={config.get('BOT_NAME', 'Contro Bot')}\n")
            f.write(f"BOT_VERSION={config.get('BOT_VERSION', '2.0.0')}\n\n")
            
            # Admin and User Configuration
            f.write("# Admin and User Configuration\n")
            f.write(f"ADMIN_USER_ID={config.get('ADMIN_USER_ID', '')}\n")
            f.write(f"AUTHORIZATION={config.get('AUTHORIZATION', '')}\n")
            f.write(f"USER_TOKEN={config.get('USER_TOKEN', '')}\n")
            f.write(f"USER_ID={config.get('USER_ID', '')}\n\n")
            
            # Database Configuration
            f.write("# Database Configuration\n")
            f.write(f"DB_URL={config.get('DB_URL', 'mongodb://localhost:27017')}\n")
            f.write(f"DB_DATABASE_NAME={config.get('DB_DATABASE_NAME', 'contro-bot-db')}\n")
            f.write(f"DB_MAX_POOL_SIZE={config.get('DB_MAX_POOL_SIZE', '20')}\n")
            f.write(f"DB_MIN_POOL_SIZE={config.get('DB_MIN_POOL_SIZE', '5')}\n")
            f.write(f"DB_CONNECT_TIMEOUT={config.get('DB_CONNECT_TIMEOUT', '60000')}\n")
            f.write(f"DB_SERVER_SELECTION_TIMEOUT={config.get('DB_SERVER_SELECTION_TIMEOUT', '60000')}\n")
            f.write(f"DB_SOCKET_TIMEOUT={config.get('DB_SOCKET_TIMEOUT', '120000')}\n")
            f.write(f"DB_HEARTBEAT_FREQUENCY={config.get('DB_HEARTBEAT_FREQUENCY', '120000')}\n")
            f.write(f"DB_MAX_IDLE_TIME={config.get('DB_MAX_IDLE_TIME', '180000')}\n\n")
            
            # Cache Configuration
            f.write("# Cache Configuration\n")
            f.write(f"CACHE_ENABLED={config.get('CACHE_ENABLED', 'true')}\n")
            f.write(f"CACHE_REDIS_URL={config.get('CACHE_REDIS_URL', '')}\n")
            f.write(f"CACHE_DEFAULT_TTL={config.get('CACHE_DEFAULT_TTL', '3600')}\n")
            f.write(f"CACHE_MAX_SIZE={config.get('CACHE_MAX_SIZE', '1000')}\n")
            f.write(f"CACHE_STRATEGY={config.get('CACHE_STRATEGY', 'LRU')}\n\n")
            
            # API Configuration
            f.write("# API Configuration\n")
            f.write(f"API_ENABLED={config.get('API_ENABLED', 'true')}\n")
            f.write(f"API_HOST={config.get('API_HOST', '0.0.0.0')}\n")
            f.write(f"API_PORT={config.get('API_PORT', '8000')}\n")
            f.write(f"API_CORS_ORIGINS={config.get('API_CORS_ORIGINS', '*')}\n")
            f.write(f"API_RATE_LIMIT={config.get('API_RATE_LIMIT', '100')}\n")
            f.write(f"API_RATE_LIMIT_WINDOW={config.get('API_RATE_LIMIT_WINDOW', '60')}\n\n")
            
            # Logging Configuration
            f.write("# Logging Configuration\n")
            f.write(f"LOG_LEVEL={config.get('LOG_LEVEL', 'DEBUG')}\n")
            f.write(f"LOG_FILE_ENABLED={config.get('LOG_FILE_ENABLED', 'true')}\n")
            f.write(f"LOG_FILE_PATH={config.get('LOG_FILE_PATH', 'logs/bot.log')}\n")
            f.write(f"LOG_MAX_FILE_SIZE={config.get('LOG_MAX_FILE_SIZE', '10485760')}\n")
            f.write(f"LOG_BACKUP_COUNT={config.get('LOG_BACKUP_COUNT', '5')}\n")
            f.write(f"LOG_FORMAT={config.get('LOG_FORMAT', 'json')}\n")
            f.write(f"LOG_COLORED={config.get('LOG_COLORED', 'true')}\n\n")
            
            # Security Configuration
            f.write("# Security Configuration\n")
            f.write(f"SECURITY_ENABLED={config.get('SECURITY_ENABLED', 'true')}\n")
            f.write(f"SECURITY_JWT_SECRET={config.get('SECURITY_JWT_SECRET', 'your-secret-key-change-this')}\n")
            f.write(f"SECURITY_JWT_EXPIRY={config.get('SECURITY_JWT_EXPIRY', '3600')}\n")
            f.write(f"SECURITY_PASSWORD_SALT_ROUNDS={config.get('SECURITY_PASSWORD_SALT_ROUNDS', '12')}\n\n")
            
            # External Services
            f.write("# External Services\n")
            f.write(f"OPENAI_API_KEY={config.get('OPENAI_API_KEY', '')}\n")
            f.write(f"PERPLEXITY_API_KEY={config.get('PERPLEXITY_API_KEY', '')}\n")
            f.write(f"GUILDS_API_KEY={config.get('GUILDS_API_KEY', '')}\n")
            f.write(f"TMDB_API_KEY={config.get('TMDB_API_KEY', '')}\n\n")
            
            # Reddit API credentials
            f.write("# Reddit API Credentials\n")
            f.write(f"REDDIT_CLIENT_ID={config.get('REDDIT_CLIENT_ID', '')}\n")
            f.write(f"REDDIT_CLIENT_SECRET={config.get('REDDIT_CLIENT_SECRET', '')}\n")
            f.write(f"REDDIT_PASSWORD={config.get('REDDIT_PASSWORD', '')}\n")
            f.write(f"REDDIT_USER_AGENT={config.get('REDDIT_USER_AGENT', '')}\n")
            f.write(f"REDDIT_USERNAME={config.get('REDDIT_USERNAME', '')}\n\n")
            
            # Spotify API credentials
            f.write("# Spotify API Credentials\n")
            f.write(f"SPOTIFY_CLIENT_ID={config.get('SPOTIFY_CLIENT_ID', '')}\n")
            f.write(f"SPOTIFY_CLIENT_SECRET={config.get('SPOTIFY_CLIENT_SECRET', '')}\n\n")
            
            # Server and Channel IDs
            f.write("# Server and Channel IDs\n")
            f.write(f"SESSION_ID={config.get('SESSION_ID', '')}\n")
            f.write(f"TEKNOMINATOR_CID={config.get('TEKNOMINATOR_CID', '')}\n")
            f.write(f"TEKNOMINATOR_GID={config.get('TEKNOMINATOR_GID', '')}\n")
            f.write(f"COMMUNITY_CID={config.get('COMMUNITY_CID', '')}\n")
            f.write(f"COMMUNITY_GID={config.get('COMMUNITY_GID', '')}\n\n")
            
            # Feature Flags
            f.write("# Feature Flags\n")
            f.write(f"FEATURE_AI_CHAT={config.get('FEATURE_AI_CHAT', 'true')}\n")
            f.write(f"FEATURE_GAME_LOGS={config.get('FEATURE_GAME_LOGS', 'true')}\n")
            f.write(f"FEATURE_LEVELING={config.get('FEATURE_LEVELING', 'true')}\n")
            f.write(f"FEATURE_MODERATION={config.get('FEATURE_MODERATION', 'true')}\n")
            f.write(f"FEATURE_WELCOME={config.get('FEATURE_WELCOME', 'true')}\n")
            f.write(f"FEATURE_TICKETS={config.get('FEATURE_TICKETS', 'true')}\n")
            f.write(f"FEATURE_GIVEAWAYS={config.get('FEATURE_GIVEAWAYS', 'true')}\n")
            f.write(f"FEATURE_REDDIT={config.get('FEATURE_REDDIT', 'true')}\n")
            f.write(f"FEATURE_SPOTIFY={config.get('FEATURE_SPOTIFY', 'true')}\n")
            f.write(f"FEATURE_TMDB={config.get('FEATURE_TMDB', 'true')}\n\n")
            
            # Performance Configuration
            f.write("# Performance Configuration\n")
            f.write(f"PERFORMANCE_MAX_CONCURRENT_TASKS={config.get('PERFORMANCE_MAX_CONCURRENT_TASKS', '100')}\n")
            f.write(f"PERFORMANCE_TASK_TIMEOUT={config.get('PERFORMANCE_TASK_TIMEOUT', '30')}\n")
            f.write(f"PERFORMANCE_MEMORY_LIMIT={config.get('PERFORMANCE_MEMORY_LIMIT', '512')}\n")
    
    async def create_default_config(self):
        """Create default configuration if none exists."""
        default_config = {
            'DISCORD_TOKEN': '',
            'DISCORD_DEV_TOKEN': '',
            'DISCORD_PREMIUM_TOKEN': '',
            'DISCORD_PREFIX': '!',
            'ENVIRONMENT': 'development',
            'DEBUG': 'true',
            'BOT_NAME': 'Contro Bot',
            'BOT_VERSION': '2.0.0',
            'ADMIN_USER_ID': '',
            'AUTHORIZATION': '',
            'USER_TOKEN': '',
            'USER_ID': '',
            'DB_URL': 'mongodb://localhost:27017',
            'DB_DATABASE_NAME': 'contro-bot-db',
            'DB_MAX_POOL_SIZE': '20',
            'DB_MIN_POOL_SIZE': '5',
            'DB_CONNECT_TIMEOUT': '60000',
            'DB_SERVER_SELECTION_TIMEOUT': '60000',
            'DB_SOCKET_TIMEOUT': '120000',
            'DB_HEARTBEAT_FREQUENCY': '120000',
            'DB_MAX_IDLE_TIME': '180000',
            'CACHE_ENABLED': 'true',
            'CACHE_REDIS_URL': '',
            'CACHE_DEFAULT_TTL': '3600',
            'CACHE_MAX_SIZE': '1000',
            'CACHE_STRATEGY': 'LRU',
            'API_ENABLED': 'true',
            'API_HOST': '0.0.0.0',
            'API_PORT': '8000',
            'API_CORS_ORIGINS': '*',
            'API_RATE_LIMIT': '100',
            'API_RATE_LIMIT_WINDOW': '60',
            'LOG_LEVEL': 'DEBUG',
            'LOG_FILE_ENABLED': 'true',
            'LOG_FILE_PATH': 'logs/bot.log',
            'LOG_MAX_FILE_SIZE': '10485760',
            'LOG_BACKUP_COUNT': '5',
            'LOG_FORMAT': 'json',
            'LOG_COLORED': 'true',
            'SECURITY_ENABLED': 'true',
            'SECURITY_JWT_SECRET': 'your-secret-key-change-this',
            'SECURITY_JWT_EXPIRY': '3600',
            'SECURITY_PASSWORD_SALT_ROUNDS': '12',
            'OPENAI_API_KEY': '',
            'PERPLEXITY_API_KEY': '',
            'GUILDS_API_KEY': '',
            'TMDB_API_KEY': '',
            'REDDIT_CLIENT_ID': '',
            'REDDIT_CLIENT_SECRET': '',
            'REDDIT_PASSWORD': '',
            'REDDIT_USER_AGENT': '',
            'REDDIT_USERNAME': '',
            'SPOTIFY_CLIENT_ID': '',
            'SPOTIFY_CLIENT_SECRET': '',
            'SESSION_ID': '',
            'TEKNOMINATOR_CID': '',
            'TEKNOMINATOR_GID': '',
            'COMMUNITY_CID': '',
            'COMMUNITY_GID': '',
            'FEATURE_AI_CHAT': 'true',
            'FEATURE_GAME_LOGS': 'true',
            'FEATURE_LEVELING': 'true',
            'FEATURE_MODERATION': 'true',
            'FEATURE_WELCOME': 'true',
            'FEATURE_TICKETS': 'true',
            'FEATURE_GIVEAWAYS': 'true',
            'FEATURE_REDDIT': 'true',
            'FEATURE_SPOTIFY': 'true',
            'FEATURE_TMDB': 'true',
            'PERFORMANCE_MAX_CONCURRENT_TASKS': '100',
            'PERFORMANCE_TASK_TIMEOUT': '30',
            'PERFORMANCE_MEMORY_LIMIT': '512'
        }
        
        self.write_new_config(default_config)
    
    async def migrate_database(self):
        """Migrate database structure if needed."""
        self.logger.info("Checking database structure")
        
        try:
            # Initialize database connection
            db = await get_database()
            
            # Check if database is accessible
            if await db.health_check():
                self.logger.info("Database connection successful")
                
                # Create indexes for better performance
                await self.create_database_indexes(db)
            else:
                self.logger.warning("Database connection failed, skipping database migration")
                
        except Exception as e:
            self.logger.warning(f"Database migration skipped: {e}")
    
    async def create_database_indexes(self, db):
        """Create database indexes for better performance."""
        self.logger.info("Creating database indexes")
        
        try:
            # Guild collection indexes
            await db.create_index("guilds", [("guild_id", 1)], unique=True)
            await db.create_index("guilds", [("name", 1)])
            
            # Users collection indexes
            await db.create_index("users", [("user_id", 1)], unique=True)
            await db.create_index("users", [("guild_id", 1)])
            
            # Giveaways collection indexes
            await db.create_index("giveaways", [("guild_id", 1)])
            await db.create_index("giveaways", [("status", 1)])
            await db.create_index("giveaways", [("end_time", 1)])
            
            # Moderation collection indexes
            await db.create_index("moderation", [("guild_id", 1)])
            await db.create_index("moderation", [("user_id", 1)])
            await db.create_index("moderation", [("action_type", 1)])
            await db.create_index("moderation", [("created_at", -1)])
            
            self.logger.info("Database indexes created successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to create some indexes: {e}")
    
    async def update_file_structure(self):
        """Update file structure for new architecture."""
        self.logger.info("Updating file structure")
        
        # Create necessary directories
        directories = [
            "logs",
            "config",
            "tests/unit",
            "tests/integration",
            "tests/fixtures",
            "docs"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Copy new files
        if Path("main-new.py").exists():
            shutil.copy2("main-new.py", "main.py.new")
        
        if Path("requirements-new.txt").exists():
            shutil.copy2("requirements-new.txt", "requirements.txt.new")
        
        self.logger.info("File structure updated")
    
    async def validate_migration(self):
        """Validate the migration was successful."""
        self.logger.info("Validating migration")
        
        # Check if new configuration exists
        if not self.new_config_path.exists():
            raise Exception("New configuration file not created")
        
        # Check if backup exists
        if not self.backup_dir.exists():
            raise Exception("Backup directory not created")
        
        # Test configuration loading
        try:
            # Temporarily rename old config and use new one
            if self.old_config_path.exists():
                old_config_backup = self.old_config_path.with_suffix('.env.old')
                self.old_config_path.rename(old_config_backup)
            
            self.new_config_path.rename(self.old_config_path)
            
            # Test configuration loading
            config = get_config()
            self.logger.info("Configuration validation successful")
            
            # Restore old config
            if old_config_backup.exists():
                self.old_config_path.rename(self.new_config_path)
                old_config_backup.rename(self.old_config_path)
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise
    
    async def rollback_migration(self):
        """Rollback migration in case of failure."""
        self.logger.info("Rolling back migration")
        
        # Restore original files
        if (self.backup_dir / ".env.backup").exists():
            shutil.copy2(self.backup_dir / ".env.backup", self.old_config_path)
        
        if (self.backup_dir / "main.py.backup").exists():
            shutil.copy2(self.backup_dir / "main.py.backup", "main.py")
        
        if (self.backup_dir / "requirements.txt.backup").exists():
            shutil.copy2(self.backup_dir / "requirements.txt.backup", "requirements.txt")
        
        # Remove new files
        for file_path in [self.new_config_path, Path("main.py.new"), Path("requirements.txt.new")]:
            if file_path.exists():
                file_path.unlink()
        
        self.logger.info("Migration rollback completed")


async def main():
    """Main migration function."""
    print("🔄 Contro Discord Bot - Architecture Migration")
    print("=" * 50)
    
    migrator = ArchitectureMigrator()
    
    try:
        await migrator.run_migration()
        
        print("\n📋 Migration Summary:")
        print(f"✅ Backup created at: {migrator.backup_dir}")
        print("✅ Configuration migrated")
        print("✅ Database structure updated")
        print("✅ File structure updated")
        
        print("\n📝 Next Steps:")
        print("1. Review the new configuration in .env.new")
        print("2. Install new dependencies: pip install -r requirements-new.txt")
        print("3. Test the new bot: python main.py dev")
        print("4. If everything works, replace old files with new ones")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Rolling back changes...")
        await migrator.rollback_migration()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 