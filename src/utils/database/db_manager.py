"""
Centralized database manager for MongoDB connections
Provides a singleton pattern to ensure only one connection is used throughout the application
"""

import logging
from typing import Optional
import asyncio
import os
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.collection import AsyncCollection
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Singleton database manager for MongoDB connections using PyMongo async"""
    
    _instance = None
    _db: Optional[AsyncDatabase] = None
    _client: Optional[AsyncMongoClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    async def initialize(self, connection_string: str, database_name: str = "contro_bot") -> AsyncDatabase:
        """Initialize the async database connection"""
        if self._db is None:
            try:
                self._client = AsyncMongoClient(
                    connection_string,
                    serverSelectionTimeoutMS=30000,
                    connectTimeoutMS=30000,
                    socketTimeoutMS=60000,
                    tls=True,
                    retryWrites=True,
                    w='majority'
                )
                
                # Get database name from environment or use provided
                db_name = os.getenv("DB", database_name)
                self._db = self._client[db_name]
                
                # Test the connection
                await self._client.admin.command('ping')
                logger.info(f"Successfully connected to MongoDB database: {db_name}")
                
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise
        
        return self._db
    
    def get_database(self) -> Optional[AsyncDatabase]:
        """Get the async database instance"""
        if self._db is None:
            # Try to initialize from environment
            try:
                load_dotenv()
                
                mongo_uri = os.getenv("MONGO_DB") or os.getenv("MONGODB_URI")
                if not mongo_uri:
                    logger.error("MONGO_DB environment variable not set")
                    return None
                
                # Create async client
                self._client = AsyncMongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=30000,
                    connectTimeoutMS=30000,
                    socketTimeoutMS=60000,
                    tls=True,
                    retryWrites=True,
                    w='majority'
                )
                
                # Get database name from environment or use default
                db_name = os.getenv("DB", "contro-bot-db")
                self._db = self._client[db_name]
                
                # Note: We can't test connection here since this is sync method
                # Connection will be tested on first use
                logger.info(f"Async MongoDB client created for database: {db_name}")
                
            except Exception as e:
                logger.error(f"Failed to create async MongoDB client: {e}")
                return None
        
        return self._db
    
    def get_collection(self, collection_name: str) -> Optional[AsyncCollection]:
        """Get a specific collection from the database"""
        db = self.get_database()
        if db is not None:
            return db[collection_name]
        return None
    
    async def close(self):
        """Close the database connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Optional[AsyncDatabase]:
    """Convenience function to get database instance"""
    return db_manager.get_database()


def get_collection(collection_name: str) -> Optional[AsyncCollection]:
    """Convenience function to get a collection"""
    return db_manager.get_collection(collection_name) 