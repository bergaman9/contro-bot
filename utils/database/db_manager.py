"""
Centralized Database Manager for Contro Bot
Handles all MongoDB connections and provides a single source of truth
"""

import asyncio
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Singleton database manager for centralized connection handling"""
    
    _instance = None
    _client: Optional[AsyncIOMotorClient] = None
    _database: Optional[AsyncIOMotorDatabase] = None
    _sync_client: Optional[pymongo.MongoClient] = None
    _sync_database: Optional[pymongo.database.Database] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    async def initialize(self) -> AsyncIOMotorDatabase:
        """Initialize the async database connection"""
        if self._database is not None:
            return self._database
            
        try:
            mongo_uri = os.getenv("MONGO_DB")
            if not mongo_uri:
                logger.error("MONGO_DB environment variable not set")
                raise ValueError("MongoDB URI not configured")
            
            # Create async client with optimized settings
            self._client = AsyncIOMotorClient(
                mongo_uri,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=60000,
                maxPoolSize=100,
                minPoolSize=10,
                maxIdleTimeMS=180000,
                heartbeatFrequencyMS=120000,
                retryWrites=True,
                retryReads=True,
                w='majority'
            )
            
            # Test connection
            await self._client.admin.command('ping')
            
            # Get database
            db_name = os.getenv("DB", "contro-bot-db")
            self._database = self._client[db_name]
            
            logger.info(f"Successfully connected to MongoDB database: {db_name}")
            return self._database
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {e}")
            raise
    
    def get_sync_db(self) -> pymongo.database.Database:
        """Get synchronous database connection (for legacy code)"""
        if self._sync_database is not None:
            return self._sync_database
            
        try:
            mongo_uri = os.getenv("MONGO_DB")
            if not mongo_uri:
                raise ValueError("MongoDB URI not configured")
            
            # Create sync client
            self._sync_client = pymongo.MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=60000,
                maxPoolSize=100,
                minPoolSize=10
            )
            
            # Test connection
            self._sync_client.admin.command('ping')
            
            # Get database
            db_name = os.getenv("DB", "contro-bot-db")
            self._sync_database = self._sync_client[db_name]
            
            logger.info(f"Successfully connected to MongoDB (sync) database: {db_name}")
            return self._sync_database
            
        except Exception as e:
            logger.error(f"Failed to initialize sync MongoDB connection: {e}")
            raise
    
    async def get_database(self) -> AsyncIOMotorDatabase:
        """Get the async database connection, initializing if needed"""
        if self._database is None:
            await self.initialize()
        return self._database
    
    async def close(self):
        """Close all database connections"""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("Closed async MongoDB connection")
            
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
            self._sync_database = None
            logger.info("Closed sync MongoDB connection")
    
    def is_connected(self) -> bool:
        """Check if async database is connected"""
        return self._database is not None
    
    def is_sync_connected(self) -> bool:
        """Check if sync database is connected"""
        return self._sync_database is not None


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions for backward compatibility
async def get_async_db() -> AsyncIOMotorDatabase:
    """Get async database connection"""
    return await db_manager.get_database()


def get_sync_db() -> pymongo.database.Database:
    """Get sync database connection"""
    return db_manager.get_sync_db()


async def initialize_database() -> AsyncIOMotorDatabase:
    """Initialize and return database connection"""
    return await db_manager.initialize()


def is_database_connected() -> bool:
    """Check if database is connected"""
    return db_manager.is_connected() 