"""Database connection management for MongoDB Atlas."""
import motor.motor_asyncio
from typing import Optional, Dict, Any, List
import logging
from pymongo import ASCENDING, DESCENDING
import certifi

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages MongoDB Atlas connection and operations."""
    
    def __init__(self, connection_string: str, database_name: str):
        """Initialize database connection.
        
        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self._client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self._db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None
    
    async def connect(self):
        """Connect to MongoDB Atlas."""
        if self._client is None:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(
                self.connection_string,
                tlsCAFile=certifi.where()
            )
            self._db = self._client[self.database_name]
            
            # Test connection
            await self._client.server_info()
            logger.info(f"Connected to MongoDB Atlas database: {self.database_name}")
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Disconnected from MongoDB Atlas")
    
    @property
    def db(self) -> motor.motor_asyncio.AsyncIOMotorDatabase:
        """Get database instance."""
        if not self._db:
            raise RuntimeError("Database not connected")
        return self._db
    
    def get_collection(self, collection_name: str) -> motor.motor_asyncio.AsyncIOMotorCollection:
        """Get a collection from the database.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection instance
        """
        return self.db[collection_name]
    
    async def find_one(self, collection: str, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document.
        
        Args:
            collection: Collection name
            filter: Query filter
            
        Returns:
            Document or None
        """
        coll = self.get_collection(collection)
        return await coll.find_one(filter)
    
    async def find_many(
        self, 
        collection: str, 
        filter: Dict[str, Any] = None,
        sort: List[tuple] = None,
        limit: int = None,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Find multiple documents.
        
        Args:
            collection: Collection name
            filter: Query filter
            sort: Sort specification
            limit: Maximum number of documents
            skip: Number of documents to skip
            
        Returns:
            List of documents
        """
        coll = self.get_collection(collection)
        cursor = coll.find(filter or {})
        
        if sort:
            cursor = cursor.sort(sort)
        if skip > 0:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        
        return await cursor.to_list(length=None)
    
    async def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """Insert a single document.
        
        Args:
            collection: Collection name
            document: Document to insert
            
        Returns:
            Inserted document ID
        """
        coll = self.get_collection(collection)
        result = await coll.insert_one(document)
        return str(result.inserted_id)
    
    async def insert_many(self, collection: str, documents: List[Dict[str, Any]]) -> List[str]:
        """Insert multiple documents.
        
        Args:
            collection: Collection name
            documents: Documents to insert
            
        Returns:
            List of inserted document IDs
        """
        coll = self.get_collection(collection)
        result = await coll.insert_many(documents)
        return [str(id) for id in result.inserted_ids]
    
    async def update_one(
        self, 
        collection: str, 
        filter: Dict[str, Any], 
        update: Dict[str, Any],
        upsert: bool = False
    ) -> int:
        """Update a single document.
        
        Args:
            collection: Collection name
            filter: Query filter
            update: Update operations
            upsert: Create if doesn't exist
            
        Returns:
            Number of modified documents
        """
        coll = self.get_collection(collection)
        result = await coll.update_one(filter, update, upsert=upsert)
        return result.modified_count
    
    async def update_many(
        self, 
        collection: str, 
        filter: Dict[str, Any], 
        update: Dict[str, Any]
    ) -> int:
        """Update multiple documents.
        
        Args:
            collection: Collection name
            filter: Query filter
            update: Update operations
            
        Returns:
            Number of modified documents
        """
        coll = self.get_collection(collection)
        result = await coll.update_many(filter, update)
        return result.modified_count
    
    async def delete_one(self, collection: str, filter: Dict[str, Any]) -> int:
        """Delete a single document.
        
        Args:
            collection: Collection name
            filter: Query filter
            
        Returns:
            Number of deleted documents
        """
        coll = self.get_collection(collection)
        result = await coll.delete_one(filter)
        return result.deleted_count
    
    async def delete_many(self, collection: str, filter: Dict[str, Any]) -> int:
        """Delete multiple documents.
        
        Args:
            collection: Collection name
            filter: Query filter
            
        Returns:
            Number of deleted documents
        """
        coll = self.get_collection(collection)
        result = await coll.delete_many(filter)
        return result.deleted_count
    
    async def count_documents(self, collection: str, filter: Dict[str, Any] = None) -> int:
        """Count documents matching filter.
        
        Args:
            collection: Collection name
            filter: Query filter
            
        Returns:
            Document count
        """
        coll = self.get_collection(collection)
        return await coll.count_documents(filter or {})
    
    async def create_indexes(self):
        """Create database indexes for better performance."""
        # Guild indexes
        guilds = self.get_collection("guilds")
        await guilds.create_index("guild_id", unique=True)
        await guilds.create_index("created_at")
        
        # User indexes
        users = self.get_collection("users")
        await users.create_index("user_id", unique=True)
        await users.create_index([("global_xp", DESCENDING)])
        
        # Member indexes
        members = self.get_collection("members")
        await members.create_index([("guild_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
        await members.create_index([("guild_id", ASCENDING), ("xp", DESCENDING)])
        await members.create_index("user_id")
        
        logger.info("Database indexes created/verified") 