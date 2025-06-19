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
        self.game_stats_cache = {}  # Cache for game stats to reduce DB queries
        self.game_logs_cache = {}   # Cache for game logs
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
                self.update_game_activities.start()
                self.update_game_logs.start()
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

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handler for when a member leaves the server"""
        if self.mongodb is None:
            return  # Skip if not initialized
            
        try:
            await self.remove_game_logs_in_db(member.guild, member)
        except Exception as e:
            logger.error(f"Error in on_member_remove for {member}: {e}")

    @tasks.loop(seconds=300, reconnect=True)  # Increased to 5 minutes
    async def update_game_activities(self):
        """Update game activity statistics periodically"""
        if self.mongodb is None:
            return  # Skip if not initialized
            
        try:
            current_time = discord.utils.utcnow().timestamp()
            bulk_operations = []
            
            for guild in self.bot.guilds:
                # Process only a subset of members each run to distribute load
                for member in guild.members:
                    # Only check users if enough time has passed since last check
                    last_check = self.last_activity_check.get(member.id, 0)
                    if current_time - last_check < self.update_interval/2:
                        continue
                        
                    self.last_activity_check[member.id] = current_time
                    
                    # Only process members actually playing games
                    if (not member.bot and member.activity and 
                            member.activity.type == discord.ActivityType.playing):
                        game_name = member.activity.name
                        if game_name:
                            # Queue the update for batch processing
                            bulk_operations.append((guild.id, game_name, member.id))
            
            # Process all updates in a single batch if there are any
            if bulk_operations:
                await self.batch_update_games_in_db(bulk_operations)
                
        except Exception as e:
            logger.error(f"Error in update_game_activities: {e}")

    @tasks.loop(seconds=300, reconnect=True)  # Increased to 5 minutes
    async def update_game_logs(self):
        """Update current game playing logs"""
        if self.mongodb is None:
            return  # Skip if not initialized
            
        try:
            # Process in batches to avoid rate limits
            for guild in self.bot.guilds:
                players_to_add = []
                players_to_remove = []
                
                # Get current member IDs in guild - do this once to avoid repeated calls
                current_member_ids = {member.id for member in guild.members if not member.bot}
                
                # Check the cached guild log first
                guild_log_key = f"guild_log_{guild.id}"
                
                async def fetch_guild_log():
                    if not self.mongodb:
                        return None
                    game_logs = self.mongodb["game_logs"]
                    return await game_logs.find_one({"guild_id": guild.id})
                
                guild_log = await self.get_cached_data(self.game_logs_cache, guild_log_key, fetch_guild_log)
                
                # Track existing active players from DB to identify who needs to be removed
                existing_active_members = set()
                if guild_log:
                    for game in guild_log.get("game_names", []):
                        for player in game.get("active_players", []):
                            existing_active_members.add(player.get("member_id"))
                
                # Find members who are playing games
                active_players = {}  # Keep track of currently active players
                for member in guild.members:
                    if (not member.bot and member.activity and 
                            member.activity.type == discord.ActivityType.playing):
                        game_name = member.activity.name
                        if game_name:
                            players_to_add.append({
                                "guild_id": guild.id,
                                "game_name": game_name,
                                "member_id": member.id,
                                "member_name": member.name,
                                "member_discriminator": str(member.discriminator)
                            })
                            active_players[member.id] = True
                
                # Find members who need to be removed (not playing anymore)
                members_to_remove = existing_active_members - set(active_players.keys())
                for member_id in members_to_remove:
                    if member_id in current_member_ids:  # Make sure they're still in the guild
                        member = guild.get_member(member_id)
                        if member:
                            players_to_remove.append((guild, member))
                
                # Process additions in one batch (only if there are any)
                if players_to_add:
                    await self.batch_update_game_logs_in_db(players_to_add)
                
                # Process removals in another batch (only if there are any)
                if players_to_remove:
                    await self.batch_remove_game_logs_in_db(players_to_remove)
                    
                # Invalidate cache after updates
                self.game_logs_cache.pop(guild_log_key, None)
                    
                # Brief pause to avoid hitting rate limits
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in update_game_logs: {e}")

    @tasks.loop(minutes=60, reconnect=True)  # Increased to 1 hour
    async def clean_up_database_for_guild(self):
        """Periodically clean up the database to remove stale data"""
        if self.mongodb is None:
            return  # Skip if not initialized
            
        try:
            for guild in self.bot.guilds:
                game_logs = self.mongodb["game_logs"]
                guild_log = await game_logs.find_one({"guild_id": guild.id})

                if not guild_log:
                    continue

                # Get current member IDs from guild - only do this once
                current_member_ids = {member.id for member in guild.members}
                updated_game_names = []
                
                for game in guild_log.get("game_names", []):
                    # Filter out players who are no longer in the guild
                    active_players = [player for player in game.get("active_players", []) 
                                      if player["member_id"] in current_member_ids]
                    
                    # Only keep games that still have active players
                    if active_players:
                        game["active_players"] = active_players
                        updated_game_names.append(game)

                # Only update if there are changes
                if len(updated_game_names) != len(guild_log.get("game_names", [])):
                    await game_logs.update_one(
                        {"guild_id": guild.id}, 
                        {"$set": {"game_names": updated_game_names}}
                    )
                    
                    # Invalidate cache
                    self.game_logs_cache.pop(f"guild_log_{guild.id}", None)
                    
        except Exception as e:
            logger.error(f"Error in clean_up_database_for_guild: {e}")

    async def remove_game_logs_in_db(self, guild, member):
        """Remove a member from all game logs"""
        if self.mongodb is None:
            return  # Skip if not initialized
            
        try:
            # Check cache first
            guild_log_key = f"guild_log_{guild.id}"
            
            async def fetch_guild_log():
                game_logs = self.mongodb["game_logs"]
                return await game_logs.find_one({"guild_id": guild.id})
                
            guild_log = await self.get_cached_data(self.game_logs_cache, guild_log_key, fetch_guild_log)
            
            if guild_log:
                updated_game_names = []
                modified = False
                
                for game in guild_log.get("game_names", []):
                    # Filter out the member from active_players
                    active_players = [player for player in game.get("active_players", [])
                                     if player.get("member_id") != member.id]
                    
                    # Only keep games that still have active players
                    if active_players:
                        if len(active_players) != len(game.get("active_players", [])):
                            modified = True
                        game["active_players"] = active_players
                        updated_game_names.append(game)
                    else:
                        modified = True
                
                # Only update if there were changes
                if modified:
                    # Update the database with the filtered game list
                    game_logs = self.mongodb["game_logs"]
                    await game_logs.update_one(
                        {"guild_id": guild.id}, 
                        {"$set": {"game_names": updated_game_names}}
                    )
                    
                    # Invalidate cache
                    self.game_logs_cache.pop(guild_log_key, None)
                
        except Exception as e:
            logger.error(f"Error in remove_game_logs_in_db for {member}: {e}")
            
    async def batch_update_games_in_db(self, operations):
        """Update game statistics in batches"""
        if self.mongodb is None:
            return
            
        try:
            game_stats = self.mongodb["game_stats"]
            updates_by_guild = {}
            
            # Group operations by guild
            for guild_id, game_name, member_id in operations:
                if guild_id not in updates_by_guild:
                    updates_by_guild[guild_id] = {}
                    
                if game_name not in updates_by_guild[guild_id]:
                    updates_by_guild[guild_id][game_name] = set()
                    
                updates_by_guild[guild_id][game_name].add(member_id)
            
            # Process each guild's updates
            for guild_id, games in updates_by_guild.items():
                # Check cache first
                guild_stats_key = f"guild_stats_{guild_id}"
                
                async def fetch_guild_stats():
                    guild_data = await game_stats.find_one({"guild_id": guild_id})
                    if not guild_data:
                        await game_stats.insert_one({
                            "guild_id": guild_id, 
                            "played_games": []
                        })
                        return await game_stats.find_one({"guild_id": guild_id})
                    return guild_data
                
                guild_data = await self.get_cached_data(self.game_stats_cache, guild_stats_key, fetch_guild_stats)
                
                played_games = guild_data.get("played_games", [])
                modified = False
                
                # Update each game
                for game_name, member_ids in games.items():
                    game_found = False
                    
                    # Look for existing game entry
                    for game in played_games:
                        if game["game_name"] == game_name:
                            game_found = True
                            game["total_time_played"] += 1
                            
                            # Update each member's play time
                            for member_id in member_ids:
                                player_found = False
                                for player in game["players"]:
                                    if player["member_id"] == member_id:
                                        player["time_played"] += 1
                                        player_found = True
                                        break
                                        
                                if not player_found:
                                    game["players"].append({
                                        "member_id": member_id, 
                                        "time_played": 1
                                    })
                                    
                            modified = True
                            break
                    
                    # Create new game entry if not found
                    if not game_found:
                        played_games.append({
                            "game_name": game_name,
                            "total_time_played": 1,
                            "players": [
                                {"member_id": member_id, "time_played": 1} 
                                for member_id in member_ids
                            ]
                        })
                        modified = True
                
                # Update database if changes were made
                if modified:
                    await game_stats.update_one(
                        {"guild_id": guild_id}, 
                        {"$set": {"played_games": played_games}}
                    )
                    
                    # Invalidate cache
                    self.game_stats_cache.pop(guild_stats_key, None)
                    
        except Exception as e:
            logger.error(f"Error in batch_update_games_in_db: {e}")

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        # Stop background tasks
        if self.update_game_activities.is_running():
            self.update_game_activities.cancel()
            
        if self.update_game_logs.is_running():
            self.update_game_logs.cancel()
            
        if self.clean_up_database_for_guild.is_running():
            self.clean_up_database_for_guild.cancel()
            
        # Cancel initialization if still pending
        if hasattr(self, 'init_task') and not self.init_task.done():
            self.init_task.cancel()
            
        # Clear caches
        self.game_stats_cache.clear()
        self.game_logs_cache.clear()
        self.last_activity_check.clear()
            
        logger.info("GameStats cog unloaded")

async def setup(bot):
    await bot.add_cog(GameStats(bot))
