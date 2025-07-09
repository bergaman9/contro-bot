import discord
from discord.ext import commands, tasks
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from urllib.parse import urlparse
import json

from utils.database.connection import get_database
from utils.core.config import get_config

logger = logging.getLogger(__name__)

class CustomStatusManager(commands.Cog):
    """Custom Status Manager - Automatically assign roles based on user status"""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.status_cache = {}
        self.update_task = None
        self.active_timers: Dict[str, asyncio.Task] = {}
        self.cooldowns: Dict[str, datetime] = {}
        self.config = get_config()
        
    async def cog_load(self):
        """Initialize database connection when cog loads"""
        try:
            self.db = await get_database()
            logger.info("✅ Custom Status Manager cog loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load Custom Status Manager cog: {e}")
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Handle member status changes"""
        if before.activity != after.activity or before.status != after.status:
            await self.check_status_rules(after)
    
    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        """Handle presence updates"""
        if before.activity != after.activity or before.status != after.status:
            await self.check_status_rules(after)
    
    async def check_status_rules(self, member: discord.Member):
        """Check and apply status rules for a member"""
        if not self.db:
            return
        
        try:
            # Get guild settings
            settings = await self.db.custom_status_rules.find_one({"guild_id": str(member.guild.id)})
            if not settings or not settings.get("enabled", False):
                return
            
            # Check cooldown
            cooldown_key = f"{member.guild.id}_{member.id}"
            cooldown_seconds = settings.get("settings", {}).get("cooldown_seconds", 30)
            
            if cooldown_key in self.cooldowns:
                time_diff = datetime.now() - self.cooldowns[cooldown_key]
                if time_diff.total_seconds() < cooldown_seconds:
                    return
            
            self.cooldowns[cooldown_key] = datetime.now()
            
            # Prepare activity data
            activity_data = self.extract_activity_data(member)
            
            # Check each rule
            for rule in settings.get("rules", []):
                if not rule.get("enabled", True):
                    continue
                
                if await self.evaluate_rule(rule, activity_data):
                    await self.apply_rule_actions(member, rule, activity_data)
                    await self.log_rule_action(member, rule, activity_data)
                    await self.update_statistics(settings, rule["id"])
                    
                    # Only apply one rule per check (highest priority)
                    break
                    
        except Exception as e:
            logger.error(f"Error checking status rules for {member}: {e}")
    
    def extract_activity_data(self, member: discord.Member) -> Dict[str, Any]:
        """Extract relevant data from member's activity"""
        data = {
            "status_text": "",
            "game_name": "",
            "url": "",
            "activity_type": "",
            "timestamp": datetime.now()
        }
        
        if member.activity:
            if isinstance(member.activity, discord.Game):
                data["game_name"] = member.activity.name
                data["activity_type"] = "playing"
            elif isinstance(member.activity, discord.Streaming):
                data["activity_type"] = "streaming"
                data["url"] = member.activity.url
            elif isinstance(member.activity, discord.Activity):
                data["activity_type"] = member.activity.type.name
                if member.activity.name:
                    data["status_text"] = member.activity.name
                if hasattr(member.activity, 'url') and member.activity.url:
                    data["url"] = member.activity.url
        
        # Also check custom status
        if member.activity and hasattr(member.activity, 'state') and member.activity.state:
            data["status_text"] = member.activity.state
        
        return data
    
    async def evaluate_rule(self, rule: Dict, activity_data: Dict) -> bool:
        """Evaluate if a rule matches the activity data"""
        rule_type = rule.get("type")
        conditions = rule.get("conditions", {})
        
        try:
            if rule_type == "status_text":
                return self.evaluate_status_text_rule(conditions, activity_data["status_text"])
            elif rule_type == "game":
                return self.evaluate_game_rule(conditions, activity_data["game_name"])
            elif rule_type == "url":
                return self.evaluate_url_rule(conditions, activity_data["url"])
            elif rule_type == "keyword":
                return self.evaluate_keyword_rule(conditions, activity_data["status_text"])
            elif rule_type == "activity_type":
                return self.evaluate_activity_type_rule(conditions, activity_data["activity_type"])
            elif rule_type == "time_based":
                return self.evaluate_time_based_rule(conditions)
            else:
                logger.warning(f"Unknown rule type: {rule_type}")
                return False
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.get('name', 'Unknown')}: {e}")
            return False
    
    def evaluate_status_text_rule(self, conditions: Dict, status_text: str) -> bool:
        """Evaluate status text rule"""
        if not status_text:
            return False
        
        # Check exact matches
        if "status_exact" in conditions and conditions["status_exact"]:
            if status_text in conditions["status_exact"]:
                return True
        
        # Check contains
        if "status_contains" in conditions and conditions["status_contains"]:
            for phrase in conditions["status_contains"]:
                if phrase.lower() in status_text.lower():
                    return True
        
        # Check regex
        if "status_regex" in conditions and conditions["status_regex"]:
            try:
                pattern = re.compile(conditions["status_regex"], re.IGNORECASE)
                if pattern.search(status_text):
                    return True
            except re.error:
                logger.error(f"Invalid regex pattern: {conditions['status_regex']}")
        
        return False
    
    def evaluate_game_rule(self, conditions: Dict, game_name: str) -> bool:
        """Evaluate game rule"""
        if not game_name:
            return False
        
        if "game_names" in conditions and conditions["game_names"]:
            for name in conditions["game_names"]:
                if name.lower() in game_name.lower():
                    return True
        
        return False
    
    def evaluate_url_rule(self, conditions: Dict, url: str) -> bool:
        """Evaluate URL rule"""
        if not url:
            return False
        
        try:
            parsed_url = urlparse(url)
            
            # Check domains
            if "url_domains" in conditions and conditions["url_domains"]:
                for domain in conditions["url_domains"]:
                    if domain in parsed_url.netloc:
                        return True
            
            # Check patterns
            if "url_patterns" in conditions and conditions["url_patterns"]:
                for pattern in conditions["url_patterns"]:
                    if pattern in url:
                        return True
            
            # Check keywords
            if "url_keywords" in conditions and conditions["url_keywords"]:
                for keyword in conditions["url_keywords"]:
                    if keyword.lower() in url.lower():
                        return True
        except Exception:
            return False
        
        return False
    
    def evaluate_keyword_rule(self, conditions: Dict, status_text: str) -> bool:
        """Evaluate keyword rule"""
        if not status_text or "keywords" not in conditions:
            return False
        
        case_sensitive = conditions.get("case_sensitive", False)
        text = status_text if case_sensitive else status_text.lower()
        
        for keyword in conditions["keywords"]:
            search_keyword = keyword if case_sensitive else keyword.lower()
            if search_keyword in text:
                return True
        
        return False
    
    def evaluate_activity_type_rule(self, conditions: Dict, activity_type: str) -> bool:
        """Evaluate activity type rule"""
        if not activity_type or "activity_types" not in conditions:
            return False
        
        return activity_type in conditions["activity_types"]
    
    def evaluate_time_based_rule(self, conditions: Dict) -> bool:
        """Evaluate time-based rule"""
        if "time_ranges" not in conditions:
            return False
        
        now = datetime.now()
        current_time = now.hour * 60 + now.minute
        current_day = now.weekday()
        
        for time_range in conditions["time_ranges"]:
            start_time = self.parse_time_to_minutes(time_range["start_time"])
            end_time = self.parse_time_to_minutes(time_range["end_time"])
            
            # Check day of week
            if "days_of_week" in time_range:
                if current_day not in time_range["days_of_week"]:
                    continue
            
            # Check time range
            if start_time <= end_time:
                # Same day range
                if start_time <= current_time <= end_time:
                    return True
            else:
                # Overnight range
                if current_time >= start_time or current_time <= end_time:
                    return True
        
        return False
    
    def parse_time_to_minutes(self, time_str: str) -> int:
        """Parse time string (HH:MM) to minutes"""
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    
    async def apply_rule_actions(self, member: discord.Member, rule: Dict, activity_data: Dict):
        """Apply rule actions to the member"""
        actions = rule.get("actions", {})
        
        try:
            # Add roles
            for role_id in actions.get("add_roles", []):
                role = member.guild.get_role(int(role_id))
                if role and role not in member.roles:
                    await member.add_roles(role, reason=f"Custom Status Rule: {rule['name']}")
                    logger.info(f"Added role {role.name} to {member} via rule {rule['name']}")
            
            # Remove roles
            for role_id in actions.get("remove_roles", []):
                role = member.guild.get_role(int(role_id))
                if role and role in member.roles:
                    await member.remove_roles(role, reason=f"Custom Status Rule: {rule['name']}")
                    logger.info(f"Removed role {role.name} from {member} via rule {rule['name']}")
            
            # Handle temporary roles
            for temp_role in actions.get("temporary_roles", []):
                role_id = temp_role["role_id"]
                duration_minutes = temp_role["duration_minutes"]
                
                role = member.guild.get_role(int(role_id))
                if role and role not in member.roles:
                    await member.add_roles(role, reason=f"Custom Status Rule: {rule['name']} (Temporary)")
                    
                    # Schedule removal
                    timer_key = f"{member.guild.id}_{member.id}_{role_id}"
                    if timer_key in self.active_timers:
                        self.active_timers[timer_key].cancel()
                    
                    self.active_timers[timer_key] = asyncio.create_task(
                        self.remove_temporary_role(member, role, duration_minutes, rule['name'])
                    )
            
            # Send message
            if "send_message" in actions:
                message_config = actions["send_message"]
                channel = member.guild.get_channel(int(message_config["channel_id"]))
                if channel:
                    message = message_config["message"].replace("{user}", member.mention)
                    await channel.send(message)
                    
        except Exception as e:
            logger.error(f"Error applying rule actions for {member}: {e}")
    
    async def remove_temporary_role(self, member: discord.Member, role: discord.Role, duration_minutes: int, rule_name: str):
        """Remove a temporary role after the specified duration"""
        try:
            await asyncio.sleep(duration_minutes * 60)
            
            if role in member.roles:
                await member.remove_roles(role, reason=f"Custom Status Rule: {rule_name} (Temporary expired)")
                logger.info(f"Removed temporary role {role.name} from {member}")
            
            # Clean up timer
            timer_key = f"{member.guild.id}_{member.id}_{role.id}"
            if timer_key in self.active_timers:
                del self.active_timers[timer_key]
                
        except asyncio.CancelledError:
            # Timer was cancelled
            pass
        except Exception as e:
            logger.error(f"Error removing temporary role: {e}")
    
    async def log_rule_action(self, member: discord.Member, rule: Dict, activity_data: Dict):
        """Log rule action to database"""
        if not self.db:
            return
        
        try:
            log_entry = {
                "guild_id": str(member.guild.id),
                "user_id": str(member.id),
                "rule_id": rule["id"],
                "action_type": "role_added",  # Default, could be enhanced
                "role_id": "",  # Would need to track which roles were added
                "trigger_data": activity_data,
                "executed_at": datetime.now()
            }
            
            await self.db.custom_status_logs.insert_one(log_entry)
            
        except Exception as e:
            logger.error(f"Error logging rule action: {e}")
    
    async def update_statistics(self, settings: Dict, rule_id: str):
        """Update rule statistics"""
        if not self.db:
            return
        
        try:
            # Update total actions
            await self.db.custom_status_rules.update_one(
                {"guild_id": settings["guild_id"]},
                {
                    "$inc": {"statistics.total_actions": 1},
                    "$set": {"statistics.last_action": datetime.now()},
                    "$inc": {f"statistics.rules_triggered.{rule_id}": 1}
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")

async def setup(bot):
    await bot.add_cog(CustomStatusManager(bot)) 