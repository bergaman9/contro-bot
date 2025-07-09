import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def cleanup_old_games_docs():
    mongo_uri = os.getenv('MONGO_DB', 'mongodb://localhost:27017')
    db_name = os.getenv('DB', 'contro-bot-db')
    print(f"Connecting to MongoDB: {mongo_uri}")
    print(f"Database: {db_name}")
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    # Silinecek dokümanları bul
    old_docs = db.games.find({
        '$or': [
            { 'guild_id': { '$exists': False } },
            { 'games': { '$exists': False } }
        ]
    })
    count = 0
    async for doc in old_docs:
        print(f"Deleting old doc: {doc.get('_id')} - {doc.get('name', '')}")
        await db.games.delete_one({'_id': doc['_id']})
        count += 1
    print(f"Deleted {count} old games documents.")

if __name__ == "__main__":
    asyncio.run(cleanup_old_games_docs()) 