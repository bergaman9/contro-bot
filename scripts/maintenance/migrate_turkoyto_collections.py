from pymongo import MongoClient
import os
import re
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Use the full connection string from the environment
MONGO_URI = os.getenv("MONGO_DB", "mongodb://localhost:27017/contro-bot-db")

# Try to extract the DB name from the connection string
match = re.search(r"/(\w+)(\?|$)", MONGO_URI)
if match:
    DB_NAME = match.group(1)
else:
    DB_NAME = "contro-bot-db"

RENAME_MAP = {
    "turkoyto_games": "games",
    "turkoyto_users": "users",
    "turkoyto_tickets": "tickets",
    "turkoyto_ticket_logs": "ticket_logs",
    "turkoyto_config": "config",
    "turkoyto_sessions": "sessions",
    "turkoyto_events": "events",
    # Add more if needed
}

def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    for old, new in RENAME_MAP.items():
        if old in db.list_collection_names():
            print(f"Merging {old} → {new}")
            old_coll = db[old]
            new_coll = db[new]
            count = 0
            for doc in old_coll.find():
                # Only insert if _id does not exist in new collection
                if not new_coll.find_one({'_id': doc['_id']}):
                    new_coll.insert_one(doc)
                    count += 1
            print(f"Inserted {count} new documents into {new}")
            # Drop the old collection
            old_coll.drop()
            print(f"Dropped old collection {old}")
        else:
            print(f"Collection {old} not found, skipping.")

    print("Merge migration complete.")

if __name__ == "__main__":
    main() 