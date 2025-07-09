from src.utils.database.connection import get_database
from datetime import datetime

async def increment_utility_stat(guild_id: int, stat_field: str, amount: int = 1):
    db = await get_database()
    collection = db.get_collection('utility_stats')
    await collection.update_one(
        {'guild_id': guild_id},
        {
            '$inc': {stat_field: amount},
            '$set': {'lastAction': datetime.utcnow(), 'updated_at': datetime.utcnow()}
        },
        upsert=True
    ) 