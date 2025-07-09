"""Database utilities for MongoDB Atlas with async and sync operations using pymongo."""
import os
import logging
from typing import Optional, Dict, List, Any, Union
import dotenv
import asyncio
import time
from ..core.logger import logger
import certifi

# MongoDB imports
import pymongo
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# Ensure environment variables are loaded
dotenv.load_dotenv()

# Set up logging
logger = logging.getLogger('database')

# Disable pymongo debug logs
logging.getLogger('pymongo').setLevel(logging.WARNING)
logging.getLogger('pymongo.connection').setLevel(logging.WARNING)
logging.getLogger('pymongo.topology').setLevel(logging.WARNING)
logging.getLogger('pymongo.serverSelection').setLevel(logging.WARNING)
logging.getLogger('pymongo.command').setLevel(logging.WARNING)

# MongoDB Atlas Configuration
MONGO_URI = os.getenv('DB_URL') or os.getenv('MONGO_DB') or os.getenv('MONGODB_URI')
DB_NAME = os.getenv('DB_DATABASE_NAME') or os.getenv('DB', 'contro')

if not MONGO_URI:
    logger.warning("MongoDB URI not found in environment variables!")
    MONGO_URI = "mongodb://localhost:27017/"

# Global client instances
sync_client = None
sync_db = None
async_client = None
async_db = None

def initialize_sync_mongodb():
    """Initialize synchronous MongoDB connection"""
    global sync_client, sync_db
    
    try:
        if "+srv" in MONGO_URI:
            logger.info("Connecting to MongoDB Atlas with SRV connection")
            sync_client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                maxIdleTimeMS=60000,
                retryWrites=True,
                maxPoolSize=5,
                waitQueueTimeoutMS=10000,
                retryReads=True,
                tls=True,
                tlsAllowInvalidCertificates=True,
                tlsCAFile=certifi.where()
            )
        else:
            logger.info("Connecting to local MongoDB")
            sync_client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                maxIdleTimeMS=60000,
                retryWrites=True,
                maxPoolSize=5,
                waitQueueTimeoutMS=10000,
                retryReads=True
            )
        
        # Test connection
        sync_client.admin.command('ping')
        sync_db = sync_client[DB_NAME]
        logger.info(f"Sync MongoDB connected successfully to database: {DB_NAME}")
        return sync_db
        
    except Exception as e:
        logger.error(f"Failed to connect to sync MongoDB: {e}")
        return DummySyncDatabase()

async def initialize_async_mongodb():
    """Initialize asynchronous MongoDB connection using pymongo's async features"""
    global async_client, async_db
    
    try:
        if "+srv" in MONGO_URI:
            logger.info("Connecting to MongoDB Atlas with async SRV connection")
            async_client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                maxIdleTimeMS=60000,
                retryWrites=True,
                maxPoolSize=5,
                waitQueueTimeoutMS=10000,
                retryReads=True,
                tls=True,
                tlsAllowInvalidCertificates=True,
                tlsCAFile=certifi.where()
            )
        else:
            logger.info("Connecting to local MongoDB with async connection")
            async_client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                maxIdleTimeMS=60000,
                retryWrites=True,
                maxPoolSize=5,
                waitQueueTimeoutMS=10000,
                retryReads=True
            )
        
        # Test connection - use sync ping for now since pymongo async is limited
        async_client.admin.command('ping')
        async_db = async_client[DB_NAME]
        logger.info(f"Async MongoDB connected successfully to database: {DB_NAME}")
        return async_db
        
    except Exception as e:
        logger.error(f"Failed to connect to async MongoDB: {e}")
        return DummyAsyncDatabase()

def get_sync_db():
    """Get synchronous MongoDB database"""
    global sync_db
    if sync_db is None:
        sync_db = initialize_sync_mongodb()
    return sync_db

def get_async_db():
    """Get asynchronous MongoDB database (should be initialized with ensure_async_db)"""
    global async_db
    if async_db is None:
        logger.warning("Async DB not initialized. Call await ensure_async_db() at startup.")
        return DummyAsyncDatabase()
    return async_db

async def ensure_async_db():
    """Ensure async database is initialized"""
    global async_db
    if async_db is None:
        async_db = await initialize_async_mongodb()
    return async_db

def get_sync_client():
    """Get synchronous MongoDB client"""
    global sync_client
    if sync_client is None:
        initialize_sync_mongodb()
    return sync_client

def get_async_client():
    """Get asynchronous MongoDB client"""
    global async_client
    if async_client is None:
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                loop.run_until_complete(initialize_async_mongodb())
        except RuntimeError:
            logger.warning("No event loop for async client")
    return async_client

async def close_async_mongodb():
    """Close async MongoDB connection"""
    global async_client, async_db
    if async_client:
        async_client.close()
        async_client = None
        async_db = None
        logger.info("Async MongoDB connection closed")

def close_sync_mongodb():
    """Close sync MongoDB connection"""
    global sync_client, sync_db
    if sync_client:
        sync_client.close()
        sync_client = None
        sync_db = None
        logger.info("Sync MongoDB connection closed")

# Dummy classes for fallback
class DummyAsyncDatabase:
    """Dummy async database for fallback"""
    
    def __init__(self):
        logger.warning("Using DummyAsyncDatabase - MongoDB connection failed")
        self.active_tickets = DummyAsyncCollection("active_tickets")
        self.closed_tickets = DummyAsyncCollection("closed_tickets")
        self.ticket_departments = DummyAsyncCollection("ticket_departments")
        self.ticket_panels = DummyAsyncCollection("ticket_panels")
        self.tickets = DummyAsyncCollection("tickets")
    
    def __getitem__(self, collection_name: str):
        if hasattr(self, collection_name):
            return getattr(self, collection_name)
        return DummyAsyncCollection(collection_name)
    
    async def list_collection_names(self) -> List[str]:
        return []
    
    async def command(self, command: str):
        return {"ok": 1}

class DummyAsyncCollection:
    """Dummy async collection"""
    
    def __init__(self, name: str = "unknown"):
        self.name = name
    
    async def find_one(self, *args, **kwargs):
        logger.debug(f"Dummy async find_one on collection {self.name}")
        return None
    
    def find(self, *args, **kwargs):
        return DummyAsyncCursor()
    
    async def update_one(self, *args, **kwargs):
        logger.debug(f"Dummy async update_one on collection {self.name}")
        return type('UpdateResult', (), {'modified_count': 0, 'matched_count': 0})()
    
    async def insert_one(self, *args, **kwargs):
        logger.debug(f"Dummy async insert_one on collection {self.name}")
        return type('InsertResult', (), {'inserted_id': None})()
    
    async def delete_one(self, *args, **kwargs):
        logger.debug(f"Dummy async delete_one on collection {self.name}")
        return type('DeleteResult', (), {'deleted_count': 0})()
    
    def aggregate(self, *args, **kwargs):
        return DummyAsyncCursor()
    
    async def count_documents(self, *args, **kwargs):
        logger.debug(f"Dummy async count_documents on collection {self.name}")
        return 0

class DummyAsyncCursor:
    """Dummy async cursor"""
    
    async def to_list(self, length=None):
        return []
    
    def limit(self, num):
        return self
    
    def sort(self, *args):
        return self
    
    def skip(self, num):
        return self
    
    async def __aiter__(self):
        return self
    
    async def __anext__(self):
        raise StopAsyncIteration

class DummySyncDatabase:
    """Dummy sync database for fallback"""
    
    def __init__(self):
        logger.warning("Using DummySyncDatabase - MongoDB connection failed")
    
    def __getitem__(self, collection_name: str):
        return DummySyncCollection(collection_name)
    
    def list_collection_names(self) -> List[str]:
        return []

class DummySyncCollection:
    """Dummy sync collection"""
    
    def __init__(self, name: str = "unknown"):
        self.name = name
    
    def find_one(self, *args, **kwargs):
        logger.debug(f"Dummy sync find_one on collection {self.name}")
        return None
    
    def find(self, *args, **kwargs):
        return []
    
    def update_one(self, *args, **kwargs):
        logger.debug(f"Dummy sync update_one on collection {self.name}")
        return type('UpdateResult', (), {'modified_count': 0, 'matched_count': 0})()
    
    def insert_one(self, *args, **kwargs):
        logger.debug(f"Dummy sync insert_one on collection {self.name}")
        return type('InsertResult', (), {'inserted_id': None})()
    
    def delete_one(self, *args, **kwargs):
        logger.debug(f"Dummy sync delete_one on collection {self.name}")
        return type('DeleteResult', (), {'deleted_count': 0})()
    
    def aggregate(self, *args, **kwargs):
        return []
    
    def count_documents(self, *args, **kwargs):
        logger.debug(f"Dummy sync count_documents on collection {self.name}")
        return 0

# Backward compatibility functions
def initialize_mongodb():
    """Legacy function for backward compatibility"""
    return initialize_sync_mongodb()

async def test_async_connection():
    """Test async MongoDB connection"""
    try:
        db = await ensure_async_db()
        # Use sync ping since pymongo async is limited
        db.command('ping')
        logger.info('Async MongoDB connected successfully!')
        return True
    except Exception as e:
        logger.error(f'Async MongoDB connection failed: {e}')
        return False

def test_sync_connection():
    """Test sync MongoDB connection"""
    try:
        db = get_sync_db()
        db.command('ping')
        logger.info('Sync MongoDB connected successfully!')
        return True
    except Exception as e:
        logger.error(f'Sync MongoDB connection failed: {e}')
        return False

def get_collection(collection_name, db=None):
    """Get a collection from the database (sync)"""
    if db is None:
        db = get_sync_db()
    return db[collection_name]

def is_db_available(db):
    """Check if db is not None and not a DummySyncDatabase"""
    return db is not None and not isinstance(db, DummySyncDatabase)

def get_database(db_name=None):
    """
    Get a synchronous MongoDB database connection
    """
    if db_name is None:
        db_name = os.getenv("DB", "contro-bot-db")
    db = get_sync_db()
    if hasattr(db, '__getitem__'):
        return db[db_name]
    return db
