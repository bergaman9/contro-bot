"""
AI-powered profanity detection system using Sinkaf library.
Provides advanced Turkish profanity detection with context awareness.
"""

import asyncio
import discord
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

try:
    from sinkaf import Sinkaf
except ImportError:
    Sinkaf = None
    logging.warning("Sinkaf library not found. AI profanity detection will be disabled.")

from utils.database.connection import get_async_db
from utils.core.formatting import create_embed


class AIProfanityDetector:
    """AI-powered profanity detection using Sinkaf"""
    
    def __init__(self):
        self.sinkaf = None
        self.mongo_db = get_async_db()
        self.logger = logging.getLogger('ai_profanity')
        
        if Sinkaf:
            try:
                self.sinkaf = Sinkaf()
                self.logger.info("Sinkaf AI profanity detector initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Sinkaf: {e}")
                self.sinkaf = None
        else:
            self.logger.warning("Sinkaf not available - AI profanity detection disabled")
    
    def is_available(self) -> bool:
        """Check if AI profanity detection is available"""
        return self.sinkaf is not None
    
    async def detect_profanity(self, text: str, confidence_threshold: float = 0.7) -> Tuple[bool, float]:
        """
        Detect profanity in text using AI
        
        Args:
            text: Text to analyze
            confidence_threshold: Minimum confidence level to consider as profanity
            
        Returns:
            Tuple of (is_profanity, confidence_score)
        """
        if not self.is_available():
            return False, 0.0
        
        try:
            # Sinkaf expects a list of texts
            result = self.sinkaf.tahmin([text])
            
            if result and len(result) > 0:
                is_profanity = result[0]
                # Try to get confidence score if available
                confidence = getattr(result, 'confidence', 1.0) if is_profanity else 0.0
                
                # Apply threshold
                is_profane = is_profanity and confidence >= confidence_threshold
                
                return is_profane, confidence
            
            return False, 0.0
            
        except Exception as e:
            self.logger.error(f"Error in AI profanity detection: {e}")
            return False, 0.0
    
    async def analyze_message(self, message: discord.Message, settings: Dict) -> Dict:
        """
        Analyze a message for profanity and return detailed results
        
        Args:
            message: Discord message to analyze
            settings: Guild moderation settings
            
        Returns:
            Dict with analysis results
        """
        if not settings.get("ai_profanity_filter_enabled", False):
            return {"detected": False, "reason": "AI filter disabled"}
        
        confidence_threshold = settings.get("ai_profanity_confidence_threshold", 0.7)
        
        # Analyze message content
        is_profane, confidence = await self.detect_profanity(
            message.content, 
            confidence_threshold
        )
        
        result = {
            "detected": is_profane,
            "confidence": confidence,
            "threshold": confidence_threshold,
            "content": message.content,
            "user_id": message.author.id,
            "channel_id": message.channel.id,
            "guild_id": message.guild.id,
            "message_id": message.id,
            "timestamp": datetime.utcnow()
        }
        
        # Log detection if enabled
        if is_profane and settings.get("log_deleted_messages", True):
            await self.log_profanity_detection(result)
        
        return result
    
    async def log_profanity_detection(self, detection_result: Dict):
        """Log profanity detection to database"""
        try:
            await self.mongo_db.profanity_logs.insert_one({
                **detection_result,
                "detection_type": "ai_sinkaf",
                "logged_at": datetime.utcnow()
            })
        except Exception as e:
            self.logger.error(f"Failed to log profanity detection: {e}")
    
    async def get_profanity_stats(self, guild_id: int, days: int = 30) -> Dict:
        """Get profanity detection statistics for a guild"""
        try:
            from datetime import timedelta
            
            since_date = datetime.utcnow() - timedelta(days=days)
            
            pipeline = [
                {
                    "$match": {
                        "guild_id": guild_id,
                        "timestamp": {"$gte": since_date},
                        "detection_type": "ai_sinkaf"
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_detections": {"$sum": 1},
                        "unique_users": {"$addToSet": "$user_id"},
                        "avg_confidence": {"$avg": "$confidence"},
                        "max_confidence": {"$max": "$confidence"},
                        "min_confidence": {"$min": "$confidence"}
                    }
                }
            ]
            
            result = await self.mongo_db.profanity_logs.aggregate(pipeline).to_list(1)
            
            if result:
                stats = result[0]
                stats["unique_users_count"] = len(stats["unique_users"])
                del stats["unique_users"]
                return stats
            
            return {
                "total_detections": 0,
                "unique_users_count": 0,
                "avg_confidence": 0.0,
                "max_confidence": 0.0,
                "min_confidence": 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get profanity stats: {e}")
            return {}


class ProfanityModerationHandler:
    """Handles moderation actions when profanity is detected"""
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = get_async_db()
        self.logger = logging.getLogger('profanity_moderation')
    
    async def handle_profanity_detection(self, message: discord.Message, detection_result: Dict, settings: Dict):
        """Handle a profanity detection with appropriate action"""
        if not detection_result.get("detected", False):
            return
        
        action = settings.get("profanity_action", "delete")
        user = message.author
        guild = message.guild
        
        try:
            # Always delete the message first
            if action in ["delete", "warn", "mute", "kick", "ban"]:
                await message.delete()
            
            # Log the action
            await self.log_moderation_action(message, detection_result, action, settings)
            
            # Take additional action based on settings
            if action == "warn":
                await self.warn_user(user, message.channel, detection_result, settings)
            elif action == "mute":
                await self.mute_user(user, guild, settings)
            elif action == "kick":
                await self.kick_user(user, guild, detection_result)
            elif action == "ban":
                await self.ban_user(user, guild, detection_result)
            
            # Send notification to moderation log channel
            await self.send_moderation_log(message, detection_result, action, settings)
            
        except Exception as e:
            self.logger.error(f"Error handling profanity detection: {e}")
    
    async def warn_user(self, user: discord.Member, channel: discord.TextChannel, detection_result: Dict, settings: Dict):
        """Warn user for profanity"""
        try:
            embed = create_embed(
                title="⚠️ Profanity Warning",
                description=f"Your message was automatically removed for containing inappropriate content.\n\n"
                           f"**Confidence:** {detection_result['confidence']:.2%}\n"
                           f"**Action:** Message deleted\n\n"
                           f"Please follow the server rules and keep the chat respectful.",
                color=discord.Color.orange()
            )
            
            # Try to send DM first, fallback to channel mention
            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                # Send in channel if DM fails
                warning_msg = await channel.send(
                    f"{user.mention}",
                    embed=embed,
                    delete_after=10
                )
                
        except Exception as e:
            self.logger.error(f"Error warning user: {e}")
    
    async def mute_user(self, user: discord.Member, guild: discord.Guild, settings: Dict):
        """Mute user for profanity"""
        try:
            mute_role_id = settings.get("mute_role_id")
            duration = settings.get("punishment_duration", 3600)  # 1 hour default
            
            if mute_role_id:
                mute_role = guild.get_role(mute_role_id)
                if mute_role:
                    await user.add_roles(mute_role, reason="AI profanity detection")
                    
                    # Schedule unmute (you might want to implement a task for this)
                    # For now, just log it
                    await self.mongo_db.scheduled_unmutes.insert_one({
                        "user_id": user.id,
                        "guild_id": guild.id,
                        "unmute_at": datetime.utcnow().timestamp() + duration,
                        "reason": "ai_profanity_auto_mute"
                    })
                    
        except Exception as e:
            self.logger.error(f"Error muting user: {e}")
    
    async def kick_user(self, user: discord.Member, guild: discord.Guild, detection_result: Dict):
        """Kick user for profanity"""
        try:
            reason = f"AI profanity detection - Confidence: {detection_result['confidence']:.2%}"
            await user.kick(reason=reason)
        except Exception as e:
            self.logger.error(f"Error kicking user: {e}")
    
    async def ban_user(self, user: discord.Member, guild: discord.Guild, detection_result: Dict):
        """Ban user for profanity"""
        try:
            reason = f"AI profanity detection - Confidence: {detection_result['confidence']:.2%}"
            await user.ban(reason=reason, delete_message_days=1)
        except Exception as e:
            self.logger.error(f"Error banning user: {e}")
    
    async def send_moderation_log(self, message: discord.Message, detection_result: Dict, action: str, settings: Dict):
        """Send log to moderation log channel"""
        try:
            log_channel_id = settings.get("moderation_log_channel")
            if not log_channel_id:
                return
            
            log_channel = self.bot.get_channel(log_channel_id)
            if not log_channel:
                return
            
            embed = create_embed(
                title="🤖 AI Profanity Detection",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="User",
                value=f"{message.author.mention} ({message.author.id})",
                inline=True
            )
            
            embed.add_field(
                name="Channel",
                value=f"#{message.channel.name}",
                inline=True
            )
            
            embed.add_field(
                name="Action Taken",
                value=action.title(),
                inline=True
            )
            
            embed.add_field(
                name="AI Confidence",
                value=f"{detection_result['confidence']:.2%}",
                inline=True
            )
            
            embed.add_field(
                name="Threshold",
                value=f"{detection_result['threshold']:.2%}",
                inline=True
            )
            
            embed.add_field(
                name="Message Content",
                value=f"```{detection_result['content'][:1000]}```",
                inline=False
            )
            
            embed.timestamp = datetime.utcnow()
            embed.set_footer(text="Sinkaf AI Detection")
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error sending moderation log: {e}")
    
    async def log_moderation_action(self, message: discord.Message, detection_result: Dict, action: str, settings: Dict):
        """Log moderation action to database"""
        try:
            await self.mongo_db.moderation_actions.insert_one({
                "type": "ai_profanity_action",
                "user_id": message.author.id,
                "guild_id": message.guild.id,
                "channel_id": message.channel.id,
                "message_id": message.id,
                "action": action,
                "detection_result": detection_result,
                "moderator": "AI System",
                "timestamp": datetime.utcnow(),
                "reason": f"AI profanity detection - {detection_result['confidence']:.2%} confidence"
            })
        except Exception as e:
            self.logger.error(f"Error logging moderation action: {e}")


# Global instances
ai_profanity_detector = AIProfanityDetector()
profanity_moderation_handler = None


def initialize_profanity_handler(bot):
    """Initialize the profanity moderation handler with bot instance"""
    global profanity_moderation_handler
    profanity_moderation_handler = ProfanityModerationHandler(bot)
    return profanity_moderation_handler


__all__ = [
    'AIProfanityDetector',
    'ProfanityModerationHandler', 
    'ai_profanity_detector',
    'initialize_profanity_handler'
]
