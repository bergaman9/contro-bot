#!/usr/bin/env python3
"""
MongoDB Atlas connection test script
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_mongodb_connection():
    """Test MongoDB Atlas connection"""
    try:
        from src.utils.database.connection import test_async_connection, test_sync_connection
        
        print("🔍 Testing MongoDB Atlas connection...")
        print(f"MongoDB URI: {os.getenv('MONGO_DB', 'Not set')}")
        print(f"Database: {os.getenv('DB', 'contro')}")
        
        # Test sync connection
        print("\n📡 Testing sync connection...")
        sync_success = test_sync_connection()
        if sync_success:
            print("✅ Sync MongoDB connection successful!")
        else:
            print("❌ Sync MongoDB connection failed!")
        
        # Test async connection
        print("\n🔄 Testing async connection...")
        async_success = await test_async_connection()
        if async_success:
            print("✅ Async MongoDB connection successful!")
        else:
            print("❌ Async MongoDB connection failed!")
        
        return sync_success and async_success
        
    except Exception as e:
        print(f"❌ Error testing MongoDB connection: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_ticket_collections():
    """Test ticket-related collections"""
    try:
        from src.utils.database.connection import get_async_db, get_sync_db
        
        print("\n🎫 Testing ticket collections...")
        
        # Test async collections
        async_db = get_async_db()
        collections = ['active_tickets', 'closed_tickets', 'ticket_departments', 'ticket_panels']
        
        for collection_name in collections:
            try:
                collection = async_db[collection_name]
                # Use sync count_documents since pymongo async is limited
                count = collection.count_documents({})
                print(f"✅ {collection_name}: {count} documents")
            except Exception as e:
                print(f"❌ {collection_name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing collections: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 MongoDB Atlas Connection Test")
    print("=" * 40)
    
    # Test basic connection
    connection_ok = await test_mongodb_connection()
    
    if connection_ok:
        # Test collections
        await test_ticket_collections()
        
        print("\n🎉 All tests completed!")
    else:
        print("\n💥 Connection tests failed!")
        print("\n📋 Troubleshooting:")
        print("1. Check your .env file has MONGO_DB or MONGODB_URI set")
        print("2. Ensure your MongoDB Atlas cluster is running")
        print("3. Verify your connection string format:")
        print("   mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority")
        print("4. Check your IP is whitelisted in MongoDB Atlas")

if __name__ == "__main__":
    asyncio.run(main()) 