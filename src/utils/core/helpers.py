"""Helper functions for various bot functionality."""
import discord
from discord.ext import commands
import asyncio
import logging
from typing import Union, Dict, Any, Optional
import re
import json
import random
import string
import aiohttp
from datetime import datetime, timedelta

# Function to check if context is from a command or interaction
async def check_if_ctx_or_interaction(ctx_or_interaction):
    """
    Determines if the input is a Context object or an Interaction.
    Returns appropriate methods for responding based on the type.
    """
    if isinstance(ctx_or_interaction, commands.Context):
        send = ctx_or_interaction.send
        guild = ctx_or_interaction.guild
        author = ctx_or_interaction.author
        channel = ctx_or_interaction.channel
    else:  # Interaction
        send = ctx_or_interaction.response.send_message
        guild = ctx_or_interaction.guild
        author = ctx_or_interaction.user
        channel = ctx_or_interaction.channel
    
    return send, guild, author, channel

# Function used in register.py
def find_guild_in_register_collection(mongo_db, guild_id):
    """Find guild record in register collection."""
    return mongo_db['register'].find_one({"guild_id": guild_id})

# Common utility functions that might have been in the utils module
def check_video_url(message_content):
    """Check if a message content contains a video URL."""
    video_platforms = [
        "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", "twitch.tv",
        "streamable.com", "tiktok.com", "instagram.com/reel", "facebook.com/watch",
        "twitter.com/i/status", "vm.tiktok.com"
    ]
    message_content = message_content.strip().lower()
    for platform in video_platforms:
        if platform in message_content:
            return True
    return False

# Additional helper functions that might be needed
def is_url(text):
    """Check if text is a URL."""
    url_prefixes = ["http://", "https://", "www."]
    return any(text.startswith(prefix) for prefix in url_prefixes)

def contains_invite_link(text):
    """Check if text contains a Discord invite link."""
    invite_keywords = ["discord.gg/", "discord.com/invite/"]
    return any(keyword in text.lower() for keyword in invite_keywords)

def truncate_string(text, max_length=2000):
    """Truncate a string to a maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def is_owner(ctx):
    """Check if the user is the bot owner or server owner."""
    return ctx.author.id == ctx.bot.owner_id or ctx.author == ctx.guild.owner

def has_permissions(**perms):
    """Check if the user has the required permissions."""
    def predicate(ctx):
        if ctx.author.id == ctx.bot.owner_id:
            return True
        return ctx.author.guild_permissions >= discord.Permissions(**perms)
    return commands.check(predicate)

def is_feature_enabled(guild_id: int, feature: str, mongo_db=None) -> bool:
    """
    Check if a feature is enabled for a guild.
    
    Args:
        guild_id: The guild ID to check
        feature: The feature name to check
        mongo_db: MongoDB connection (optional, will initialize if not provided)
    
    Returns:
        bool: True if feature is enabled, False otherwise
    """
    # Default feature states
    default_features = {
        "welcome_system": True,
        "leveling_system": True,
        "starboard_system": False,
        "auto_moderation": True,
        "logging_system": True,
        "ticket_system": True,
        "community_features": True
    }
    
    try:
        if mongo_db is None:
            from src.utils.database import initialize_mongodb
            mongo_db = initialize_mongodb()
        
        # Check if mongo_db is still None after initialization
        if mongo_db is None:
            logging.warning("MongoDB connection not available, using default feature states")
            return default_features.get(feature, True)
        
        # Check if feature_toggles collection exists
        if not hasattr(mongo_db, 'feature_toggles') or mongo_db.feature_toggles is None:
            logging.warning("feature_toggles collection not available, using default feature states")
            return default_features.get(feature, True)
        
        features = mongo_db.feature_toggles.find_one({"guild_id": guild_id}) or {}
        return features.get(feature, default_features.get(feature, True))
    except Exception as e:
        logging.error(f"Error checking feature toggle: {e}")
        return default_features.get(feature, True)

def feature_required(feature_name: str):
    """
    Decorator to require a feature to be enabled before running a command.
    
    Args:
        feature_name: The name of the feature required
    """
    def decorator(func):
        async def wrapper(self, ctx, *args, **kwargs):
            if hasattr(ctx, 'guild') and ctx.guild:
                if not is_feature_enabled(ctx.guild.id, feature_name):
                    from src.utils.core.formatting import create_embed
                    
                    embed = create_embed(
                        description=f"❌ The {feature_name.replace('_', ' ').title()} feature is disabled on this server.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed, ephemeral=True)
                    return
            
            return await func(self, ctx, *args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator

async def get_guild_features(guild_id: int, mongo_db=None) -> Dict[str, bool]:
    """
    Get all feature states for a guild.
    
    Args:
        guild_id: The guild ID
        mongo_db: MongoDB connection (optional)
    
    Returns:
        dict: Dictionary of feature names and their states
    """
    default_features = {
        "welcome_system": True,
        "leveling_system": True,
        "starboard_system": False,
        "auto_moderation": True,
        "logging_system": True,
        "ticket_system": True,
        "community_features": True
    }
    
    try:
        if mongo_db is None:
            from src.utils.database import initialize_mongodb
            mongo_db = initialize_mongodb()
        
        # Check if mongo_db is still None after initialization
        if mongo_db is None:
            logging.warning("MongoDB connection not available, using default feature states")
            return default_features
        
        # Check if feature_toggles collection exists
        if not hasattr(mongo_db, 'feature_toggles') or mongo_db.feature_toggles is None:
            logging.warning("feature_toggles collection not available, using default feature states")
            return default_features
        
        features = mongo_db.feature_toggles.find_one({"guild_id": guild_id}) or {}
        
        # Merge with defaults
        result = default_features.copy()
        result.update(features)
        
        # Remove MongoDB internal fields
        result.pop("_id", None)
        result.pop("guild_id", None)
        
        return result
    except Exception as e:
        logging.error(f"Error getting guild features: {e}")
        return default_features

def format_time(seconds: int) -> str:
    """Format seconds into a human-readable time string."""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            return f"{minutes} minutes"
        return f"{minutes} minutes {remaining_seconds} seconds"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes == 0:
            return f"{hours} hours"
        return f"{hours} hours {remaining_minutes} minutes"

# Add other helper functions as needed
