import os
from pymongo import MongoClient, ASCENDING

MONGO_URI = os.getenv('MONGO_DB') or os.getenv('MONGODB_URI') or 'mongodb://localhost:27017/'
DB_NAME = os.getenv('DB', 'contro')

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def ensure_collection(name):
    if name not in db.list_collection_names():
        db.create_collection(name)
        print(f"Created collection: {name}")
    else:
        print(f"Collection already exists: {name}")

def ensure_index(collection, field, unique=False):
    indexes = [idx['key'][0][0] for idx in collection.list_indexes()]
    if field not in indexes:
        collection.create_index([(field, ASCENDING)], unique=unique)
        print(f"Created index on {collection.name}.{field}")
    else:
        print(f"Index already exists on {collection.name}.{field}")

def main():
    # 1. giveaways koleksiyonu ve indexler
    ensure_collection('giveaways')
    giveaways = db['giveaways']
    ensure_index(giveaways, 'guild_id')
    ensure_index(giveaways, 'end_time')
    ensure_index(giveaways, 'ended')

    # 2. giveaway_settings
    ensure_collection('giveaway_settings')
    # 3. giveaway_history
    ensure_collection('giveaway_history')
    # 4. giveaway_participants
    ensure_collection('giveaway_participants')

    print("Migration completed.")

if __name__ == '__main__':
    main() 