"""Database utilities for MongoDB asynchronous operations."""
import os
import logging
from typing import Optional, Dict, List, Any, Union, TYPE_CHECKING
import dotenv
import asyncio
import motor.motor_asyncio
import pymongo
import time
from ..core.logger import logger
import certifi

# Motor kütüphanesi, MongoDB için asenkron işlemler sağlar
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# Giveaways ve diğer modüller için gereken sınıf
AsyncMongoClient = AsyncIOMotorClient  # Basit bir alias oluşturuyoruz

# Type tanımlamaları - direkt modül importları yerine TYPE_CHECKING kullanılır
if TYPE_CHECKING:
    # Type checking sırasında kullanılacak tip tanımlamaları
    from motor.motor_asyncio import AsyncIOMotorDatabase as AsyncDatabase
    from motor.motor_asyncio import AsyncIOMotorCollection as AsyncCollection
else:
    # Runtime'da kullanılacak sınıflar
    try:
        # Motor sınıflarını içe aktar
        from motor.motor_asyncio import AsyncIOMotorDatabase as AsyncDatabase
        from motor.motor_asyncio import AsyncIOMotorCollection as AsyncCollection
    except ImportError:
        # İçe aktarma başarısız olursa kendi sınıflarımızı tanımlayalım
        class AsyncDatabase:
            """Type placeholder for AsyncDatabase if not available"""
            pass
        
        class AsyncCollection:
            """Type placeholder for AsyncCollection if not available"""
            pass

# Ensure environment variables are loaded
dotenv.load_dotenv()

# Set up logging
logger = logging.getLogger('database')

# Güvenli bir şekilde veritabanını kontrol eden yardımcı fonksiyon
def is_db_available(db):
    """Safely check if database is available"""
    return db is not None

class AsyncMongoManager:
    """Asynchronous MongoDB manager using Motor"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional["AsyncDatabase"] = None
        self.connection_string: Optional[str] = None
        self.db_name: str = "contro"
        self.is_connected: bool = False
        self.connection_attempts: int = 0
        self.max_retries: int = 5
        
    async def initialize(self, connection_string: Optional[str] = None) -> Optional["AsyncDatabase"]:
        """Initialize async MongoDB connection"""
        self.connection_attempts += 1
        
        try:
            # Get MongoDB URI from environment
            if not connection_string:
                connection_string = os.getenv('MONGO_DB') or os.getenv('MONGODB_URI')
                
            if not connection_string:
                connection_string = "mongodb://localhost:27017/"
                logger.warning("MongoDB URI not found in environment variables! Using default connection.")
            else:
                # Mask sensitive parts for logging
                safe_uri = self._mask_uri(connection_string)
                logger.info(f"Connecting to MongoDB with URI: {safe_uri}")
            
            self.connection_string = connection_string
              # Create Motor AsyncIOMotorClient with optimal settings
            if "+srv" in connection_string:
                logger.info("MongoDB Atlas SRV connection detected, configuring SSL/TLS")
                
                # SSL/TLS için ek ayarlar - PyMongo'nun yeni versiyonlarıyla uyumlu
                ssl_options = {
                    'tls': True, # ssl yerine tls kullanılıyor yeni versiyonlarda
                    'tlsAllowInvalidCertificates': True,
                }
                
                # Motor AsyncIOMotorClient ile optimal ayarlar
                self.client = AsyncIOMotorClient(
                    connection_string,
                    serverSelectionTimeoutMS=30000,   # Increased timeout for server selection
                    connectTimeoutMS=30000,           # Increased timeout for initial connection
                    socketTimeoutMS=60000,            # Increased socket timeout to 60s
                    maxIdleTimeMS=90000,              # Keep connections alive longer
                    retryWrites=True,                 # Enable retry for write operations
                    maxPoolSize=10,                   # Reduced connection pool size
                    waitQueueTimeoutMS=20000,         # Increased wait for connection from pool
                    retryReads=True,                  # Enable retry for read operations
                    heartbeatFrequencyMS=60000,       # Heart beat frequency (increased)
                    **ssl_options                     # SSL/TLS options for Atlas
                )
            else:
                # Yerel veya özel MongoDB için standart bağlantı
                self.client = AsyncIOMotorClient(
                    connection_string,
                    serverSelectionTimeoutMS=30000,   # Increased timeout for server selection
                    connectTimeoutMS=30000,           # Increased timeout for initial connection
                    socketTimeoutMS=60000,            # Increased socket timeout to 60s
                    maxIdleTimeMS=90000,              # Keep connections alive longer
                    retryWrites=True,                 # Enable retry for write operations
                    maxPoolSize=10,                   # Reduced connection pool size
                    waitQueueTimeoutMS=20000,         # Increased wait for connection from pool
                    retryReads=True,                  # Enable retry for read operations
                    heartbeatFrequencyMS=60000,       # Heart beat frequency (increased)
                )
            
            # Get database name
            self.db_name = os.getenv('DB', 'contro')
            if not self.db_name:
                self.db_name = "contro"
                
            # Get database reference
            self.db = self.client[self.db_name]
            
            # Test connection
            await self._test_connection()
            
            self.is_connected = True
            self.connection_attempts = 0
            logger.info(f"MongoDB async connection established successfully to database: {self.db_name}")
            return self.db
            
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            logger.error(f"MongoDB connection error: {e}")
              # Retry logic
            if self.connection_attempts < self.max_retries:
                retry_delay = min(5 + self.connection_attempts * 2, 15)  # Increased retry delay, max 15 seconds
                logger.info(f"Retrying MongoDB connection in {retry_delay} seconds (attempt {self.connection_attempts}/{self.max_retries})...")
                await asyncio.sleep(retry_delay)
                return await self.initialize(connection_string)
            
            # Create fallback database
            logger.warning("Using DummyAsyncDatabase as fallback after failed connection attempts")
            self.db = DummyAsyncDatabase()
            return self.db
            
        except Exception as e:
            logger.error(f"Failed to initialize async MongoDB: {e}", exc_info=True)
            # Create fallback database
            self.db = DummyAsyncDatabase()
            return self.db
    
    async def _test_connection(self):
        """Test the MongoDB connection"""
        try:
            # Test with server info and ping
            await self.client.admin.command('ping')
            server_info = await self.client.server_info()
            logger.info(f"MongoDB server version: {server_info.get('version', 'unknown')}")
        except ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB connection timed out - server may be down: {e}")
            # Log connection details for debugging (mask sensitive info)
            conn_str = self._mask_uri(self.connection_string)
            logger.error(f"Connection details: {conn_str}, Options: {self.client.options}")
            raise
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            # Log connection details
            conn_str = self._mask_uri(self.connection_string)
            logger.error(f"Connection details: {conn_str}, Options: {self.client.options}")
            raise
        except Exception as e:
            logger.error(f"MongoDB connection test failed: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            # Print traceback for better debugging
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _mask_uri(self, uri: str) -> str:
        """Mask sensitive parts of the URI for logging"""
        if '@' in uri:
            return uri.split('@')[0][:15] + "...@<host>"
        return "***masked***"
    
    async def close(self):
        """Close the MongoDB connection"""
        if self.client:
            self.client.close()  # Motor client's close() is not async
            self.is_connected = False
            logger.info("MongoDB connection closed")
    
    def get_collection(self, collection_name: str) -> "AsyncCollection":
        """Get a collection from the database"""
        if self.db is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.db[collection_name]
    
    def __getitem__(self, collection_name: str) -> "AsyncCollection":
        """Allow dict-like access to collections"""
        return self.get_collection(collection_name)
    
    async def list_collection_names(self) -> List[str]:
        """List all collection names in the database"""
        if self.db is None:
            return []
        return await self.db.list_collection_names()
    
    async def ensure_connected(self) -> bool:
        """Ensure the database is connected, reconnect if needed"""
        if not self.is_connected and self.connection_attempts < self.max_retries:
            try:
                await self.initialize(self.connection_string)
                return self.is_connected
            except Exception as e:
                logger.error(f"Failed to reconnect to MongoDB: {e}")
                return False
        return self.is_connected

# Global async MongoDB manager instance
_mongo_manager: Optional[AsyncMongoManager] = None

async def initialize_async_mongodb(connection_string: Optional[str] = None) -> "AsyncDatabase":
    """Initialize async MongoDB connection (preferred method)"""
    global _mongo_manager
    
    if _mongo_manager is None:
        _mongo_manager = AsyncMongoManager()
    
    db = await _mongo_manager.initialize(connection_string)
    
    # Make sure we return something (either real DB or fallback)
    if db is None:
        logger.warning("MongoDB initialization failed, returning DummyAsyncDatabase")
        return DummyAsyncDatabase()
    
    return db

def get_async_db() -> "AsyncDatabase":
    """Get the current async database instance"""
    global _mongo_manager
    
    if _mongo_manager is None or _mongo_manager.db is None:
        logger.warning("Async MongoDB not initialized. Using DummyAsyncDatabase.")
        return DummyAsyncDatabase()
    
    return _mongo_manager.db

def get_async_client() -> Optional[AsyncIOMotorClient]:
    """Get the current async client instance"""
    global _mongo_manager
    
    if _mongo_manager is None:
        logger.warning("Async MongoDB not initialized. Call initialize_async_mongodb() first.")
        return None
    
    return _mongo_manager.client

# Sync MongoDB functions for backward compatibility
def initialize_mongodb() -> Any:
    """Synchronous MongoDB initialization (legacy, for backward compatibility)"""
    max_retries = 5
    retry_delay = 5
    attempt = 0
    
    while attempt < max_retries:
        attempt += 1
        try:
            connection_string = os.getenv('MONGO_DB') or os.getenv('MONGODB_URI')
            
            if not connection_string:
                connection_string = "mongodb://localhost:27017/"
                logger.warning("MongoDB URI not found in environment variables! Using default connection.")
            
            # Check if this is an Atlas connection (srv connection string)
            if "+srv" in connection_string:
                logger.info("MongoDB Atlas SRV connection detected for sync connection, configuring SSL/TLS")
                
                # Additional SSL/TLS settings for modern pymongo versions
                client = MongoClient(
                    connection_string,
                    serverSelectionTimeoutMS=60000,    # Increased from 5000 (60 seconds)
                    connectTimeoutMS=60000,            # Increased from 5000 (60 seconds)
                    socketTimeoutMS=120000,            # Increased from 60000 (120 seconds)
                    maxIdleTimeMS=180000,              # Increased from 90000 (180 seconds)
                    retryWrites=True,                  # Keep as is
                    maxPoolSize=50,                    # Keep as is
                    waitQueueTimeoutMS=30000,          # Increased from 10000 (30 seconds)
                    tls=True,                          # Modern pymongo uses tls instead of ssl
                    tlsAllowInvalidCertificates=True,  # Bypass certificate validation issues
                    retryReads=True                    # Added for better reliability
                )
            else:
                # Standard connection for local or custom MongoDB
                client = MongoClient(
                    connection_string,
                    serverSelectionTimeoutMS=60000,    # Increased (60 seconds)
                    connectTimeoutMS=60000,            # Increased (60 seconds)
                    socketTimeoutMS=120000,            # Increased (120 seconds)
                    maxIdleTimeMS=180000,              # Increased (180 seconds)
                    retryWrites=True,
                    maxPoolSize=50,
                    waitQueueTimeoutMS=30000,          # Increased (30 seconds)
                    retryReads=True
                )
            
            db_name = os.getenv('DB', 'contro')
            db = client[db_name]
            
            # Test connection - with shorter timeout to fail faster
            client.admin.command('ping', serverSelectionTimeoutMS=30000)
            logger.info(f"Sync MongoDB connected successfully to database: {db_name}")
            
            return db
            
        except Exception as e:
            logger.error(f"Failed to connect to sync MongoDB (attempt {attempt}/{max_retries}): {e}")
            
            if attempt < max_retries:
                logger.info(f"Retrying connection in {retry_delay} seconds...")
                time.sleep(retry_delay)
                # Increase delay for next attempt, but not more than 15 seconds
                retry_delay = min(retry_delay + 2, 15)
            else:
                logger.error("Maximum sync MongoDB connection attempts reached, using fallback")
                # Return a functional fallback object
                return DummySyncDatabase()

async def close_async_mongodb():
    """Close async MongoDB connection"""
    global _mongo_manager
    
    if _mongo_manager:
        await _mongo_manager.close()
        _mongo_manager = None

# Utility functions for common operations
async def ensure_async_db() -> "AsyncDatabase":
    """Ensure async database is initialized and return it"""
    db = get_async_db()
    if isinstance(db, DummyAsyncDatabase) and _mongo_manager and _mongo_manager.connection_attempts < _mongo_manager.max_retries:
        # Try to reinitialize
        db = await initialize_async_mongodb()
    return db

class DummyAsyncDatabase:
    """Dummy async database for fallback when connection fails"""
    
    def __init__(self):
        logger.warning("Using DummyAsyncDatabase - MongoDB connection failed")
        # Add commonly accessed collections as properties
        self.levelling_settings = DummyAsyncCollection("levelling_settings")
        self.feature_toggles = DummyAsyncCollection("feature_toggles")
        self.server_settings = DummyAsyncCollection("server_settings")
        self.welcomer = DummyAsyncCollection("welcomer")
        self.ticket_settings = DummyAsyncCollection("ticket_settings")
        self.turkoyto_users = DummyAsyncCollection("turkoyto_users")
        self.users = DummyAsyncCollection("users")
    
    def __getitem__(self, collection_name: str):
        # Return existing collection if it's one of the predefined ones
        if hasattr(self, collection_name):
            return getattr(self, collection_name)
        return DummyAsyncCollection(collection_name)
    
    async def list_collection_names(self) -> List[str]:
        return []

class DummyAsyncCollection:
    """Dummy async collection that returns empty results"""
    
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
    """Dummy sync database for fallback when connection fails"""
    
    def __init__(self):
        logger.warning("Using DummySyncDatabase - MongoDB connection failed")
    
    def __getitem__(self, collection_name: str):
        return DummySyncCollection(collection_name)
    
    def list_collection_names(self) -> List[str]:
        return []

class DummySyncCollection:
    """Dummy sync collection that returns empty results"""
    
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

def is_async_client(client_or_db) -> bool:
    """Check if a client or database is an async instance"""
    if hasattr(motor.motor_asyncio, 'AsyncIOMotorDatabase'):
        AsyncDatabase = motor.motor_asyncio.AsyncIOMotorDatabase
    else:
        # Fallback to basic type check that will still work
        return 'AsyncIOMotor' in str(type(client_or_db))
        
    return isinstance(client_or_db, (AsyncIOMotorClient, AsyncDatabase))

# Legacy alias for backward compatibility
async_initialize_mongodb = initialize_async_mongodb

def get_database(db_name=None):
    """
    Get a synchronous MongoDB database connection
    
    Args:
        db_name (str, optional): Database name, uses default from env if None
        
    Returns:
        pymongo.database.Database: MongoDB database connection
    """
    client = initialize_mongodb()
    if db_name is None:
        db_name = os.getenv("MONGODB_DATABASE", "controBot")
    return client[db_name]

def get_collection(collection_name, db_name=None):
    """
    Get a synchronous MongoDB collection
    
    Args:
        collection_name (str): Collection name
        db_name (str, optional): Database name, uses default if None
        
    Returns:
        pymongo.collection.Collection: MongoDB collection
    """
    db = get_database(db_name)
    return db[collection_name]
