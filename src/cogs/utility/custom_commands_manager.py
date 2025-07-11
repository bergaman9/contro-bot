import asyncio
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import discord
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
import uuid
from src.core.logger import LoggerMixin

class CustomCommandsManager(commands.Cog, LoggerMixin):
    """Advanced Custom Commands System with scheduling, auto-responses, and event handling"""
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = None  # Will be initialized in cog_load
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        self.command_cache = {}  # Cache for guild commands
        self.cooldown_cache = {}  # Cache for cooldowns
        self.variable_cache = {}  # Cache for dynamic variables
        
    async def cog_load(self):
        """Load all scheduled commands on startup"""
        # Initialize database connection
        from src.utils.core.manager import get_async_database
        self.mongo_db = await get_async_database()
        
        await self.load_scheduled_commands()
        self.cleanup_cooldowns.start()
        
    async def cog_unload(self):
        """Cleanup on cog unload"""
        self.cleanup_cooldowns.cancel()
        self.scheduler.shutdown()
        
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle text-based commands and auto-responses"""
        if message.author.bot:
            return
            
        await self.process_text_commands(message)
        await self.process_auto_responses(message)
        
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member join events"""
        await self.process_event_commands('member_join', member=member)
        
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle member leave events"""
        await self.process_event_commands('member_leave', member=member)
        
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reaction events"""
        if user.bot:
            return
        await self.process_event_commands('reaction_add', reaction=reaction, user=user)
        
    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        """Handle reaction remove events"""
        if user.bot:
            return
        await self.process_event_commands('reaction_remove', reaction=reaction, user=user)
        
    async def process_text_commands(self, message):
        """Process text-based commands"""
        guild_id = str(message.guild.id)
        
        # Get commands for this guild
        commands = await self.get_guild_commands(guild_id)
        if not commands:
            return
            
        text_commands = [cmd for cmd in commands if cmd['type'] == 'text_command' and cmd['enabled']]
        
        for command in text_commands:
            if await self.should_trigger_command(command, message):
                await self.execute_command(command, message)
                
    async def process_auto_responses(self, message):
        """Process auto-response commands"""
        guild_id = str(message.guild.id)
        
        commands = await self.get_guild_commands(guild_id)
        if not commands:
            return
            
        auto_commands = [cmd for cmd in commands if cmd['type'] == 'auto_response' and cmd['enabled']]
        
        for command in auto_commands:
            if await self.should_trigger_auto_response(command, message):
                await self.execute_command(command, message)
                
    async def process_event_commands(self, event_type: str, **kwargs):
        """Process event-based commands"""
        guild_id = str(kwargs.get('member', kwargs.get('reaction', kwargs.get('user'))).guild.id)
        
        commands = await self.get_guild_commands(guild_id)
        if not commands:
            return
            
        event_commands = [cmd for cmd in commands if cmd['type'] == 'event_command' and cmd['enabled']]
        
        for command in event_commands:
            if event_type in command['trigger'].get('events', []):
                if await self.should_trigger_event_command(command, event_type, **kwargs):
                    await self.execute_command(command, None, event_type=event_type, **kwargs)
                    
    async def should_trigger_command(self, command: Dict, message) -> bool:
        """Check if a text command should be triggered"""
        trigger = command['trigger']
        content = message.content.lower()
        
        # Check prefix
        if 'prefix' in trigger and not content.startswith(trigger['prefix'].lower()):
            return False
            
        # Check exact match
        if 'exact_match' in trigger and content != trigger['exact_match'].lower():
            return False
            
        # Check contains
        if 'contains' in trigger:
            if not any(keyword.lower() in content for keyword in trigger['contains']):
                return False
                
        # Check regex
        if 'regex' in trigger:
            try:
                if not re.search(trigger['regex'], content, re.IGNORECASE):
                    return False
            except re.error:
                return False
                
        # Check permissions
        if not await self.check_permissions(command, message.author, message.channel):
            return False
            
        # Check cooldown
        if not await self.check_cooldown(command, message.author, message.channel):
            return False
            
        return True
        
    async def should_trigger_auto_response(self, command: Dict, message) -> bool:
        """Check if an auto-response should be triggered"""
        trigger = command['trigger']
        content = message.content.lower()
        
        # Check keywords
        if 'keywords' in trigger:
            if not any(keyword.lower() in content for keyword in trigger['keywords']):
                return False
                
        # Check user IDs
        if 'user_ids' in trigger and str(message.author.id) not in trigger['user_ids']:
            return False
            
        # Check role IDs
        if 'role_ids' in trigger:
            user_roles = [str(role.id) for role in message.author.roles]
            if not any(role_id in user_roles for role_id in trigger['role_ids']):
                return False
                
        # Check channel IDs
        if 'channel_ids' in trigger and str(message.channel.id) not in trigger['channel_ids']:
            return False
            
        # Check conditions
        if 'conditions' in trigger:
            if not await self.check_conditions(command['trigger']['conditions'], message):
                return False
                
        # Check cooldown
        if not await self.check_cooldown(command, message.author, message.channel):
            return False
            
        return True
        
    async def should_trigger_event_command(self, command: Dict, event_type: str, **kwargs) -> bool:
        """Check if an event command should be triggered"""
        # Check permissions
        user = kwargs.get('user', kwargs.get('member'))
        channel = kwargs.get('channel')
        
        if not await self.check_permissions(command, user, channel):
            return False
            
        # Check conditions
        if 'conditions' in command['trigger']:
            if not await self.check_conditions(command['trigger']['conditions'], **kwargs):
                return False
                
        return True
        
    async def check_permissions(self, command: Dict, user, channel) -> bool:
        """Check if user has permission to use command"""
        permissions = command['permissions']
        
        # Check admin only
        if permissions.get('admin_only', False):
            if not user.guild_permissions.administrator:
                return False
                
        # Check everyone permission
        if permissions.get('everyone', True):
            return True
            
        # Check specific roles
        if permissions.get('roles'):
            user_roles = [str(role.id) for role in user.roles]
            if any(role_id in user_roles for role_id in permissions['roles']):
                return True
                
        # Check specific users
        if permissions.get('users') and str(user.id) in permissions['users']:
            return True
            
        return False
        
    async def check_cooldown(self, command: Dict, user, channel) -> bool:
        """Check command cooldown"""
        cooldown = command.get('cooldown', {})
        if not cooldown.get('enabled', False):
            return True
            
        cooldown_key = f"{command['id']}:{user.id}"
        if cooldown.get('per_channel', False):
            cooldown_key += f":{channel.id}"
            
        current_time = datetime.now()
        last_used = self.cooldown_cache.get(cooldown_key)
        
        if last_used:
            time_diff = (current_time - last_used).total_seconds()
            if time_diff < cooldown.get('seconds', 0):
                return False
                
        self.cooldown_cache[cooldown_key] = current_time
        return True
        
    async def check_conditions(self, conditions: Dict, **kwargs) -> bool:
        """Check conditional triggers"""
        message = kwargs.get('message')
        user = kwargs.get('user', kwargs.get('member'))
        
        # Check user has role
        if 'user_has_role' in conditions:
            user_roles = [str(role.id) for role in user.roles]
            if not any(role_id in user_roles for role_id in conditions['user_has_role']):
                return False
                
        # Check user in channel
        if 'user_in_channel' in conditions:
            if not any(str(channel.id) in conditions['user_in_channel'] for channel in user.guild.channels):
                return False
                
        # Check message length
        if 'message_length' in conditions and message:
            msg_len = len(message.content)
            min_len = conditions['message_length'].get('min', 0)
            max_len = conditions['message_length'].get('max', float('inf'))
            if not (min_len <= msg_len <= max_len):
                return False
                
        # Check time between
        if 'time_between' in conditions:
            current_time = datetime.now().time()
            start_time = datetime.strptime(conditions['time_between']['start'], '%H:%M').time()
            end_time = datetime.strptime(conditions['time_between']['end'], '%H:%M').time()
            
            if start_time <= end_time:
                if not (start_time <= current_time <= end_time):
                    return False
            else:  # Overnight range
                if not (current_time >= start_time or current_time <= end_time):
                    return False
                    
        # Check day of week
        if 'day_of_week' in conditions:
            current_day = datetime.now().weekday()
            if current_day not in conditions['day_of_week']:
                return False
                
        return True
        
    async def execute_command(self, command: Dict, message=None, **kwargs):
        """Execute command response"""
        start_time = datetime.now()
        
        try:
            response = command['response']
            response_type = response.get('type', 'text')
            
            # Get context for variable replacement
            context = await self.build_context(command, message, **kwargs)
            
            if response_type == 'text':
                await self.execute_text_response(response, context)
            elif response_type == 'embed':
                await self.execute_embed_response(response, context)
            elif response_type == 'action':
                await self.execute_action_response(response, context)
            elif response_type == 'multi_step':
                await self.execute_multi_step_response(response, context)
            elif response_type == 'file':
                await self.execute_file_response(response, context)
                
            # Update usage statistics
            await self.update_command_stats(command['id'], start_time)
            
        except Exception as e:
            await self.log_command_error(command['id'], str(e))
            
    async def execute_text_response(self, response: Dict, context: Dict):
        """Execute text response"""
        content = response.get('content', '')
        content = await self.replace_variables(content, context)
        
        if context.get('channel'):
            await context['channel'].send(content)
            
    async def execute_embed_response(self, response: Dict, context: Dict):
        """Execute embed response"""
        embed_data = response.get('embed', {})
        
        embed = discord.Embed()
        
        if 'title' in embed_data:
            embed.title = await self.replace_variables(embed_data['title'], context)
        if 'description' in embed_data:
            embed.description = await self.replace_variables(embed_data['description'], context)
        if 'color' in embed_data:
            embed.color = int(embed_data['color'].replace('#', ''), 16)
        if 'thumbnail' in embed_data:
            embed.set_thumbnail(url=await self.replace_variables(embed_data['thumbnail'], context))
        if 'image' in embed_data:
            embed.set_image(url=await self.replace_variables(embed_data['image'], context))
        if 'footer' in embed_data:
            footer_text = await self.replace_variables(embed_data['footer']['text'], context)
            footer_icon = await self.replace_variables(embed_data['footer'].get('icon', ''), context)
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            
        # Add fields
        for field in embed_data.get('fields', []):
            name = await self.replace_variables(field['name'], context)
            value = await self.replace_variables(field['value'], context)
            embed.add_field(name=name, value=value, inline=field.get('inline', False))
            
        if context.get('channel'):
            await context['channel'].send(embed=embed)
            
    async def execute_action_response(self, response: Dict, context: Dict):
        """Execute action response"""
        actions = response.get('actions', [])
        
        for action in actions:
            action_type = action['type']
            target = action['target']
            value = action['value']
            duration = action.get('duration')
            
            if action_type == 'add_role':
                await self.add_role_action(context, value, duration)
            elif action_type == 'remove_role':
                await self.remove_role_action(context, value)
            elif action_type == 'kick_user':
                await self.kick_user_action(context)
            elif action_type == 'ban_user':
                await self.ban_user_action(context, duration)
            elif action_type == 'send_dm':
                await self.send_dm_action(context, value)
                
    async def execute_multi_step_response(self, response: Dict, context: Dict):
        """Execute multi-step response"""
        steps = response.get('steps', [])
        
        for step in steps:
            delay = step.get('delay_seconds', 0)
            if delay > 0:
                await asyncio.sleep(delay)
                
            step_response = step.get('response', {})
            if step_response.get('type') == 'text':
                await self.execute_text_response(step_response, context)
            elif step_response.get('type') == 'embed':
                await self.execute_embed_response(step_response, context)
            elif step_response.get('type') == 'action':
                await self.execute_action_response(step_response, context)
                
    async def execute_file_response(self, response: Dict, context: Dict):
        """Execute file response"""
        file_url = response.get('file_url', '')
        file_url = await self.replace_variables(file_url, context)
        
        if context.get('channel'):
            await context['channel'].send(file=discord.File(file_url))
            
    async def add_role_action(self, context: Dict, role_id: str, duration: Optional[int] = None):
        """Add role to user"""
        user = context.get('user')
        guild = context.get('guild')
        
        if user and guild:
            role = guild.get_role(int(role_id))
            if role:
                await user.add_roles(role)
                
                if duration:
                    # Schedule role removal
                    asyncio.create_task(self.remove_role_after_delay(user, role, duration))
                    
    async def remove_role_action(self, context: Dict, role_id: str):
        """Remove role from user"""
        user = context.get('user')
        guild = context.get('guild')
        
        if user and guild:
            role = guild.get_role(int(role_id))
            if role:
                await user.remove_roles(role)
                
    async def kick_user_action(self, context: Dict):
        """Kick user from guild"""
        user = context.get('user')
        guild = context.get('guild')
        
        if user and guild:
            await guild.kick(user)
            
    async def ban_user_action(self, context: Dict, duration: Optional[int] = None):
        """Ban user from guild"""
        user = context.get('user')
        guild = context.get('guild')
        
        if user and guild:
            await guild.ban(user, delete_message_days=1)
            
            if duration:
                # Schedule unban
                asyncio.create_task(self.unban_user_after_delay(guild, user, duration))
                
    async def send_dm_action(self, context: Dict, message: str):
        """Send DM to user"""
        user = context.get('user')
        
        if user:
            message = await self.replace_variables(message, context)
            await user.send(message)
            
    async def remove_role_after_delay(self, user, role, delay_seconds: int):
        """Remove role after delay"""
        await asyncio.sleep(delay_seconds)
        await user.remove_roles(role)
        
    async def unban_user_after_delay(self, guild, user, delay_seconds: int):
        """Unban user after delay"""
        await asyncio.sleep(delay_seconds)
        await guild.unban(user)
        
    async def replace_variables(self, text: str, context: Dict) -> str:
        """Replace variables in text with actual values"""
        variables = {
            '{user}': context.get('user', {}).display_name if context.get('user') else '',
            '{user_mention}': context.get('user', {}).mention if context.get('user') else '',
            '{user_id}': str(context.get('user', {}).id) if context.get('user') else '',
            '{user_avatar}': str(context.get('user', {}).avatar.url) if context.get('user') and context.get('user').avatar else '',
            '{server_name}': context.get('guild', {}).name if context.get('guild') else '',
            '{server_id}': str(context.get('guild', {}).id) if context.get('guild') else '',
            '{member_count}': str(context.get('guild', {}).member_count) if context.get('guild') else '',
            '{channel}': context.get('channel', {}).mention if context.get('channel') else '',
            '{channel_name}': context.get('channel', {}).name if context.get('channel') else '',
            '{message_content}': context.get('message', {}).content if context.get('message') else '',
            '{timestamp}': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '{date}': datetime.now().strftime('%Y-%m-%d'),
            '{time}': datetime.now().strftime('%H:%M:%S'),
        }
        
        for var, value in variables.items():
            text = text.replace(var, str(value))
            
        return text
        
    async def build_context(self, command: Dict, message=None, **kwargs) -> Dict:
        """Build context for command execution"""
        context = {}
        
        if message:
            context.update({
                'user': message.author,
                'guild': message.guild,
                'channel': message.channel,
                'message': message
            })
        else:
            # Event-based context
            if 'member' in kwargs:
                context.update({
                    'user': kwargs['member'],
                    'guild': kwargs['member'].guild
                })
            elif 'user' in kwargs:
                context.update({
                    'user': kwargs['user'],
                    'guild': kwargs['user'].guild
                })
                
        return context
        
    async def get_guild_commands(self, guild_id: str) -> List[Dict]:
        """Get commands for a guild from cache or database"""
        if self.mongo_db is None:
            self.logger.error("MongoDB connection is not initialized in get_guild_commands.")
            return []
        if guild_id in self.command_cache:
            return self.command_cache[guild_id]
            
        try:
            collection = self.mongo_db.custom_commands
            if collection is None:
                self.logger.error("Custom commands collection is None")
                return []
                
            guild_data = await collection.find_one({'guild_id': guild_id})
            
            if guild_data and guild_data.get('system_enabled', True):
                commands = guild_data.get('commands', [])
                self.command_cache[guild_id] = commands
                return commands
        except Exception as e:
            self.logger.error(f"Error getting guild commands for {guild_id}: {e}")
            
        return []
        
    async def load_scheduled_commands(self):
        """Load all scheduled commands into scheduler"""
        if self.mongo_db is None:
            self.logger.error("MongoDB connection is not initialized in load_scheduled_commands.")
            return
        collection = self.mongo_db.custom_commands
        
        try:
            # Handle different cursor types
            cursor = collection.find({'system_enabled': True})
            
            # Check if cursor has to_list method (async cursor)
            if hasattr(cursor, 'to_list'):
                guild_data_list = await cursor.to_list(length=None)
            else:
                # If it's already a list or sync cursor, use it directly
                guild_data_list = list(cursor) if hasattr(cursor, '__iter__') else []
            
            for guild_data in guild_data_list:
                guild_id = guild_data['guild_id']
                commands = guild_data.get('commands', [])
                
                for command in commands:
                    if command['type'] == 'scheduled_command' and command['enabled']:
                        await self.schedule_command(command, guild_id)
        except Exception as e:
            self.logger.error(f"Error loading scheduled commands: {e}")
                    
    async def schedule_command(self, command: Dict, guild_id: str):
        """Schedule a command for execution"""
        trigger = command['trigger'].get('schedule', {})
        schedule_type = trigger.get('type')
        
        job_id = f"{guild_id}_{command['id']}"
        
        try:
            if schedule_type == 'interval':
                interval = trigger.get('interval_seconds', 3600)
                self.scheduler.add_job(
                    self.execute_scheduled_command,
                    IntervalTrigger(seconds=interval),
                    args=[command, guild_id],
                    id=job_id,
                    replace_existing=True
                )
            elif schedule_type == 'daily':
                time_str = trigger.get('time', '09:00')
                hour, minute = map(int, time_str.split(':'))
                self.scheduler.add_job(
                    self.execute_scheduled_command,
                    CronTrigger(hour=hour, minute=minute),
                    args=[command, guild_id],
                    id=job_id,
                    replace_existing=True
                )
            elif schedule_type == 'weekly':
                time_str = trigger.get('time', '09:00')
                days = trigger.get('days_of_week', [0])
                hour, minute = map(int, time_str.split(':'))
                self.scheduler.add_job(
                    self.execute_scheduled_command,
                    CronTrigger(day_of_week=','.join(map(str, days)), hour=hour, minute=minute),
                    args=[command, guild_id],
                    id=job_id,
                    replace_existing=True
                )
            elif schedule_type == 'cron':
                cron_expr = trigger.get('cron_expression', '0 9 * * *')
                self.scheduler.add_job(
                    self.execute_scheduled_command,
                    CronTrigger.from_crontab(cron_expr),
                    args=[command, guild_id],
                    id=job_id,
                    replace_existing=True
                )
        except Exception as e:
            print(f"Error scheduling command {command['id']}: {e}")
            
    async def execute_scheduled_command(self, command: Dict, guild_id: str):
        """Execute a scheduled command"""
        try:
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return
                
            # Get default channel for scheduled commands
            default_channel = guild.system_channel or guild.text_channels[0]
            
            context = {
                'guild': guild,
                'channel': default_channel,
                'user': None
            }
            
            await self.execute_command(command, None, **context)
            
        except Exception as e:
            await self.log_command_error(command['id'], str(e))
            
    async def update_command_stats(self, command_id: str, start_time: datetime):
        """Update command usage statistics"""
        try:
            collection = self.mongo_db.custom_commands
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            await collection.update_one(
                {'commands.id': command_id},
                {
                    '$inc': {
                        'statistics.totalCommandsExecuted': 1,
                        'commands.$.usage_count': 1
                    },
                    '$set': {
                        'statistics.lastExecution': datetime.now(),
                        'commands.$.last_used': datetime.now()
                    }
                }
            )
            
            # Log the execution
            await self.log_command_execution(command_id, execution_time)
            
        except Exception as e:
            print(f"Error updating command stats: {e}")
            
    async def log_command_execution(self, command_id: str, execution_time: float):
        """Log command execution"""
        try:
            collection = self.mongo_db.custom_commands_logs
            await collection.insert_one({
                'command_id': command_id,
                'execution_time_ms': execution_time,
                'executed_at': datetime.now(),
                'status': 'success'
            })
        except Exception as e:
            print(f"Error logging command execution: {e}")
            
    async def log_command_error(self, command_id: str, error_message: str):
        """Log command execution error"""
        try:
            collection = self.mongo_db.custom_commands_logs
            await collection.insert_one({
                'command_id': command_id,
                'error_message': error_message,
                'executed_at': datetime.now(),
                'status': 'error'
            })
        except Exception as e:
            print(f"Error logging command error: {e}")
            
    @tasks.loop(minutes=5)
    async def cleanup_cooldowns(self):
        """Clean up expired cooldowns"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, last_used in self.cooldown_cache.items():
            # Remove cooldowns older than 1 hour
            if (current_time - last_used).total_seconds() > 3600:
                expired_keys.append(key)
                
        for key in expired_keys:
            del self.cooldown_cache[key]
            
    # Discord Commands
    @commands.group(name="customcommands", aliases=["cc"])
    @commands.has_permissions(manage_guild=True)
    async def custom_commands_group(self, ctx):
        """Custom commands management"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
            
    @custom_commands_group.command(name="list")
    async def list_commands(self, ctx):
        """List all custom commands"""
        guild_id = str(ctx.guild.id)
        commands = await self.get_guild_commands(guild_id)
        
        if not commands:
            await ctx.send("No custom commands found for this server.")
            return
            
        embed = discord.Embed(title="Custom Commands", color=0x00ff00)
        
        for cmd in commands[:10]:  # Show first 10 commands
            status = "✅" if cmd['enabled'] else "❌"
            embed.add_field(
                name=f"{status} {cmd['name']}",
                value=f"Type: {cmd['type']}\nUsage: {cmd.get('usage_count', 0)} times",
                inline=True
            )
            
        await ctx.send(embed=embed)
        
    @custom_commands_group.command(name="test")
    async def test_command(self, ctx, command_name: str):
        """Test a custom command"""
        guild_id = str(ctx.guild.id)
        commands = await self.get_guild_commands(guild_id)
        
        command = next((cmd for cmd in commands if cmd['name'].lower() == command_name.lower()), None)
        
        if not command:
            await ctx.send(f"Command '{command_name}' not found.")
            return
            
        if not command['enabled']:
            await ctx.send(f"Command '{command_name}' is disabled.")
            return
            
        # Create test message
        test_message = type('TestMessage', (), {
            'content': f"{command['trigger'].get('prefix', '!')}{command_name}",
            'author': ctx.author,
            'guild': ctx.guild,
            'channel': ctx.channel
        })()
        
        await self.execute_command(command, test_message)
        
    @custom_commands_group.command(name="stats")
    async def command_stats(self, ctx):
        """Show command statistics"""
        guild_id = str(ctx.guild.id)
        collection = self.mongo_db.custom_commands
        
        guild_data = await collection.find_one({'guild_id': guild_id})
        
        if not guild_data:
            await ctx.send("No custom commands data found for this server.")
            return
            
        stats = guild_data.get('statistics', {})
        
        embed = discord.Embed(title="Custom Commands Statistics", color=0x00ff00)
        embed.add_field(name="Total Executions", value=stats.get('totalCommandsExecuted', 0), inline=True)
        embed.add_field(name="Last Execution", value=stats.get('lastExecution', 'Never'), inline=True)
        embed.add_field(name="Average Response Time", value=f"{stats.get('averageResponseTime', 0):.2f}ms", inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CustomCommandsManager(bot)) 