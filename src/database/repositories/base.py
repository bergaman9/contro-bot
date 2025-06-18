"""Base repository for MongoDB database operations."""
from typing import Optional, List, Dict, Any, Type, TypeVar
from ..models.base import BaseModel
from ..connection import DatabaseConnection
from datetime import datetime
import logging

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class for MongoDB operations."""
    
    def __init__(self, connection: DatabaseConnection, model_class: Type[T], collection_name: str):
        """Initialize repository.
        
        Args:
            connection: Database connection
            model_class: Model class to use
            collection_name: MongoDB collection name
        """
        self.db = connection
        self.model_class = model_class
        self.collection_name = collection_name
    
    @property
    def collection(self):
        """Get MongoDB collection."""
        return self.db.get_collection(self.collection_name)
    
    async def find_by_id(self, id_value: Any, id_field: str = '_id') -> Optional[T]:
        """Find a document by ID.
        
        Args:
            id_value: ID value to search for
            id_field: Name of the ID field
            
        Returns:
            Model instance or None
        """
        filter = {id_field: id_value}
        doc = await self.db.find_one(self.collection_name, filter)
        
        if doc:
            return self.model_class.from_dict(doc)
        return None
    
    async def find_all(self, limit: Optional[int] = None, skip: int = 0, sort: List[tuple] = None) -> List[T]:
        """Find all documents.
        
        Args:
            limit: Maximum number of documents to return
            skip: Number of documents to skip
            sort: Sort specification
            
        Returns:
            List of model instances
        """
        docs = await self.db.find_many(
            self.collection_name,
            filter={},
            sort=sort,
            limit=limit,
            skip=skip
        )
        return [self.model_class.from_dict(doc) for doc in docs]
    
    async def find_by(self, sort: List[tuple] = None, limit: Optional[int] = None, **criteria) -> List[T]:
        """Find documents by criteria.
        
        Args:
            sort: Sort specification
            limit: Maximum number of results
            **criteria: Field-value pairs to match
            
        Returns:
            List of model instances
        """
        filter = {k: v for k, v in criteria.items() if v is not None}
        
        docs = await self.db.find_many(
            self.collection_name,
            filter=filter,
            sort=sort,
            limit=limit
        )
        
        return [self.model_class.from_dict(doc) for doc in docs]
    
    async def find_one_by(self, **criteria) -> Optional[T]:
        """Find a single document by criteria.
        
        Args:
            **criteria: Field-value pairs to match
            
        Returns:
            Model instance or None
        """
        filter = {k: v for k, v in criteria.items() if v is not None}
        doc = await self.db.find_one(self.collection_name, filter)
        
        if doc:
            return self.model_class.from_dict(doc)
        return None
    
    async def create(self, data: Dict[str, Any]) -> T:
        """Create a new document.
        
        Args:
            data: Data for the new document
            
        Returns:
            Created model instance
        """
        # Add timestamps if not present
        now = datetime.utcnow()
        data.setdefault('created_at', now)
        data.setdefault('updated_at', now)
        
        # Insert document
        doc_id = await self.db.insert_one(self.collection_name, data)
        
        # Add the generated ID
        data['_id'] = doc_id
        
        return self.model_class.from_dict(data)
    
    async def update(self, model: T) -> bool:
        """Update a document.
        
        Args:
            model: Model instance to update
            
        Returns:
            True if updated, False otherwise
        """
        if not model.is_modified:
            return True
        
        # Get modified fields
        update_data = model.get_modified_fields()
        if not update_data:
            return True
        
        # Update timestamp
        update_data['updated_at'] = datetime.utcnow()
        
        # Determine ID field and value
        id_field, id_value = self._get_id_field_and_value(model)
        
        # Update document
        result = await self.db.update_one(
            self.collection_name,
            filter={id_field: id_value},
            update={'$set': update_data}
        )
        
        if result > 0:
            model.reset_modifications()
            return True
        
        return False
    
    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """Update a single document directly.
        
        Args:
            filter: Query filter
            update: Update operations
            
        Returns:
            True if updated, False otherwise
        """
        # Add updated_at timestamp
        if '$set' in update:
            update['$set']['updated_at'] = datetime.utcnow()
        else:
            update.setdefault('$set', {})['updated_at'] = datetime.utcnow()
        
        result = await self.db.update_one(self.collection_name, filter, update)
        return result > 0
    
    async def upsert(self, filter: Dict[str, Any], data: Dict[str, Any]) -> T:
        """Update or insert a document.
        
        Args:
            filter: Query filter
            data: Document data
            
        Returns:
            Model instance
        """
        now = datetime.utcnow()
        data['updated_at'] = now
        
        # Try to update first
        update = {'$set': data, '$setOnInsert': {'created_at': now}}
        
        await self.db.update_one(
            self.collection_name,
            filter=filter,
            update=update,
            upsert=True
        )
        
        # Fetch the document
        doc = await self.db.find_one(self.collection_name, filter)
        return self.model_class.from_dict(doc)
    
    async def delete(self, model: T) -> bool:
        """Delete a document.
        
        Args:
            model: Model instance to delete
            
        Returns:
            True if deleted, False otherwise
        """
        id_field, id_value = self._get_id_field_and_value(model)
        
        result = await self.db.delete_one(
            self.collection_name,
            filter={id_field: id_value}
        )
        
        return result > 0
    
    async def delete_by_id(self, id_value: Any, id_field: str = '_id') -> bool:
        """Delete a document by ID.
        
        Args:
            id_value: ID value
            id_field: Name of the ID field
            
        Returns:
            True if deleted, False otherwise
        """
        result = await self.db.delete_one(
            self.collection_name,
            filter={id_field: id_value}
        )
        
        return result > 0
    
    async def count(self, **criteria) -> int:
        """Count documents matching criteria.
        
        Args:
            **criteria: Field-value pairs to match
            
        Returns:
            Number of matching documents
        """
        filter = {k: v for k, v in criteria.items() if v is not None}
        return await self.db.count_documents(self.collection_name, filter)
    
    async def exists(self, **criteria) -> bool:
        """Check if documents exist matching criteria.
        
        Args:
            **criteria: Field-value pairs to match
            
        Returns:
            True if exists, False otherwise
        """
        count = await self.count(**criteria)
        return count > 0
    
    def _get_id_field_and_value(self, model: T) -> tuple[str, Any]:
        """Get the ID field name and value for a model."""
        # Try common ID field names
        for field in ['_id', 'id', f'{self.collection_name[:-1]}_id', 'user_id', 'guild_id']:
            if hasattr(model, field) and getattr(model, field) is not None:
                return field, getattr(model, field)
        
        raise ValueError(f"Could not determine ID field for {model.__class__.__name__}") 