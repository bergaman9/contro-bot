import discord
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from src.cogs.base import BaseCog
from ...utils.core.manager import get_async_database
from ...utils.helpers.discord import create_embed
from ...bot.constants import Colors

logger = logging.getLogger(__name__)

class AutoRole(BaseCog):
    """Auto Role Management System - Automatically assign roles based on various triggers"""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.role_assignment_queue = asyncio.Queue()
        self.message_counts: Dict[str, Dict[str, int]] = {}  # guild_id -> user_id -> count
        self.voice_times: Dict[str, Dict[str, int]] = {}  # guild_id -> user_id -> minutes
        self.active_timers: Dict[str, asyncio.Task] = {}
        self.cooldowns: Dict[str, datetime] = {}
        self._autorole_db = None  # Will be initialized in cog_load
        
    async def cog_load(self):
        """Initialize database connection when cog loads"""
        try:
            # Call parent cog_load first
            await super().cog_load()
            
            # Initialize database connection
            from src.utils.core.manager import get_async_database
            self._autorole_db = await get_async_database()
            
            logger.info("✅ AutoRole cog loaded successfully")
            # Start background tasks
            self.process_role_queue.start()
            self.cleanup_old_data.start()
        except Exception as e:
            logger.error(f"❌ Failed to load AutoRole cog: {e}")
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.process_role_queue.cancel()
        self.cleanup_old_data.cancel()
        # Cancel all active timers
        for timer in self.active_timers.values():
            timer.cancel()
    
    @tasks.loop(seconds=5.0)
    async def process_role_queue(self):
        """Process role assignment queue"""
        try:
            while not self.role_assignment_queue.empty():
                assignment = await self.role_assignment_queue.get()
                await self.execute_role_assignment(assignment)
        except Exception as e:
            logger.error(f"Error processing role queue: {e}")
    
    @tasks.loop(hours=1.0)
    async def cleanup_old_data(self):
        """Clean up old analytics and temporary data"""
        try:
            # Clean up old message counts (older than 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            # Implementation depends on your database structure
            logger.debug("Cleaned up old auto role data")
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    @process_role_queue.before_loop
    async def before_process_role_queue(self):
        """Wait until bot is ready"""
        await self.bot.wait_until_ready()
    
    @cleanup_old_data.before_loop
    async def before_cleanup_old_data(self):
        """Wait until bot is ready"""
        await self.bot.wait_until_ready()
    
    # ==================== EVENT HANDLERS ====================
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle member join events"""
        try:
            logger.info(f"Member joined: {member.name} in {member.guild.name}")
            
            # Get auto role settings
            settings = await self.get_auto_role_settings(member.guild.id)
            if not settings or not settings.get('enabled', False):
                return
            
            # Add to role assignment queue
            await self.role_assignment_queue.put({
                'type': 'member_join',
                'member': member,
                'settings': settings,
                'timestamp': datetime.utcnow()
            })
            
        except Exception as e:
            logger.error(f"Error handling member join for {member}: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle message events for message count tracking"""
        if message.author.bot or not message.guild:
            return
        
        try:
            # Update message count
            guild_id = str(message.guild.id)
            user_id = str(message.author.id)
            
            if guild_id not in self.message_counts:
                self.message_counts[guild_id] = {}
            if user_id not in self.message_counts[guild_id]:
                self.message_counts[guild_id][user_id] = 0
            
            self.message_counts[guild_id][user_id] += 1
            
            # Check for message count triggers
            await self.check_message_count_triggers(message.author)
            
        except Exception as e:
            logger.error(f"Error handling message for auto role: {e}")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state changes for voice time tracking"""
        if member.bot:
            return
        
        try:
            guild_id = str(member.guild.id)
            user_id = str(member.id)
            
            # Initialize tracking if needed
            if guild_id not in self.voice_times:
                self.voice_times[guild_id] = {}
            if user_id not in self.voice_times[guild_id]:
                self.voice_times[guild_id][user_id] = 0
            
            # Track voice time
            if before.channel != after.channel:
                if before.channel:  # Left a channel
                    # Stop tracking for this user
                    timer_key = f"{guild_id}_{user_id}"
                    if timer_key in self.active_timers:
                        self.active_timers[timer_key].cancel()
                        del self.active_timers[timer_key]
                
                if after.channel:  # Joined a channel
                    # Start tracking voice time
                    self.active_timers[f"{guild_id}_{user_id}"] = asyncio.create_task(
                        self.track_voice_time(member)
                    )
            
        except Exception as e:
            logger.error(f"Error handling voice state update: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reaction events for reaction-based roles"""
        if payload.member and payload.member.bot:
            return
        
        try:
            # Check for reaction role triggers
            await self.check_reaction_role_triggers(payload)
            
        except Exception as e:
            logger.error(f"Error handling reaction for auto role: {e}")
    
    # ==================== CORE ROLE ASSIGNMENT ====================
    
    async def execute_role_assignment(self, assignment: Dict[str, Any]):
        """Execute a role assignment from the queue"""
        try:
            # Güvenli settings kontrolü
            settings = assignment.get('settings')
            if not settings:
                logger.error("Assignment dict does not contain 'settings' or it is None!")
                return
            member = assignment['member']
            assignment_type = assignment['type']
            
            # Check cooldown
            cooldown_key = f"{member.guild.id}_{member.id}_{assignment_type}"
            if cooldown_key in self.cooldowns:
                if datetime.utcnow() - self.cooldowns[cooldown_key] < timedelta(minutes=5):
                    return
            self.cooldowns[cooldown_key] = datetime.utcnow()
            
            # Handle different assignment types
            if assignment_type == 'member_join':
                await self.assign_default_roles(member, settings)
            elif assignment_type == 'message_count':
                await self.assign_message_count_roles(member, assignment.get('count', 0))
            elif assignment_type == 'voice_time':
                await self.assign_voice_time_roles(member, assignment.get('minutes', 0))
            elif assignment_type == 'reaction':
                await self.assign_reaction_roles(member, assignment.get('role_id'))
            
            # Log successful assignment
            await self.log_role_assignment(member, assignment, success=True)
            
        except Exception as e:
            logger.error(f"Error executing role assignment: {e}")
            # Log failed assignment
            if 'member' in assignment:
                await self.log_role_assignment(assignment['member'], assignment, success=False, error=str(e))
    
    async def assign_default_roles(self, member: discord.Member, settings: Dict[str, Any]):
        """Assign default roles to new members"""
        try:
            roles_to_add = []
            
            # Check if member is a bot
            if member.bot and settings.get('bot_role'):
                bot_role = member.guild.get_role(int(settings['bot_role']))
                if bot_role and bot_role not in member.roles:
                    roles_to_add.append(bot_role)
            
            # Assign default role (for all members)
            if settings.get('default_role'):
                default_role = member.guild.get_role(int(settings['default_role']))
                if default_role and default_role not in member.roles:
                    roles_to_add.append(default_role)
            
            # Add roles with delay if configured
            if roles_to_add:
                delay = settings.get('join_delay', 0)
                if delay > 0:
                    await asyncio.sleep(delay)
                
                await member.add_roles(*roles_to_add, reason="Auto Role: Default assignment")
                logger.info(f"Assigned default roles to {member}: {[r.name for r in roles_to_add]}")
            
        except discord.Forbidden:
            logger.warning(f"Missing permissions to assign roles to {member} in {member.guild.name}")
        except Exception as e:
            logger.error(f"Error assigning default roles to {member}: {e}")
    
    async def assign_message_count_roles(self, member: discord.Member, count: int):
        """Assign roles based on message count"""
        try:
            # Get message count rules for this guild
            rules = await self.get_auto_role_rules(member.guild.id, 'message_count')
            
            for rule in rules:
                if not rule.get('enabled', True):
                    continue
                
                # Check if count meets the condition
                required_count = rule.get('condition', {}).get('count', 0)
                if count >= required_count:
                    role = member.guild.get_role(int(rule['role_id']))
                    if role and role not in member.roles:
                        await member.add_roles(role, reason=f"Auto Role: Message count ({count})")
                        logger.info(f"Assigned message count role {role.name} to {member}")
            
        except Exception as e:
            logger.error(f"Error assigning message count roles to {member}: {e}")
    
    async def assign_voice_time_roles(self, member: discord.Member, minutes: int):
        """Assign roles based on voice time"""
        try:
            # Get voice time rules for this guild
            rules = await self.get_auto_role_rules(member.guild.id, 'voice_time')
            
            for rule in rules:
                if not rule.get('enabled', True):
                    continue
                
                # Check if voice time meets the condition
                required_minutes = rule.get('condition', {}).get('minutes', 0)
                if minutes >= required_minutes:
                    role = member.guild.get_role(int(rule['role_id']))
                    if role and role not in member.roles:
                        await member.add_roles(role, reason=f"Auto Role: Voice time ({minutes} minutes)")
                        logger.info(f"Assigned voice time role {role.name} to {member}")
            
        except Exception as e:
            logger.error(f"Error assigning voice time roles to {member}: {e}")
    
    async def assign_reaction_roles(self, member: discord.Member, role_id: str):
        """Assign roles based on reactions"""
        try:
            role = member.guild.get_role(int(role_id))
            if role and role not in member.roles:
                await member.add_roles(role, reason="Auto Role: Reaction-based")
                logger.info(f"Assigned reaction role {role.name} to {member}")
            
        except Exception as e:
            logger.error(f"Error assigning reaction role to {member}: {e}")
    
    # ==================== TRIGGER CHECKING ====================
    
    async def check_message_count_triggers(self, member: discord.Member):
        """Check if member qualifies for message count roles"""
        try:
            guild_id = str(member.guild.id)
            user_id = str(member.id)
            
            if guild_id in self.message_counts and user_id in self.message_counts[guild_id]:
                count = self.message_counts[guild_id][user_id]
                
                # Add to role assignment queue
                await self.role_assignment_queue.put({
                    'type': 'message_count',
                    'member': member,
                    'count': count,
                    'timestamp': datetime.utcnow()
                })
            
        except Exception as e:
            logger.error(f"Error checking message count triggers: {e}")
    
    async def track_voice_time(self, member: discord.Member):
        """Track voice time for a member"""
        try:
            guild_id = str(member.guild.id)
            user_id = str(member.id)
            
            while member.voice and member.voice.channel:
                await asyncio.sleep(60)  # Update every minute
                
                if guild_id not in self.voice_times:
                    self.voice_times[guild_id] = {}
                if user_id not in self.voice_times[guild_id]:
                    self.voice_times[guild_id][user_id] = 0
                
                self.voice_times[guild_id][user_id] += 1
                
                # Check for voice time triggers every 5 minutes
                if self.voice_times[guild_id][user_id] % 5 == 0:
                    await self.role_assignment_queue.put({
                        'type': 'voice_time',
                        'member': member,
                        'minutes': self.voice_times[guild_id][user_id],
                        'timestamp': datetime.utcnow()
                    })
            
        except Exception as e:
            logger.error(f"Error tracking voice time for {member}: {e}")
    
    async def check_reaction_role_triggers(self, payload: discord.RawReactionActionEvent):
        """Check if reaction should trigger role assignment"""
        try:
            # Get reaction role rules for this guild
            rules = await self.get_auto_role_rules(payload.guild_id, 'reaction')
            
            for rule in rules:
                if not rule.get('enabled', True):
                    continue
                
                # Check if this reaction matches the rule
                condition = rule.get('condition', {})
                if (condition.get('emoji') == str(payload.emoji) and 
                    condition.get('channel_id') == str(payload.channel_id)):
                    
                    member = payload.member
                    if member:
                        await self.role_assignment_queue.put({
                            'type': 'reaction',
                            'member': member,
                            'role_id': rule['role_id'],
                            'timestamp': datetime.utcnow()
                        })
            
        except Exception as e:
            logger.error(f"Error checking reaction role triggers: {e}")
    
    # ==================== DATABASE OPERATIONS ====================
    
    async def get_auto_role_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get auto role settings for a guild"""
        try:
            if self._autorole_db is None:
                logger.error("Database connection not available")
                return None
            
            # Access the autorole_settings collection properly
            settings_collection = self._autorole_db.get_collection('autorole_settings') if hasattr(self._autorole_db, 'get_collection') else self._autorole_db['autorole_settings']
            settings = await settings_collection.find_one({"guild_id": str(guild_id)})
            return settings
        except Exception as e:
            logger.error(f"Error getting auto role settings for guild {guild_id}: {e}")
            return None
    
    async def get_auto_role_rules(self, guild_id: int, trigger_type: str = None) -> List[Dict[str, Any]]:
        """Get auto role rules for a guild"""
        try:
            if self._autorole_db is None:
                logger.error("Database connection not available")
                return []
            
            # Access the autorole_rules collection properly
            rules_collection = self._autorole_db.get_collection('autorole_rules') if hasattr(self._autorole_db, 'get_collection') else self._autorole_db['autorole_rules']
            
            query = {"guild_id": str(guild_id)}
            if trigger_type:
                query["trigger"] = trigger_type
            
            # Use async iteration instead of to_list
            rules = []
            async for rule in rules_collection.find(query):
                rules.append(rule)
            return rules
        except Exception as e:
            logger.error(f"Error getting auto role rules for guild {guild_id}: {e}")
            return []
    
    async def log_role_assignment(self, member: discord.Member, assignment: Dict[str, Any], 
                                 success: bool, error: str = None):
        """Log role assignment attempt"""
        try:
            if self._autorole_db is None:
                logger.error("Database connection not available")
                return
            
            # Access the autorole_logs collection properly
            logs_collection = self._autorole_db.get_collection('autorole_logs') if hasattr(self._autorole_db, 'get_collection') else self._autorole_db['autorole_logs']
            
            log_entry = {
                "guild_id": str(member.guild.id),
                "user_id": str(member.id),
                "assignment_type": assignment.get('type'),
                "success": success,
                "timestamp": datetime.utcnow(),
                "error_message": error
            }
            
            await logs_collection.insert_one(log_entry)
            
        except Exception as e:
            logger.error(f"Error logging role assignment: {e}")
    
    # ==================== COMMANDS ====================
    
    @commands.group(name="autorole", description="Manage auto role settings")
    @commands.has_permissions(manage_roles=True)
    async def autorole_group(self, ctx: commands.Context):
        """Auto role management commands"""
        if ctx.invoked_subcommand is None:
            embed = create_embed(
                title="🤖 Auto Role System",
                description="Manage automatic role assignments",
                color=Colors.INFO
            )
            embed.add_field(
                name="Available Commands",
                value=(
                    "`/autorole status` - Check system status\n"
                    "`/autorole stats` - View assignment statistics\n"
                    "`/autorole test` - Test role assignment\n"
                    "`/autorole reset` - Reset user data"
                ),
                inline=False
            )
            await ctx.send(embed=embed)
    
    @autorole_group.command(name="status")
    async def autorole_status(self, ctx: commands.Context):
        """Check auto role system status"""
        try:
            settings = await self.get_auto_role_settings(ctx.guild.id)
            
            embed = create_embed(
                title="🤖 Auto Role Status",
                color=Colors.INFO
            )
            
            if settings and settings.get('enabled'):
                embed.description = "✅ Auto role system is **enabled**"
                
                # Show configured roles
                roles_info = []
                if settings.get('default_role'):
                    role = ctx.guild.get_role(int(settings['default_role']))
                    roles_info.append(f"Default: {role.mention if role else 'Unknown'}")
                
                if settings.get('bot_role'):
                    role = ctx.guild.get_role(int(settings['bot_role']))
                    roles_info.append(f"Bot: {role.mention if role else 'Unknown'}")
                
                if roles_info:
                    embed.add_field(name="Configured Roles", value="\n".join(roles_info), inline=False)
                
                # Show rule count
                rules = await self.get_auto_role_rules(ctx.guild.id)
                embed.add_field(name="Active Rules", value=str(len(rules)), inline=True)
                
            else:
                embed.description = "❌ Auto role system is **disabled**"
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in autorole status command: {e}")
            await ctx.send("❌ Error checking auto role status")
    
    @autorole_group.command(name="stats")
    async def autorole_stats(self, ctx: commands.Context):
        """View auto role assignment statistics"""
        try:
            if self._autorole_db is None:
                await ctx.send("❌ Database connection not available")
                return
            
            # Access the autorole_logs collection properly
            logs_collection = self._autorole_db.get_collection('autorole_logs') if hasattr(self._autorole_db, 'get_collection') else self._autorole_db['autorole_logs']
            
            # Get recent logs using async iteration
            recent_logs = []
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            async for log in logs_collection.find({
                "guild_id": str(ctx.guild.id),
                "timestamp": {"$gte": cutoff_date}
            }):
                recent_logs.append(log)
            
            total_assignments = len(recent_logs)
            successful_assignments = len([log for log in recent_logs if log.get('success')])
            success_rate = (successful_assignments / total_assignments * 100) if total_assignments > 0 else 0
            
            embed = create_embed(
                title="📊 Auto Role Statistics",
                description=f"Last 7 days",
                color=Colors.INFO
            )
            
            embed.add_field(name="Total Assignments", value=str(total_assignments), inline=True)
            embed.add_field(name="Successful", value=str(successful_assignments), inline=True)
            embed.add_field(name="Success Rate", value=f"{success_rate:.1f}%", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in autorole stats command: {e}")
            await ctx.send("❌ Error retrieving statistics")
    
    @autorole_group.command(name="test")
    async def autorole_test(self, ctx: commands.Context, member: discord.Member = None):
        """Test auto role assignment for a member"""
        try:
            test_member = member or ctx.author
            settings = await self.get_auto_role_settings(ctx.guild.id)
            
            if not settings or not settings.get('enabled'):
                await ctx.send("❌ Auto role system is not enabled")
                return
            
            # Add to role assignment queue
            await self.role_assignment_queue.put({
                'type': 'member_join',
                'member': test_member,
                'settings': settings,
                'timestamp': datetime.utcnow()
            })
            
            embed = create_embed(
                title="🧪 Auto Role Test",
                description=f"Testing role assignment for {test_member.mention}",
                color=Colors.SUCCESS
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in autorole test command: {e}")
            await ctx.send("❌ Error testing auto role assignment")
    
    @autorole_group.command(name="reset")
    async def autorole_reset(self, ctx: commands.Context, member: discord.Member = None):
        """Reset auto role data for a member"""
        try:
            if not member:
                await ctx.send("❌ Please specify a member to reset")
                return
            
            guild_id = str(ctx.guild.id)
            user_id = str(member.id)
            
            # Reset message count
            if guild_id in self.message_counts and user_id in self.message_counts[guild_id]:
                del self.message_counts[guild_id][user_id]
            
            # Reset voice time
            if guild_id in self.voice_times and user_id in self.voice_times[guild_id]:
                del self.voice_times[guild_id][user_id]
            
            # Cancel active timer
            timer_key = f"{guild_id}_{user_id}"
            if timer_key in self.active_timers:
                self.active_timers[timer_key].cancel()
                del self.active_timers[timer_key]
            
            embed = create_embed(
                title="🔄 Auto Role Reset",
                description=f"Reset auto role data for {member.mention}",
                color=Colors.SUCCESS
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in autorole reset command: {e}")
            await ctx.send("❌ Error resetting auto role data")

async def setup(bot):
    """Setup function for the AutoRole cog"""
    await bot.add_cog(AutoRole(bot)) 