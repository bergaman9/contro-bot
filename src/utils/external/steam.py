import aiohttp
import logging
import os
import re
from typing import Dict, Optional, List, Union, Any
from ...core.config import get_config

logger = logging.getLogger('steam')

class SteamAPI:
    """
    Utility class for interacting with Steam API
    """
    
    def __init__(self):
        config = get_config()
        self.api_key = config.external_services.steam_api_key
        self.base_url = "https://api.steampowered.com"
        
        # Person states in Steam
        self.person_states = {
            0: "Offline",
            1: "Online",
            2: "Busy",
            3: "Away",
            4: "Snooze",
            5: "Looking to Trade",
            6: "Looking to Play"
        }
    
    async def get_steam_id_from_vanity_url(self, vanity_url: str) -> Optional[str]:
        """
        Convert a Steam vanity URL to a Steam ID
        
        Args:
            vanity_url: The vanity URL name (e.g., 'gabelogannewell' from 'steamcommunity.com/id/gabelogannewell')
            
        Returns:
            Steam ID as string or None if not found
        """
        if not self.api_key:
            logger.warning("Steam API key not configured")
            return None
        
        # Remove URL parts if a full URL was provided
        vanity_url = re.sub(r'^https?://steamcommunity.com/id/', '', vanity_url)
        vanity_url = vanity_url.rstrip('/')
        
        # Check if it's already a Steam ID
        if vanity_url.isdigit():
            return vanity_url
        
        try:
            url = f"{self.base_url}/ISteamUser/ResolveVanityURL/v1/"
            params = {
                "key": self.api_key,
                "vanityurl": vanity_url
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get("response", {})
                        
                        if result.get("success") == 1:
                            return result.get("steamid")
            
            return None
        except Exception as e:
            logger.error(f"Error fetching Steam ID: {e}")
            return None
    
    async def get_user_summary(self, steam_id_or_vanity: str) -> Optional[Dict]:
        """
        Get a user's Steam profile information
        
        Args:
            steam_id_or_vanity: Steam ID or vanity URL name
            
        Returns:
            Dictionary with user information or None if not found
        """
        if not self.api_key:
            logger.warning("Steam API key not configured")
            return None
        
        try:
            # Convert vanity URL to Steam ID if needed
            if not steam_id_or_vanity.isdigit():
                steam_id = await self.get_steam_id_from_vanity_url(steam_id_or_vanity)
                if not steam_id:
                    return None
            else:
                steam_id = steam_id_or_vanity
            
            url = f"{self.base_url}/ISteamUser/GetPlayerSummaries/v2/"
            params = {
                "key": self.api_key,
                "steamids": steam_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        players = data.get("response", {}).get("players", [])
                        
                        if players:
                            player = players[0]
                            
                            # Add readable persona state
                            state = player.get("personastate", 0)
                            player["personastate_name"] = self.person_states.get(state, "Unknown")
                            
                            return player
            
            return None
        except Exception as e:
            logger.error(f"Error fetching Steam user summary: {e}")
            return None
    
    async def get_owned_games(self, steam_id_or_vanity: str) -> Optional[List[Dict]]:
        """
        Get a list of games owned by the user
        
        Args:
            steam_id_or_vanity: Steam ID or vanity URL name
            
        Returns:
            List of games or None if not found/error
        """
        if not self.api_key:
            logger.warning("Steam API key not configured")
            return None
        
        try:
            # Convert vanity URL to Steam ID if needed
            if not steam_id_or_vanity.isdigit():
                steam_id = await self.get_steam_id_from_vanity_url(steam_id_or_vanity)
                if not steam_id:
                    return None
            else:
                steam_id = steam_id_or_vanity
            
            url = f"{self.base_url}/IPlayerService/GetOwnedGames/v1/"
            params = {
                "key": self.api_key,
                "steamid": steam_id,
                "include_appinfo": 1,
                "include_played_free_games": 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_data = data.get("response", {})
                        
                        if "games" in response_data:
                            return response_data["games"]
            
            return None
        except Exception as e:
            logger.error(f"Error fetching owned games: {e}")
            return None
