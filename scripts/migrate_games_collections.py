import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def migrate_games_collections():
    """Migrate from 3 separate collections to unified games collection"""
    
    # Connect to MongoDB using .env configuration
    mongo_uri = os.getenv('MONGO_DB', 'mongodb://localhost:27017')
    db_name = os.getenv('DB', 'contro-bot-db')
    
    print(f"Connecting to MongoDB: {mongo_uri}")
    print(f"Database: {db_name}")
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    # Test connection
    try:
        await db.command('ping')
        print("✅ MongoDB connection successful!")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return
    
    print("Starting games collection migration...")
    
    # Get all guilds that have game data
    guild_ids = set()
    
    # From game_logs
    try:
        async for doc in db.game_logs.find({}, {"guild_id": 1}):
            guild_ids.add(doc["guild_id"])
        print(f"Found {len(guild_ids)} guilds in game_logs")
    except Exception as e:
        print(f"Error reading game_logs: {e}")
    
    # From game_stats
    try:
        async for doc in db.game_stats.find({}, {"guild_id": 1}):
            guild_ids.add(doc["guild_id"])
        print(f"Found {len(guild_ids)} total guilds (including game_stats)")
    except Exception as e:
        print(f"Error reading game_stats: {e}")
    
    if not guild_ids:
        print("❌ No guild data found to migrate!")
        return
    
    print(f"Found {len(guild_ids)} guilds with game data")
    
    # Migrate each guild
    migrated_count = 0
    for guild_id in guild_ids:
        print(f"Migrating guild {guild_id}...")
        try:
            # Get existing data
            game_logs_doc = await db.game_logs.find_one({"guild_id": guild_id})
            game_stats_doc = await db.game_stats.find_one({"guild_id": guild_id})
            
            # Create new unified structure
            new_games_doc = {
                "guild_id": guild_id,
                "games": [],
                "enabled": True,
                "last_updated": datetime.utcnow()
            }
            
            # Build a map of games from both collections
            games_map = {}
            
            # Process game_logs data first
            if game_logs_doc and "game_names" in game_logs_doc:
                for game_log in game_logs_doc["game_names"]:
                    game_name = game_log["game_name"]
                    game_name_lower = game_name.lower()
                    games_map[game_name_lower] = {
                        "name": game_name,
                        "name_lower": game_name_lower,
                        "active_players": game_log.get("active_players", []),
                        "player_count": len(game_log.get("active_players", [])),
                        "total_time_played": 0,
                        "first_added": datetime.utcnow(),
                        "last_played": datetime.utcnow(),
                        "historical_players": []
                    }
            # Process game_stats data and merge
            if game_stats_doc and "played_games" in game_stats_doc:
                for game_stat in game_stats_doc["played_games"]:
                    game_name = game_stat["game_name"]
                    game_name_lower = game_name.lower()
                    if game_name_lower in games_map:
                        # Merge with existing data
                        games_map[game_name_lower]["total_time_played"] = game_stat.get("total_time_played", 0)
                        # Merge historical players
                        historical_players = {}
                        for player in game_stat.get("players", []):
                            historical_players[player["member_id"]] = {
                                "member_id": player["member_id"],
                                "member_name": player.get("member_name", "Unknown"),
                                "member_discriminator": "0000",
                                "time_played": player.get("time_played", 0),
                                "last_seen": datetime.utcnow()
                            }
                        # Also add active players to historical
                        for player in games_map[game_name_lower]["active_players"]:
                            member_id = player["member_id"]
                            if member_id in historical_players:
                                # Update time if exists
                                historical_players[member_id]["time_played"] = max(
                                    historical_players[member_id]["time_played"],
                                    player.get("time_played", 0)
                                )
                            else:
                                historical_players[member_id] = player.copy()
                        games_map[game_name_lower]["historical_players"] = list(historical_players.values())
                    else:
                        # Create new entry from stats
                        games_map[game_name_lower] = {
                            "name": game_name,
                            "name_lower": game_name_lower,
                            "total_time_played": game_stat.get("total_time_played", 0),
                            "player_count": 0,
                            "first_added": datetime.utcnow(),
                            "last_played": datetime.utcnow(),
                            "active_players": [],
                            "historical_players": [
                                {
                                    "member_id": player["member_id"],
                                    "member_name": player.get("member_name", "Unknown"),
                                    "member_discriminator": "0000",
                                    "time_played": player.get("time_played", 0),
                                    "last_seen": datetime.utcnow()
                                }
                                for player in game_stat.get("players", [])
                            ]
                        }
            # Convert map to list
            new_games_doc["games"] = list(games_map.values())
            # Insert new document
            if new_games_doc["games"]:  # Only insert if there are games
                await db.games.replace_one(
                    {"guild_id": guild_id},
                    new_games_doc,
                    upsert=True
                )
                migrated_count += 1
                print(f"✅ Migrated {len(new_games_doc['games'])} games for guild {guild_id}")
            else:
                print(f"⚠️ No games found for guild {guild_id}")
        except Exception as e:
            print(f"❌ Error migrating guild {guild_id}: {e}")
            continue
    print(f"\n✅ Migrated {migrated_count} guilds")
    print("Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate_games_collections()) 