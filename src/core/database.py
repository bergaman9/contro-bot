"""
Database management for Contro Discord Bot
Provides MongoDB connection and management
"""

import asyncio
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ConnectionFailure, ServerSelectionTimeoutError
from bson import ObjectId
from .config import get_config
from .exceptions import DatabaseError, ConfigurationError
from .logger import get_logger, LoggerMixin


class DatabaseManager(LoggerMixin):
    """Database manager for MongoDB connections."""
    
    def __init__(self):
        self.config = get_config().database
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._connection_string: str = self.config.url
        self._database_name: str = self.config.database_name
        
    async def connect(self) -> bool:
        """Connect to MongoDB database."""
        try:
            self.logger.info(f"Connecting to MongoDB: {self._connection_string}")
            
            # Create client with optimized settings for Raspberry Pi
            self.client = AsyncIOMotorClient(
                self._connection_string,
                maxPoolSize=3,  # Reduced for Raspberry Pi
                minPoolSize=1,  # Reduced for Raspberry Pi
                serverSelectionTimeoutMS=30000,  # Increased for Raspberry Pi
                connectTimeoutMS=30000,  # Increased for Raspberry Pi
                socketTimeoutMS=60000,  # Increased for Raspberry Pi
                maxIdleTimeMS=45000,  # Reduced for Raspberry Pi
                retryWrites=True,
                retryReads=True,
                waitQueueTimeoutMS=15000,  # Increased for Raspberry Pi
                heartbeatFrequencyMS=10000,  # Added for Raspberry Pi
                maxConnecting=2  # Added for Raspberry Pi
            )
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Get database
            self.database = self.client[self._database_name]
            
            self.logger.info(f"Successfully connected to database: {self._database_name}")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to database: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from MongoDB database."""
        if self.client:
            self.client.close()
            self.client = None
            self.database = None
            self.logger.info("Disconnected from MongoDB")
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            if self.client is None:
                return False
            
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
    
    def get_collection(self, collection_name: str):
        """Get a collection from the database."""
        if self.database is None:
            raise RuntimeError("Database not connected")
        return self.database[collection_name]
    
    async def create_indexes(self) -> None:
        """Create necessary indexes for collections."""
        if self.database is None:
            self.logger.warning("Cannot create indexes: database not connected")
            return
        
        try:
            # Guild collection indexes
            guild_collection = self.get_collection("guilds")
            await guild_collection.create_index("guild_id", unique=True)
            await guild_collection.create_index("name")
            
            # User collection indexes
            user_collection = self.get_collection("users")
            await user_collection.create_index("user_id", unique=True)
            await user_collection.create_index("guild_id")
            
            # Game logs indexes
            game_logs_collection = self.get_collection("game_logs")
            await game_logs_collection.create_index("user_id")
            await game_logs_collection.create_index("guild_id")
            await game_logs_collection.create_index("timestamp")
            
            # Leveling indexes
            leveling_collection = self.get_collection("leveling")
            await leveling_collection.create_index([("user_id", 1), ("guild_id", 1)], unique=True)
            await leveling_collection.create_index("guild_id")
            
            # Levelling settings indexes
            levelling_settings_collection = self.get_collection("levelling_settings")
            await levelling_settings_collection.create_index("guild_id", unique=True)
            
            self.logger.info("Database indexes created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create indexes: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        if self.database is None:
            return {"error": "Database not connected"}
        
        try:
            stats = await self.database.command("dbStats")
            return {
                "database": self._database_name,
                "collections": stats.get("collections", 0),
                "data_size": stats.get("dataSize", 0),
                "storage_size": stats.get("storageSize", 0),
                "indexes": stats.get("indexes", 0),
                "index_size": stats.get("indexSize", 0)
            }
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


async def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.connect()
    return _db_manager


async def close_database() -> None:
    """Close the database connection."""
    global _db_manager
    if _db_manager:
        await _db_manager.disconnect()
        _db_manager = None


# Database utilities
def object_id_to_str(obj_id: Union[ObjectId, str]) -> str:
    """Convert ObjectId to string."""
    if isinstance(obj_id, ObjectId):
        return str(obj_id)
    return obj_id


def str_to_object_id(obj_id: Union[ObjectId, str]) -> ObjectId:
    """Convert string to ObjectId."""
    if isinstance(obj_id, str):
        return ObjectId(obj_id)
    return obj_id


def is_valid_object_id(obj_id: str) -> bool:
    """Check if a string is a valid ObjectId."""
    try:
        ObjectId(obj_id)
        return True
    except Exception:
        return False


_sync_client: Optional[MongoClient] = None
_sync_db: Optional[Any] = None

def get_sync_database_manager() -> Any:
    """Get the global sync database instance (pymongo)."""
    global _sync_client, _sync_db
    config = get_config().database
    if _sync_client is None or _sync_db is None:
        _sync_client = MongoClient(
            config.url,
            maxPoolSize=3,  # Reduced for Raspberry Pi
            minPoolSize=1,  # Reduced for Raspberry Pi
            serverSelectionTimeoutMS=30000,  # Increased for Raspberry Pi
            connectTimeoutMS=30000,  # Increased for Raspberry Pi
            socketTimeoutMS=60000,  # Increased for Raspberry Pi
            maxIdleTimeMS=45000,  # Reduced for Raspberry Pi
            retryWrites=True,
            retryReads=True,
            waitQueueTimeoutMS=15000,  # Increased for Raspberry Pi
            heartbeatFrequencyMS=10000,  # Added for Raspberry Pi
            maxConnecting=2  # Added for Raspberry Pi
        )
        _sync_db = _sync_client[config.database_name]
    return _sync_db

def close_sync_database() -> None:
    global _sync_client, _sync_db
    if _sync_client:
        _sync_client.close()
        _sync_client = None
        _sync_db = None 