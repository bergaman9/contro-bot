import logging
from typing import List, Dict, Optional
import asyncio
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks
import json

from src.utils.database.connection import initialize_mongodb
from src.utils.core.formatting import create_embed
from src.utils.core.class_utils import Paginator
from src.utils.core.db import get_document, get_documents, update_document

# Set up logging
logger = logging.getLogger('game_stats')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='logs/game_stats.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

class GameStats(commands.Cog):
    """
    Tracks game activity statistics across the server
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.mongodb = None
        self.games_cache = {}  # Unified cache for games collection
        self.last_activity_check = {}  # Track when we last checked a user's activity
        self.init_task = asyncio.create_task(self.initialize())
        
        # Increased intervals to reduce load
        self.update_interval = 300  # seconds (5 minutes)
        self.cleanup_interval = 60  # minutes (1 hour)
        self.cache_ttl = 300  # seconds (5 minutes)
        self.last_cache_cleanup = datetime.now()
    
    async def initialize(self):
        """Initialize the database connection asynchronously"""
        try:
            self.mongodb = initialize_mongodb()
            if self.mongodb is not None:  # Proper way to check MongoDB connection
                # Start background tasks after database is initialized
                self.update_games.start()
                self.clean_up_database_for_guild.start()
                logger.info("GameStats cog initialized successfully")
            else:
                logger.error("MongoDB initialization returned None")
        except Exception as e:
            logger.error(f"Error initializing GameStats cog: {e}")

    async def get_cached_data(self, cache_dict, key, fetch_func, ttl=None):
        """Generic function to get data from cache or fetch if not available"""
        ttl = ttl or self.cache_ttl
        now = datetime.now()
        
        # Clean old cache entries periodically
        if (now - self.last_cache_cleanup).total_seconds() > 600:  # 10 minutes
            self._cleanup_cache(cache_dict)
            self.last_cache_cleanup = now
        
        # Check if data is in cache and not expired
        if key in cache_dict and (now - cache_dict[key]['timestamp']).total_seconds() < ttl:
            return cache_dict[key]['data']
            
        # Otherwise, fetch new data
        data = await fetch_func()
        cache_dict[key] = {
            'data': data,
            'timestamp': now
        }
        return data

    def _cleanup_cache(self, cache_dict):
        """Remove expired entries from cache"""
        now = datetime.now()
        expired_keys = [
            key for key, value in cache_dict.items() 
            if (now - value['timestamp']).total_seconds() > self.cache_ttl
        ]
        for key in expired_keys:
            cache_dict.pop(key)

    async def get_guild_games_data(self, guild_id):
        """Get unified games data for a guild"""
        games_key = f"guild_games_{guild_id}"
        
        async def fetch_guild_games():
            if not self.mongodb:
                return None
            games = self.mongodb["games"]
            return await games.find_one({"guild_id": guild_id})
        
        return await self.get_cached_data(self.games_cache, games_key, fetch_guild_games)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handler for when a member leaves the server"""
        if self.mongodb is None:
            return  # Skip if not initialized
            
        try:
            await self.remove_player_from_games(member.guild, member)
        except Exception as e:
            logger.error(f"Error in on_member_remove for {member}: {e}")

    @tasks.loop(seconds=300, reconnect=True)  # 5 minutes
    async def update_games(self):
        """Update games data for all guilds"""
        if self.mongodb is None:
            return
        
        try:
            for guild in self.bot.guilds:
                # Check if bot has permission to view member activities
                # view_activity permission was removed in newer Discord.py versions
                # Instead, we'll check if we can access member activities
                try:
                    # Try to access a member's activity to test permissions
                    test_member = next((m for m in guild.members if not m.bot), None)
                    if test_member and not hasattr(test_member, 'activity'):
                        continue
                except Exception:
                    # If we can't access member activities, skip this guild
                    continue
                
                guild_games_key = f"guild_games_{guild.id}"
                current_data = await self.get_guild_games_data(guild.id)
                
                # Get current active games from Discord
                current_games = {}
                for member in guild.members:
                    if member.bot:
                        continue
                        
                    if member.activity and member.activity.type == discord.ActivityType.playing:
                        game_name = member.activity.name
                        if not game_name:
                            continue
                            
                        game_name_lower = game_name.lower()
                        
                        if game_name_lower not in current_games:
                            current_games[game_name_lower] = {
                                "name": game_name,
                                "name_lower": game_name_lower,
                                "active_players": [],
                                "total_time_played": 0,
                                "player_count": 0,
                                "first_added": datetime.utcnow(),
                                "last_played": datetime.utcnow()
                            }
                        
                        # Add/update active player
                        player_data = {
                            "member_id": member.id,
                            "member_name": member.name,
                            "member_discriminator": str(member.discriminator),
                            "time_played": 0,  # Will be calculated
                            "last_seen": datetime.utcnow()
                        }
                        
                        # Update or add player
                        existing_player = next(
                            (p for p in current_games[game_name_lower]["active_players"] 
                             if p["member_id"] == member.id), None
                        )
                        if existing_player:
                            existing_player.update(player_data)
                        else:
                            current_games[game_name_lower]["active_players"].append(player_data)
                            current_games[game_name_lower]["player_count"] += 1
                
                # Update database
                await self.update_games_in_db(guild, current_games)
                
                # Clear cache
                self.games_cache.pop(guild_games_key, None)
                
        except Exception as e:
            logger.error(f"Error in update_games: {e}")

    async def update_games_in_db(self, guild, current_games):
        """Update games data in database"""
        if not self.mongodb:
            return
            
        try:
            games = self.mongodb["games"]
            guild_data = await games.find_one({"guild_id": guild.id})
            
            if not guild_data:
                # Create new guild games document
                guild_data = {
                    "guild_id": guild.id,
                    "games": [],
                    "enabled": True,
                    "last_updated": datetime.utcnow()
                }
            
            # Update existing games and add new ones
            updated_games = []
            existing_games = {g["name_lower"]: g for g in guild_data.get("games", [])}
            
            for game_name_lower, current_game in current_games.items():
                if game_name_lower in existing_games:
                    # Update existing game
                    existing_game = existing_games[game_name_lower]
                    
                    # Calculate time played for existing players
                    for active_player in current_game["active_players"]:
                        # Find historical data for this player
                        historical_player = next(
                            (p for p in existing_game.get("historical_players", [])
                             if p["member_id"] == active_player["member_id"]), None
                        )
                        
                        if historical_player:
                            active_player["time_played"] = historical_player.get("time_played", 0) + 5  # Add 5 minutes
                        else:
                            active_player["time_played"] = 5  # New player, start with 5 minutes
                    
                    # Update total time played
                    total_time = sum(p["time_played"] for p in current_game["active_players"])
                    
                    existing_game.update({
                        "active_players": current_game["active_players"],
                        "player_count": len(current_game["active_players"]),
                        "last_played": current_game["last_played"],
                        "total_time_played": total_time,
                        "historical_players": self._merge_historical_players(
                            existing_game.get("historical_players", []),
                            current_game["active_players"]
                        )
                    })
                    updated_games.append(existing_game)
                else:
                    # Add new game
                    current_game["historical_players"] = current_game["active_players"].copy()
                    current_game["total_time_played"] = len(current_game["active_players"]) * 5  # Initial 5 minutes per player
                    updated_games.append(current_game)
            
            # Add inactive games (not currently being played)
            for game_name_lower, existing_game in existing_games.items():
                if game_name_lower not in current_games:
                    existing_game["active_players"] = []
                    existing_game["player_count"] = 0
                    updated_games.append(existing_game)
            
            # Update database
            await games.update_one(
                {"guild_id": guild.id},
                {
                    "$set": {
                        "games": updated_games,
                        "last_updated": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error updating games in DB for {guild}: {e}")

    def _merge_historical_players(self, historical, active):
        """Merge historical player data with active players"""
        merged = {p["member_id"]: p for p in historical}
        
        for player in active:
            if player["member_id"] in merged:
                # Update existing historical data
                merged[player["member_id"]].update({
                    "member_name": player["member_name"],
                    "member_discriminator": player["member_discriminator"],
                    "time_played": player["time_played"],
                    "last_seen": player["last_seen"]
                })
            else:
                # Add new player to historical
                merged[player["member_id"]] = player.copy()
        
        return list(merged.values())

    @tasks.loop(minutes=60, reconnect=True)  # 1 hour
    async def clean_up_database_for_guild(self):
        """Periodically clean up the database to remove stale data"""
        if self.mongodb is None:
            return
            
        try:
            games_collection = self.mongodb["games"]
            
            for guild in self.bot.guilds:
                guild_data = await games_collection.find_one({"guild_id": guild.id})
                if not guild_data:
                    continue

                # Get current member IDs from guild
                current_member_ids = {member.id for member in guild.members}
                updated_games = []
                modified = False
                
                for game in guild_data.get("games", []):
                    # Filter out players who are no longer in the guild
                    active_players = [
                        player for player in game.get("active_players", []) 
                        if player["member_id"] in current_member_ids
                    ]
                    
                    historical_players = [
                        player for player in game.get("historical_players", [])
                        if player["member_id"] in current_member_ids
                    ]
                    
                    # Check if we removed any players
                    if (len(active_players) != len(game.get("active_players", [])) or
                        len(historical_players) != len(game.get("historical_players", []))):
                        modified = True
                    
                    # Update game data
                    game["active_players"] = active_players
                    game["historical_players"] = historical_players
                    game["player_count"] = len(active_players)
                    
                    # Only keep games that have historical data
                    if historical_players:
                        updated_games.append(game)
                    else:
                        modified = True

                # Only update if there are changes
                if modified:
                    await games_collection.update_one(
                        {"guild_id": guild.id}, 
                        {"$set": {"games": updated_games, "last_updated": datetime.utcnow()}}
                    )
                    
                    # Invalidate cache
                    self.games_cache.pop(f"guild_games_{guild.id}", None)
                    
        except Exception as e:
            logger.error(f"Error in clean_up_database_for_guild: {e}")

    async def remove_player_from_games(self, guild, member):
        """Remove a member from all games when they leave"""
        if self.mongodb is None:
            return
            
        try:
            games_collection = self.mongodb["games"]
            guild_data = await games_collection.find_one({"guild_id": guild.id})
            
            if not guild_data:
                return
                
            modified = False
            updated_games = []
            
            for game in guild_data.get("games", []):
                # Remove from active players
                active_players = [
                    p for p in game.get("active_players", [])
                    if p["member_id"] != member.id
                ]
                
                # Remove from historical players
                historical_players = [
                    p for p in game.get("historical_players", [])
                    if p["member_id"] != member.id
                ]
                
                if (len(active_players) != len(game.get("active_players", [])) or
                    len(historical_players) != len(game.get("historical_players", []))):
                    modified = True
                
                game["active_players"] = active_players
                game["historical_players"] = historical_players
                game["player_count"] = len(active_players)
                
                # Keep game if it still has historical data
                if historical_players:
                    updated_games.append(game)
                else:
                    modified = True
            
            if modified:
                await games_collection.update_one(
                    {"guild_id": guild.id},
                    {"$set": {"games": updated_games, "last_updated": datetime.utcnow()}}
                )
                
                # Invalidate cache
                self.games_cache.pop(f"guild_games_{guild.id}", None)
                
        except Exception as e:
            logger.error(f"Error in remove_player_from_games for {member}: {e}")

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        # Stop background tasks
        if self.update_games.is_running():
            self.update_games.cancel()
            
        if self.clean_up_database_for_guild.is_running():
            self.clean_up_database_for_guild.cancel()
            
        # Cancel initialization if still pending
        if hasattr(self, 'init_task') and not self.init_task.done():
            self.init_task.cancel()
            
        # Clear caches
        self.games_cache.clear()
        self.last_activity_check.clear()
            
        logger.info("GameStats cog unloaded")

async def setup(bot):
    await bot.add_cog(GameStats(bot))
