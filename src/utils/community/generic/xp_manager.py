import datetime
import logging
import math
import os
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import discord
from discord.ext import commands

logger = logging.getLogger('community.xp_manager')

# Constants
XP_VOICE_PER_MINUTE = 30  # Changed from 2 to 30 XP per minute in voice channels
LEVEL_MULTIPLIER = 1000  # Base XP needed for each level
MAX_WORDS_PER_MESSAGE = 50  # Limit max XP per message to prevent abuse

class XPManager:
    """Manages XP calculations and level progression for Community module"""
    def __init__(self, mongo_db=None):
        self.mongo_db = mongo_db  # This can be async or sync db
        self.xp_cooldowns = {}  # To prevent XP farming
    
    def set_mongo_db(self, mongo_db):
        """Set the MongoDB instance (async or sync)"""
        self.mongo_db = mongo_db
    
    async def get_db(self):
        """Get database instance - async preferred"""
        if self.mongo_db is None:
            # Try to get async database from connection module
            try:
                from src.utils.database.connection import ensure_async_db
                self.mongo_db = await ensure_async_db()
                logger.info("Got async database from connection module")
            except Exception as e:
                logger.error(f"Failed to get async database: {e}")
                return None
        return self.mongo_db
    
    async def add_xp(self, member, xp_amount, activity_type="message", level_up_callback=None):
        """Add XP to a user and handle level ups"""
        if member.bot:
            logger.debug(f"Skipping XP for bot user {member.name}")
            return
        
          # Get async database
        mongo_db = await self.get_db()
        if mongo_db is None:
            logger.error("Failed to get database connection")
            return None
        
        # Convert IDs to both string and integer for flexibility
        user_id_str = str(member.id)
        user_id_int = int(member.id)
        guild_id_str = str(member.guild.id)
        guild_id_int = int(member.guild.id)
        
        logger.debug(f"Adding {xp_amount} XP to {member.name} ({user_id_int}) for {activity_type}")
        
        try:
            # Find user data in users collection (flat structure)
            user_data = None
            
            try:
                # Access the users collection properly
                users_collection = mongo_db.get_collection('users') if hasattr(mongo_db, 'get_collection') else mongo_db['users']
                
                # Try the preferred ID format first (integer)
                user_data = await users_collection.find_one({
                    "user_id": user_id_int, 
                    "guild_id": guild_id_int
                })
                
                # If not found, try string format
                if not user_data:
                    logger.debug(f"User not found with integer ID, trying string ID")
                    user_data = await users_collection.find_one({
                        "user_id": user_id_str, 
                        "guild_id": guild_id_str
                    })
            except Exception as e:
                logger.error(f"Error querying MongoDB for user data: {e}", exc_info=True)
            
            # If still no data found, create new user profile
            if not user_data:
                logger.info(f"Creating new user entry for {member.name} ({user_id_int})")
                user_data = {
                    "user_id": user_id_int,  # Use integer format for consistency
                    "guild_id": guild_id_int,
                    "xp": 0,
                    "level": 0,
                    "next_level_xp": LEVEL_MULTIPLIER,
                    "messages": 0,
                    "voice_minutes": 0,
                    "registered": False,
                    "games": [],
                    "last_active": datetime.now()
                }
                
                # Insert new user document
                try:
                    await users_collection.insert_one(user_data)
                    logger.info(f"Created new user record for {member.name} ({user_id_int})")
                except Exception as e:
                    logger.error(f"Failed to create new user document: {e}", exc_info=True)
                    return None
            
            # Update XP and related stats
            old_xp = user_data.get("xp", 0)
            user_data["xp"] = old_xp + xp_amount
            user_data["last_active"] = datetime.now()
            
            if activity_type == "message":
                user_data["messages"] = user_data.get("messages", 0) + 1
            elif activity_type == "voice":
                user_data["voice_minutes"] = user_data.get("voice_minutes", 0) + (xp_amount / XP_VOICE_PER_MINUTE)
            
            old_level = user_data.get("level", 0)
            current_xp = user_data["xp"]
            next_level_xp = user_data.get("next_level_xp", LEVEL_MULTIPLIER)
            
            # Level up logic
            level_up = False
            if current_xp >= next_level_xp and user_data.get("level", 0) < 100:  # Cap at level 100
                # Level up!
                user_data["level"] = user_data.get("level", 0) + 1
                # Calculate XP needed for next level
                user_data["next_level_xp"] = LEVEL_MULTIPLIER * (user_data["level"] + 1) * 1.5
                level_up = True
                logger.info(f"User {member.name} ({user_id_int}) leveled up to {user_data['level']}!")
            
            # Save the updated user data to the users collection
            try:
                update_result = await users_collection.update_one(
                    {"user_id": user_id_int, "guild_id": guild_id_int},
                    {"$set": user_data},
                    upsert=True
                )
                
                logger.debug(f"Database update result: {update_result}")
            except Exception as e:
                logger.error(f"Failed to update user data: {e}", exc_info=True)
                return None
            
            # If user leveled up and a notification callback is provided, call it
            if level_up and level_up_callback:
                try:
                    await level_up_callback(member, user_data)
                except Exception as e:
                    logger.error(f"Error in level up callback: {e}", exc_info=True)
                    
            logger.info(f"Successfully added {xp_amount} XP to {member.name} ({user_id_int}). New XP: {old_xp} -> {user_data['xp']}")
            return user_data
        except Exception as e:
            logger.error(f"Critical error adding XP: {e}", exc_info=True)
            return None

    async def calculate_message_xp(self, message):
        """Calculate XP from a Discord message based on word count"""
        try:
            # Check if the message has content
            if not message.content:
                logger.debug(f"No content in message from {message.author.name}, skipping XP")
                return 0
                
            words = message.content.split()
            word_count = len(words)
              # Skip very short messages if desired
            if word_count < 2:
                logger.debug(f"Message from {message.author.name} has only {word_count} words, minimal XP")
                return max(1, word_count)  # Ensure at least 1 XP for any valid message
            
            xp_gain = min(word_count, MAX_WORDS_PER_MESSAGE)  # Cap at max words to prevent abuse
            logger.debug(f"Calculated {xp_gain} XP from message with {word_count} words")
            return xp_gain
        
        except Exception as e:
            logger.error(f"Error calculating message XP: {e}", exc_info=True)
            return 0  # Return 0 XP in case of error
    
    async def calculate_voice_xp(self, minutes):
        """Calculate XP from voice channel time"""
        return int(minutes * XP_VOICE_PER_MINUTE)
        
    def is_on_cooldown(self, user_id, now=None):
        """Check if a user is on XP cooldown"""
        if now is None:
            now = datetime.now().timestamp()
        
        if user_id in self.xp_cooldowns:
            last_message = self.xp_cooldowns[user_id]
            if now - last_message < 60:  # 60 seconds cooldown
                return True
        return False
    
    def set_cooldown(self, user_id, now=None):
        """Set XP cooldown for a user"""
        if now is None:
            now = datetime.now().timestamp()
        self.xp_cooldowns[user_id] = now
    
    async def get_user_stats(self, member):
        """Get a user's XP and level"""
        try:
            # Get async database
            mongo_db = await self.get_db()
            if mongo_db is None:
                logger.error("Failed to get database connection")
                return {'level': 0, 'xp': 0, 'next_level_xp': LEVEL_MULTIPLIER, 'found': False}
            
            # Try both string and integer formats for IDs
            user_id_str = str(member.id)
            user_id_int = int(member.id)
            guild_id_str = str(member.guild.id)
            guild_id_int = int(member.guild.id)
            
            logger.info(f"Getting user stats for user ID {user_id_int} in guild {guild_id_int}")

            # Try the users collection with integer IDs first
            user_data = None
            try:
                # Access the users collection properly
                users_collection = mongo_db.get_collection('users') if hasattr(mongo_db, 'get_collection') else mongo_db['users']
                
                # Try async query first with integer IDs
                user_data = await users_collection.find_one({
                    "user_id": user_id_int, 
                    "guild_id": guild_id_int
                })
                logger.info(f"Integer ID query result: {'Found' if user_data else 'Not Found'}")
                
                # If not found, try with string IDs
                if not user_data:
                    user_data = await users_collection.find_one({
                        "user_id": user_id_str, 
                        "guild_id": guild_id_str
                    })
                    logger.info(f"String ID query result: {'Found' if user_data else 'Not Found'}")
            except Exception as e:
                logger.error(f"Error querying database: {e}", exc_info=True)

            # If we found user data (either format), return it
            if user_data:
                logger.info(f"User data found and will be used: {user_data}")
                
                # Calculate rank
                rank = await self.get_user_rank(user_id_int, guild_id_int)
                logger.info(f"Calculated rank: {rank}")
                
                return {
                    'level': user_data.get('level', 0),
                    'xp': user_data.get('xp', 0),
                    'next_level_xp': user_data.get('next_level_xp', LEVEL_MULTIPLIER),
                    'rank': rank,
                    'total_voice_time': user_data.get('voice_minutes', 0),
                    'messages': user_data.get('messages', 0),
                    'games': user_data.get('games', []),
                    'registered': user_data.get('registered', False),
                    'found': True
                }

            # If no data found, create a new user entry and return default values
            logger.warning(f"No data found for user {user_id_int} in guild {guild_id_int}")
            
            # Create a new user entry in users collection
            new_user_data = {
                "user_id": user_id_int,
                "guild_id": guild_id_int,
                "xp": 0,
                "level": 0,
                "next_level_xp": LEVEL_MULTIPLIER,
                "messages": 0,
                "voice_minutes": 0,
                "registered": False,
                "games": [],
                "last_active": datetime.now()
            }
            
            try:
                # Try to create the new user
                await mongo_db['users'].insert_one(new_user_data)
                logger.info(f"Created new user entry for {user_id_int} in guild {guild_id_int}")
            except Exception as e:
                logger.error(f"Failed to create new user: {e}")
            
            return {
                'level': 0,
                'xp': 0, 
                'next_level_xp': LEVEL_MULTIPLIER,
                'rank': 0, 
                'total_voice_time': 0,
                'messages': 0,
                'games': [],
                'registered': False,
                'found': False
            }

        except Exception as e:
            logger.error(f"Critical error in get_user_stats for user {member.id}: {e}", exc_info=True)
            return {'level': 0, 'xp': 0, 'next_level_xp': LEVEL_MULTIPLIER, 'rank': 0, 'total_voice_time': 0, 'found': False}

    async def get_user_rank(self, user_id, guild_id):
        """Get a user's rank in the server based on XP"""
        try:
            # Get async database
            mongo_db = await self.get_db()
            if mongo_db is None:
                logger.error("Failed to get database connection")
                return 0
            
            # Convert to integers for consistency with DB format
            if isinstance(user_id, str):
                user_id = int(user_id)
            if isinstance(guild_id, str):
                guild_id = int(guild_id)
            
            logger.info(f"Calculating rank for user {user_id} in guild {guild_id}")
            
            # Get all users from users collection with integer guild_id
            users = []
            try:
                # Try async approach first
                cursor = mongo_db['users'].find({"guild_id": guild_id}).sort("xp", -1)
                users = await cursor.to_list(length=None)
            except Exception as e:
                logger.error(f"Error getting users for ranking: {e}", exc_info=True)
            
            # If we found users in collection
            if users:
                # Find user's position - check both integer and string IDs
                for i, user in enumerate(users):
                    doc_user_id = user.get("user_id")
                    if doc_user_id == user_id or str(doc_user_id) == str(user_id):
                        rank = i + 1
                        logger.info(f"User rank found: {rank}")
                        return rank
            
            logger.warning(f"User {user_id} not found in rank calculations")
            return 0
        except Exception as e:
            logger.error(f"Error getting user rank: {e}", exc_info=True)
            return 0
    
    async def get_top_users(self, guild_id, limit=10):
        """Get top users by XP"""
        try:
            mongo_db = await self.get_db()
            if mongo_db is None:
                return []
            
            cursor = mongo_db['users'].find({"guild_id": guild_id}).sort("xp", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error getting top users: {e}")
            return []
    
    async def get_top_games(self, guild_id, limit=10):
        """Get most popular games in the community"""
        try:
            mongo_db = await self.get_db()
            if mongo_db is None:
                return []
            
            games = mongo_db.games
            pipeline = [
                {"$match": {"guild_id": guild_id}},
                {"$unwind": "$games"},
                {"$group": {
                    "_id": "$games.name", 
                    "count": {"$sum": "$games.player_count"},
                    "total_time": {"$sum": "$games.total_time_played"}
                }},
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            
            cursor = games.aggregate(pipeline)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error getting top games: {e}")
            return []
    
    async def register_user(self, member, games):
        """Register a user with their games"""
        # Convert IDs to strings for consistency
        user_id = str(member.id)
        guild_id = str(member.guild.id)
        
        # New format user data
        user_data = {
            "user_id": user_id,
            "guild_id": guild_id,
            "username": member.name,
            "games": games,
            "level": 0,
            "xp": 0,
            "messages": 0,
            "voice_minutes": 0,
            "registered": True,
            "last_active": datetime.now()
        }
        
        try:
            # Update in new collection
            try:
                await self.mongo_db['users'].update_one(
                    {"user_id": user_id, "guild_id": guild_id},
                    {"$set": user_data},
                    upsert=True
                )
            except (TypeError, AttributeError):
                self.mongo_db['users'].update_one(
                    {"user_id": user_id, "guild_id": guild_id},
                    {"$set": user_data},
                    upsert=True
                )
            
            # Also update in legacy collection for backward compatibility
            try:
                # Check if user exists in legacy collection
                legacy_user = None
                try:
                    legacy_user = await self.mongo_db['users'].find_one({"user_id": user_id})
                except (TypeError, AttributeError):
                    legacy_user = self.mongo_db['users'].find_one({"user_id": user_id})
                
                if legacy_user:
                    # Update existing user
                    try:
                        await self.mongo_db['users'].update_one(
                            {"user_id": user_id},
                            {"$set": {f"guilds.{guild_id}": {
                                "username": member.name,
                                "games": games,
                                "level": 0,
                                "xp": 0,
                                "messages": 0,
                                "voice_minutes": 0,
                                "registered": True,
                                "last_active": datetime.now()
                            }}}
                        )
                    except (TypeError, AttributeError):
                        self.mongo_db['users'].update_one(
                            {"user_id": user_id},
                            {"$set": {f"guilds.{guild_id}": {
                                "username": member.name,
                                "games": games,
                                "level": 0,
                                "xp": 0,
                                "messages": 0,
                                "voice_minutes": 0,
                                "registered": True,
                                "last_active": datetime.now()
                            }}}
                        )
                else:
                    # Create new user in legacy format
                    legacy_data = {
                        "user_id": user_id,
                        "guilds": {
                            guild_id: {
                                "username": member.name,
                                "games": games,
                                "level": 0,
                                "xp": 0,
                                "messages": 0,
                                "voice_minutes": 0,
                                "registered": True,
                                "last_active": datetime.now()
                            }
                        }
                    }
                    try:
                        await self.mongo_db['users'].insert_one(legacy_data)
                    except (TypeError, AttributeError):
                        self.mongo_db['users'].insert_one(legacy_data)
            except Exception as e:
                logger.warning(f"Failed to update legacy format during registration: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False
    
    async def prepare_level_card_data(self, member, guild=None):
        """
        Prepares all data needed for level card rendering
        
        Args:
            member (discord.Member): The member to get data for
            guild (discord.Guild, optional): The guild context
            
        Returns:
            dict: A dictionary with all user data needed for card rendering
        """
        try:
            if guild is None and hasattr(member, 'guild'):
                guild = member.guild
                
            if guild is None:
                logger.error("Guild is required for level card data preparation")
                return None
                
            # Convert IDs to integers for database lookup
            user_id_int = int(member.id)
            guild_id_int = int(guild.id)
            
            logger.info(f"Preparing level card data for user {member.name} ({user_id_int}) in guild {guild_id_int}")
            
            # Get user stats from database
            user_data = await self.get_user_stats(member)
            
            # If data wasn't found, we might need to create it
            if not user_data or not user_data.get('found', False):
                logger.warning(f"No user data found, creating new entry for {user_id_int}")
                
                # Check if async MongoDB is available
                is_async = False
                try:
                    is_async = hasattr(self.mongo_db['users'].insert_one, '__await__')
                except Exception:
                    is_async = False
                
                # Create a new user document
                new_user = {
                    "user_id": user_id_int,
                    "guild_id": guild_id_int,
                    "xp": 0,
                    "level": 0,
                    "next_level_xp": 1000,
                    "messages": 0,
                    "voice_minutes": 0,
                    "registered": False,
                    "games": [],
                    "last_active": datetime.now()
                }
                
                # Insert the new document
                try:
                    if is_async:
                        await self.mongo_db['users'].insert_one(new_user)
                    else:
                        self.mongo_db['users'].insert_one(new_user)
                    
                    # Set the user data
                    user_data = {
                        'level': 0,
                        'xp': 0,
                        'next_level_xp': 1000,
                        'rank': 0,
                        'total_voice_time': 0,
                        'messages': 0,
                        'games': [],
                        'registered': False,
                        'found': True
                    }
                except Exception as e:
                    logger.error(f"Failed to create new user: {e}", exc_info=True)
                    user_data = None
            
            # If we have user data, prepare it for rendering
            if user_data:
                # Calculate rank if not already included
                if 'rank' not in user_data or user_data['rank'] is None or user_data['rank'] == 0:
                    rank = await self.get_user_rank(user_id_int, guild_id_int)
                    user_data['rank'] = rank if rank > 0 else 0
                
                # Ensure all required fields are present
                if "level" not in user_data:
                    user_data["level"] = 0
                if "xp" not in user_data:
                    user_data["xp"] = 0
                if "next_level_xp" not in user_data:
                    user_data["next_level_xp"] = LEVEL_MULTIPLIER
                
                logger.info(f"Level card data prepared: Level={user_data.get('level')}, XP={user_data.get('xp')}, Rank={user_data.get('rank')}")
                return user_data
            else:
                # Return fallback data
                logger.warning(f"Using fallback data for user {user_id_int}")
                fallback_data = {
                    'level': 0,
                    'xp': 0,
                    'next_level_xp': 1000,
                    'rank': 0,
                    'total_voice_time': 0,
                    'messages': 0,
                    'games': [],
                    'registered': False,
                    'found': False
                }
                return fallback_data
        except Exception as e:
            logger.error(f"Error preparing level card data: {e}", exc_info=True)
            # Return minimal fallback data
            return {
                'level': 0,
                'xp': 0,
                'next_level_xp': LEVEL_MULTIPLIER,
                'rank': 0,
                'found': False
            }
    
    async def create_and_render_level_card(self, bot, member, guild=None, output_path=None):
        """
        Create a level card with all necessary data lookup and rendering
        
        Args:
            bot: Discord bot instance
            member (discord.Member): Discord member to create card for
            guild (discord.Guild, optional): Guild context
            output_path (str, optional): Custom path to save the card
            
        Returns:
            str: Path to the rendered level card
        """
        try:
            # Import here to avoid circular imports
            from .card_renderer import create_level_card
            
            # Prepare data for the card
            user_data = await self.prepare_level_card_data(member, guild)
            
            if guild is None and hasattr(member, 'guild'):
                guild = member.guild
            
            # Generate temp file path if not provided
            if output_path is None:
                temp_dir = os.path.join("data", "Temp")
                os.makedirs(temp_dir, exist_ok=True)
                output_filename = f"level_card_{member.id}_{int(time.time())}.png"
                output_path = os.path.join(temp_dir, output_filename)
            
            # Create the level card
            card_path = await create_level_card(
                bot,
                member,
                user_data,
                guild=guild,
                mongo_db=self.mongo_db,
                output_path=output_path
            )
            
            return card_path
        except Exception as e:
            logger.error(f"Error creating level card: {e}", exc_info=True)
            return None
