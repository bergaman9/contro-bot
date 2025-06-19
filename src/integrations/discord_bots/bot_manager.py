"""
Discord Bot Invitation and Management System
Manages invitations and configurations for popular Discord bots
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from enum import Enum
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

@dataclass
class BotConfig:
    """Configuration for a Discord bot"""
    id: str
    name: str
    description: str
    permissions: int
    scopes: List[str]
    website: str
    category: str
    features: List[str]
    setup_instructions: str
    recommended_channels: List[str]

class BotCategory(Enum):
    """Categories for Discord bots"""
    MODERATION = "moderation"
    MUSIC = "music"
    UTILITY = "utility"
    FUN = "fun"
    ECONOMY = "economy"
    LEVELING = "leveling"
    LOGGING = "logging"
    TICKETS = "tickets"
    GAMES = "games"
    AI = "ai"

class BotManager:
    """Manages Discord bot invitations and configurations"""
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.popular_bots = self._load_popular_bots()
    
    def _load_popular_bots(self) -> Dict[str, BotConfig]:
        """Load configurations for popular Discord bots"""
        return {
            # Moderation Bots
            "carl": BotConfig(
                id="235148962103951360",
                name="Carl-bot",
                description="Advanced automod, logging, reaction roles, and custom commands",
                permissions=1543503103,  # Comprehensive moderation permissions
                scopes=["bot", "applications.commands"],
                website="https://carl-bot.io",
                category=BotCategory.MODERATION.value,
                features=[
                    "Advanced automoderation",
                    "Reaction roles",
                    "Custom commands",
                    "Logging system",
                    "Tickets",
                    "Giveaways"
                ],
                setup_instructions="1. Configure automod in dashboard\n2. Set up logging channels\n3. Create reaction roles\n4. Import custom commands",
                recommended_channels=["mod-log", "automod-log", "staff-chat"]
            ),
            
            "dyno": BotConfig(
                id="155149108183695360",
                name="Dyno",
                description="Moderation, custom commands, and server management",
                permissions=1543245943,
                scopes=["bot"],
                website="https://dyno.gg",
                category=BotCategory.MODERATION.value,
                features=[
                    "Advanced moderation",
                    "Anti-spam/raid protection",
                    "Custom commands",
                    "Music player",
                    "Server statistics"
                ],
                setup_instructions="1. Configure moderation settings\n2. Set up automod\n3. Create custom commands\n4. Enable desired modules",
                recommended_channels=["dyno-log", "mod-commands"]
            ),
            
            # Leveling Bots
            "mee6": BotConfig(
                id="159985870458322944",
                name="MEE6",
                description="Leveling system, moderation, and custom commands",
                permissions=1544027382,
                scopes=["bot"],
                website="https://mee6.xyz",
                category=BotCategory.LEVELING.value,
                features=[
                    "XP and leveling system",
                    "Role rewards",
                    "Basic moderation",
                    "Custom commands",
                    "Music player",
                    "Reaction roles"
                ],
                setup_instructions="1. Configure XP system\n2. Set up role rewards\n3. Enable moderation\n4. Create leaderboard",
                recommended_channels=["level-up", "leaderboard"]
            ),
            
            "probot": BotConfig(
                id="282859044593598464",
                name="ProBot",
                description="Leveling, moderation, and utility features",
                permissions=1342564672,
                scopes=["bot"],
                website="https://probot.io",
                category=BotCategory.LEVELING.value,
                features=[
                    "Advanced leveling system",
                    "Moderation tools",
                    "Welcome/goodbye messages",
                    "Server statistics",
                    "Custom commands"
                ],
                setup_instructions="1. Configure leveling system\n2. Set up welcome messages\n3. Enable moderation\n4. Create server stats",
                recommended_channels=["welcome", "level-rewards", "server-stats"]
            ),
            
            # Music Bots
            "groovy": BotConfig(
                id="234395307759108106",
                name="Groovy",
                description="High-quality music streaming",
                permissions=3165248,
                scopes=["bot"],
                website="https://groovy.bot",
                category=BotCategory.MUSIC.value,
                features=[
                    "High-quality music streaming",
                    "Playlist support",
                    "Queue management",
                    "Sound effects",
                    "24/7 mode"
                ],
                setup_instructions="1. Create music channels\n2. Set up DJ role\n3. Configure queue settings\n4. Enable 24/7 if needed",
                recommended_channels=["music", "music-requests"]
            ),
            
            "rythm": BotConfig(
                id="235088799074484224",
                name="Rythm",
                description="Feature-rich music bot",
                permissions=3165248,
                scopes=["bot"],
                website="https://rythm.fm",
                category=BotCategory.MUSIC.value,
                features=[
                    "Music streaming",
                    "Playlist management",
                    "Effects and filters",
                    "Queue system",
                    "Lyrics display"
                ],
                setup_instructions="1. Set up music channels\n2. Configure permissions\n3. Create playlists\n4. Set volume limits",
                recommended_channels=["music", "bot-commands"]
            ),
            
            # Utility Bots
            "tickets": BotConfig(
                id="557628352828014614",
                name="Ticket Tool",
                description="Professional ticket system",
                permissions=1342440512,
                scopes=["bot", "applications.commands"],
                website="https://tickettool.xyz",
                category=BotCategory.TICKETS.value,
                features=[
                    "Advanced ticket system",
                    "Custom categories",
                    "Transcripts",
                    "Staff management",
                    "Analytics"
                ],
                setup_instructions="1. Create ticket categories\n2. Set up staff roles\n3. Configure transcripts\n4. Create ticket panels",
                recommended_channels=["tickets", "ticket-logs", "staff-chat"]
            ),
            
            "statbot": BotConfig(
                id="280497242417225728",
                name="StatBot",
                description="Server statistics and analytics",
                permissions=134218816,
                scopes=["bot"],
                website="https://statbot.net",
                category=BotCategory.UTILITY.value,
                features=[
                    "Member count channels",
                    "Server statistics",
                    "Growth analytics",
                    "Custom counters",
                    "Graphs and charts"
                ],
                setup_instructions="1. Create stat channels\n2. Set up counters\n3. Configure analytics\n4. Enable graphs",
                recommended_channels=["📊│stats", "📈│analytics"]
            ),
            
            # Fun/Games Bots
            "dank": BotConfig(
                id="270904126974590976",
                name="Dank Memer",
                description="Memes, currency, and mini-games",
                permissions=322624,
                scopes=["bot", "applications.commands"],
                website="https://dankmemer.lol",
                category=BotCategory.ECONOMY.value,
                features=[
                    "Virtual economy",
                    "Mini-games",
                    "Meme generation",
                    "Trading system",
                    "Achievements"
                ],
                setup_instructions="1. Set up economy channels\n2. Configure game settings\n3. Enable trading\n4. Create shop items",
                recommended_channels=["💰│economy", "🎮│games", "🏪│shop"]
            ),
            
            "pokecord": BotConfig(
                id="365975655608745985",
                name="Pokécord",
                description="Pokémon catching and collecting game",
                permissions=150528,
                scopes=["bot"],
                website="https://pokecord.com",
                category=BotCategory.GAMES.value,
                features=[
                    "Pokémon catching",
                    "Collection system",
                    "Trading",
                    "Battles",
                    "Leaderboards"
                ],
                setup_instructions="1. Enable spawning\n2. Set up trading channels\n3. Configure battle settings\n4. Create leaderboards",
                recommended_channels=["🎮│pokemon", "🔄│trading", "⚔️│battles"]
            )
        }
    
    def get_bot_config(self, bot_name: str) -> Optional[BotConfig]:
        """Get configuration for a specific bot"""
        return self.popular_bots.get(bot_name.lower())
    
    def get_bots_by_category(self, category: BotCategory) -> List[BotConfig]:
        """Get all bots in a specific category"""
        return [bot for bot in self.popular_bots.values() if bot.category == category.value]
    
    def search_bots(self, query: str) -> List[BotConfig]:
        """Search bots by name, description, or features"""
        query = query.lower()
        results = []
        
        for bot in self.popular_bots.values():
            if (query in bot.name.lower() or 
                query in bot.description.lower() or
                any(query in feature.lower() for feature in bot.features)):
                results.append(bot)
        
        return results
    
    def generate_invite_url(self, bot_id: str, guild_id: str, permissions: Optional[int] = None) -> str:
        """Generate OAuth2 invite URL for a bot"""
        bot_config = None
        for bot in self.popular_bots.values():
            if bot.id == bot_id:
                bot_config = bot
                break
        
        if not bot_config:
            raise ValueError(f"Bot with ID {bot_id} not found")
        
        perms = permissions or bot_config.permissions
        scopes = "&".join([f"scope={scope}" for scope in bot_config.scopes])
        
        return (f"https://discord.com/oauth2/authorize?"
                f"client_id={bot_id}&"
                f"{scopes}&"
                f"permissions={perms}&"
                f"guild_id={guild_id}")
    
    def generate_bulk_invite_urls(self, bot_names: List[str], guild_id: str) -> Dict[str, str]:
        """Generate invite URLs for multiple bots"""
        urls = {}
        
        for bot_name in bot_names:
            bot_config = self.get_bot_config(bot_name)
            if bot_config:
                try:
                    urls[bot_name] = self.generate_invite_url(bot_config.id, guild_id)
                except Exception as e:
                    logger.error(f"Error generating invite URL for {bot_name}: {e}")
                    urls[bot_name] = f"Error: {str(e)}"
            else:
                urls[bot_name] = "Error: Bot not found"
        
        return urls
    
    def get_recommended_bots_for_server_type(self, server_type: str) -> List[str]:
        """Get recommended bots based on server type"""
        recommendations = {
            "gaming": ["carl", "mee6", "groovy", "dank", "pokecord"],
            "community": ["carl", "mee6", "tickets", "statbot", "dyno"],
            "business": ["carl", "tickets", "statbot", "dyno"],
            "study": ["carl", "tickets", "statbot", "groovy"],
            "music": ["groovy", "rythm", "carl", "mee6"],
            "turkish": ["probot", "carl", "mee6", "groovy", "tickets"],
            "default": ["carl", "mee6", "tickets", "statbot"]
        }
        
        return recommendations.get(server_type.lower(), recommendations["default"])
    
    async def check_bot_status(self, bot_id: str) -> Dict[str, Any]:
        """Check if a bot is online and responsive"""
        try:
            # This would require additional API calls or bot checking service
            # For now, return a basic status
            return {
                "online": True,
                "response_time": "N/A",
                "last_seen": "N/A",
                "status": "operational"
            }
        except Exception as e:
            logger.error(f"Error checking bot status for {bot_id}: {e}")
            return {
                "online": False,
                "response_time": "N/A",
                "last_seen": "N/A",
                "status": "unknown",
                "error": str(e)
            }
    
    def get_setup_guide(self, bot_name: str) -> Dict[str, Any]:
        """Get detailed setup guide for a bot"""
        bot_config = self.get_bot_config(bot_name)
        if not bot_config:
            return {"error": "Bot not found"}
        
        return {
            "bot_name": bot_config.name,
            "description": bot_config.description,
            "features": bot_config.features,
            "setup_instructions": bot_config.setup_instructions.split('\n'),
            "recommended_channels": bot_config.recommended_channels,
            "website": bot_config.website,
            "permissions_needed": bot_config.permissions,
            "category": bot_config.category
        }
    
    def calculate_permissions(self, features: List[str]) -> int:
        """Calculate required permissions based on desired features"""
        permission_map = {
            "moderation": 1543503103,
            "music": 3165248,
            "leveling": 134218816,
            "tickets": 1342440512,
            "logging": 536977472,
            "roles": 268435456,
            "channels": 16,
            "messages": 11264,
            "basic": 150528
        }
        
        total_permissions = 0
        for feature in features:
            feature_lower = feature.lower()
            for perm_name, perm_value in permission_map.items():
                if perm_name in feature_lower:
                    total_permissions |= perm_value
                    break
        
        return total_permissions if total_permissions > 0 else permission_map["basic"] 