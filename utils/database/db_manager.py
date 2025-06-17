"""
Centralized database manager for MongoDB connections
Provides a singleton pattern to ensure only one connection is used throughout the application
"""

import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Singleton database manager for MongoDB connections"""
    
    _instance = None
    _db = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def initialize(self, connection_string: str, database_name: str = "contro_bot") -> Database:
        """Initialize the database connection"""
        if self._db is None:
            try:
                self._client = MongoClient(connection_string)
                self._db = self._client[database_name]
                
                # Test the connection
                self._client.server_info()
                logger.info(f"Successfully connected to MongoDB database: {database_name}")
                
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise
        
        return self._db
    
    def get_database(self) -> Optional[Database]:
        """Get the database instance"""
        if self._db is None:
            # Try to initialize from environment
            try:
                import os
                from dotenv import load_dotenv
                load_dotenv()
                
                mongo_uri = os.getenv("MONGO_DB")
                if not mongo_uri:
                    logger.error("MONGO_DB environment variable not set")
                    return None
                
                # Initialize with proper parameters for MongoDB Atlas
                self._client = MongoClient(
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
                
                # Test the connection
                self._client.server_info()
                logger.info(f"Successfully connected to MongoDB database: {db_name}")
                
            except Exception as e:
                logger.error(f"Failed to auto-initialize database: {e}")
                return None
        
        return self._db
    
    def get_collection(self, collection_name: str):
        """Get a specific collection from the database"""
        db = self.get_database()
        if db is not None:
            return db[collection_name]
        return None
    
    def close(self):
        """Close the database connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Optional[Database]:
    """Convenience function to get database instance"""
    return db_manager.get_database()


def get_collection(collection_name: str):
    """Convenience function to get a collection"""
    return db_manager.get_collection(collection_name) 