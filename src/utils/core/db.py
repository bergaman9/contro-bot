"""Database utility wrappers for interacting with MongoDB."""
import asyncio
import logging
from typing import Optional, Dict, List, Any, Union

from src.utils.database.connection import (
    initialize_mongodb, 
    initialize_async_mongodb,
    get_database, 
    get_async_db, 
    get_collection
)

# Create an alias for backward compatibility
async_initialize_mongodb = initialize_async_mongodb

# Setup logging
logger = logging.getLogger(__name__)

async def get_document(collection_name, query, db=None):
    """
    Get a single document from the specified collection.
    
    Args:
        collection_name (str): The name of the collection
        query (dict): The query to search for
        db: Optional database connection, will use default if None
        
    Returns:
        The document if found, otherwise None
    """
    if db is None:
        db = get_async_db()
    
    try:
        collection = db[collection_name]
        document = await collection.find_one(query)
        return document
    except Exception as e:
        logger.error(f"Error retrieving document: {e}")
        return None

async def get_documents(collection_name, query, sort=None, limit=0, db=None):
    """
    Get multiple documents from the specified collection.
    
    Args:
        collection_name (str): The name of the collection
        query (dict): The query to search for
        sort (tuple): Optional sorting tuple of (field, direction)
        limit (int): Optional limit of results (0 = no limit)
        db: Optional database connection, will use default if None
        
    Returns:
        List of documents or empty list if none found
    """
    if db is None:
        db = get_async_db()
    
    try:
        collection = db[collection_name]
        cursor = collection.find(query)
        
        if sort:
            cursor = cursor.sort(*sort)
        
        if limit > 0:
            cursor = cursor.limit(limit)
            
        return await cursor.to_list(length=limit or None)
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        return []

async def insert_document(collection_name, document, db=None):
    """
    Insert a single document into the specified collection.
    
    Args:
        collection_name (str): The name of the collection
        document (dict): The document to insert
        db: Optional database connection, will use default if None
        
    Returns:
        The inserted document ID if successful, otherwise None
    """
    if db is None:
        db = get_async_db()
    
    try:
        collection = db[collection_name]
        result = await collection.insert_one(document)
        return result.inserted_id
    except Exception as e:
        logger.error(f"Error inserting document: {e}")
        return None

async def update_document(collection_name, query, update, upsert=False, db=None):
    """
    Update a single document in the specified collection.
    
    Args:
        collection_name (str): The name of the collection
        query (dict): The query to find the document to update
        update (dict): The update operations to perform
        upsert (bool): Whether to insert if document doesn't exist
        db: Optional database connection, will use default if None
        
    Returns:
        True if successful, otherwise False
    """
    if db is None:
        db = get_async_db()
    
    try:
        collection = db[collection_name]
        result = await collection.update_one(query, update, upsert=upsert)
        return result.modified_count > 0 or (upsert and result.upserted_id is not None)
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        return False

async def delete_document(collection_name, query, db=None):
    """
    Delete a single document from the specified collection.
    
    Args:
        collection_name (str): The name of the collection
        query (dict): The query to find the document to delete
        db: Optional database connection, will use default if None
        
    Returns:
        True if successful, otherwise False
    """
    if db is None:
        db = get_async_db()
    
    try:
        collection = db[collection_name]
        result = await collection.delete_one(query)
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return False

# Sync versions for compatibility

def get_document_sync(collection_name, query, db=None):
    """Synchronous version of get_document"""
    if db is None:
        db = get_database()
    
    try:
        collection = db[collection_name]
        document = collection.find_one(query)
        return document
    except Exception as e:
        logger.error(f"Error retrieving document (sync): {e}")
        return None

def get_documents_sync(collection_name, query, sort=None, limit=0, db=None):
    """Synchronous version of get_documents"""
    if db is None:
        db = get_database()
    
    try:
        collection = db[collection_name]
        cursor = collection.find(query)
        
        if sort:
            cursor = cursor.sort(*sort)
        
        if limit > 0:
            cursor = cursor.limit(limit)
            
        return list(cursor)
    except Exception as e:
        logger.error(f"Error retrieving documents (sync): {e}")
        return [] 