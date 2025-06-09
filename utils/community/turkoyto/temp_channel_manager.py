import discord
import logging
import asyncio
from typing import Dict, Optional, Any

logger = logging.getLogger('turkoyto')

class TempChannelManager:
    """Manages temporary voice channels that are created when users join a specific channel"""
    
    def __init__(self, bot):
        self.bot = bot
        self.creator_channel_id = 1364003174356226120  # ID of the channel that triggers creation
        self.temp_channels = {}  # Maps channel_id -> creator_id
        self.channel_timers = {}  # Maps channel_id -> deletion timer task
    
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates for temporary channel creation and deletion"""
        try:
            # User joined the creator channel
            if after.channel and after.channel.id == self.creator_channel_id:
                await self.create_temp_channel(member, after.channel)
                return
                
            # User left a temporary channel - delete it immediately if empty
            if before.channel and before.channel.id in self.temp_channels:
                if len(before.channel.members) == 0:
                    # Delete channel immediately instead of scheduling
                    await self.delete_channel(before.channel)
                
            # User joined a channel that was scheduled for deletion - cancel deletion
            if after.channel and after.channel.id in self.channel_timers:
                timer_task = self.channel_timers[after.channel.id]
                if timer_task and not timer_task.done():
                    timer_task.cancel()
                    self.channel_timers[after.channel.id] = None
                    logger.info(f"Cancelled deletion timer for channel {after.channel.name} ({after.channel.id})")
                    
        except Exception as e:
            logger.error(f"Error in temp channel voice state update handler: {e}", exc_info=True)
    
    async def create_temp_channel(self, member, creator_channel):
        """Create a temporary voice channel for a member and move them to it"""
        try:
            # Get the guild from the creator channel
            guild = creator_channel.guild
            
            # Determine the category to place the channel in (same as creator channel)
            category = creator_channel.category
            
            # Get game information if available
            game_name = None
            game_emoji = "🎮"  # Default emoji
            
            # Try to get the member's activity (game)
            for activity in member.activities:
                if isinstance(activity, discord.Game) or isinstance(activity, discord.Activity):
                    game_name = activity.name
                    game_emoji = self.get_game_emoji(game_name)
                    break
            
            # Create channel name
            if game_name:
                channel_name = f"{game_emoji} {member.display_name} kanalı"
            else:
                channel_name = f"{game_emoji} {member.display_name} kanalı"
            
            # Create the channel
            temp_channel = await guild.create_voice_channel(
                name=channel_name,
                category=category,
                reason=f"Temporary game channel for {member.display_name}"
            )
            
            # Register the channel in our tracking dict
            self.temp_channels[temp_channel.id] = member.id
            
            # Move the member to the new channel
            await member.move_to(temp_channel)
            
            logger.info(f"Created temporary channel {temp_channel.name} ({temp_channel.id}) for {member.display_name}")
            
            return temp_channel
            
        except Exception as e:
            logger.error(f"Error creating temporary channel: {e}", exc_info=True)
            return None
    
    async def delete_channel(self, channel):
        """Delete a channel immediately"""
        try:
            # Check if the channel still exists and is empty
            try:
                channel = await self.bot.fetch_channel(channel.id)
                if len(channel.members) == 0:
                    await channel.delete(reason="Temporary channel is empty")
                    # Remove from our tracking
                    if channel.id in self.temp_channels:
                        del self.temp_channels[channel.id]
                    if channel.id in self.channel_timers:
                        del self.channel_timers[channel.id]
                    logger.info(f"Deleted empty temporary channel {channel.name} ({channel.id})")
            except discord.NotFound:
                # Channel already deleted
                if channel.id in self.temp_channels:
                    del self.temp_channels[channel.id]
                if channel.id in self.channel_timers:
                    del self.channel_timers[channel.id]
                logger.info(f"Channel {channel.id} was already deleted")
                
        except Exception as e:
            logger.error(f"Error in delete_channel: {e}", exc_info=True)
    
    # Keep this method for backward compatibility
    async def schedule_channel_deletion(self, channel, delay=15):
        """Schedule a channel for deletion after a delay (in seconds)"""
        try:
            # Just call delete_channel directly
            await self.delete_channel(channel)
            logger.info(f"Deleted channel {channel.name} ({channel.id}) immediately")
        except Exception as e:
            logger.error(f"Error scheduling channel deletion: {e}", exc_info=True)
    
    # Keep this method for backward compatibility but it won't be used
    async def delete_channel_after_delay(self, channel, delay):
        """Legacy method kept for compatibility"""
        pass
    
    def get_game_emoji(self, game_name):
        """Get an appropriate emoji for a game"""
        game_name_lower = game_name.lower()
        
        # Common games and their emojis
        game_emojis = {
            "minecraft": "⛏️",
            "valorant": "🔫",
            "league of legends": "🧙",
            "fortnite": "🏝️",
            "counter-strike": "💣",
            "cs2": "💣",
            "apex legends": "🎯",
            "call of duty": "🪖",
            "gta": "🚗",
            "rocket league": "⚽",
            "among us": "👨‍🚀",
            "pubg": "🔫",
            "overwatch": "🦸",
            "rust": "🪓",
            "rainbow six": "🛡️"
        }
        
        # Check if game name contains any of our known games
        for known_game, emoji in game_emojis.items():
            if known_game in game_name_lower:
                return emoji
        
        # Default emoji for games
        return "🎮"
