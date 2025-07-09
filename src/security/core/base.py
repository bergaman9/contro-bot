"""
Base Security Framework for Contro Bot
Provides foundation classes for modular security system
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """Security alert levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ActionType(Enum):
    """Types of security actions"""
    ALLOW = "allow"
    WARN = "warn"
    TIMEOUT = "timeout"
    KICK = "kick"
    BAN = "ban"
    DELETE = "delete"
    LOCKDOWN = "lockdown"
    QUARANTINE = "quarantine"

@dataclass
class SecurityEvent:
    """Base class for security events"""
    event_id: str
    timestamp: datetime
    guild_id: int
    user_id: Optional[int]
    channel_id: Optional[int]
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    severity: SecurityLevel = SecurityLevel.LOW
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "event_type": self.event_type,
            "data": self.data,
            "severity": self.severity.value
        }

@dataclass
class SecurityResponse:
    """Response from security module"""
    action: ActionType
    reason: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    auto_resolve: bool = False
    duration: Optional[timedelta] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "auto_resolve": self.auto_resolve,
            "duration": self.duration.total_seconds() if self.duration else None
        }

@dataclass
class SecurityConfig:
    """Configuration for security modules"""
    enabled: bool = True
    sensitivity: float = 0.7
    auto_action: bool = False
    log_events: bool = True
    alert_threshold: SecurityLevel = SecurityLevel.MEDIUM
    rate_limits: Dict[str, int] = field(default_factory=dict)
    whitelist: List[int] = field(default_factory=list)
    blacklist: List[int] = field(default_factory=list)
    custom_settings: Dict[str, Any] = field(default_factory=dict)

class SecurityModule(ABC):
    """Base class for all security modules"""
    
    def __init__(self, name: str, config: SecurityConfig):
        self.name = name
        self.config = config
        self.enabled = config.enabled
        self.event_history: List[SecurityEvent] = []
        self.last_alert = datetime.min
        self.stats = {
            "events_processed": 0,
            "threats_detected": 0,
            "actions_taken": 0,
            "false_positives": 0
        }
    
    @abstractmethod
    async def process_event(self, event: SecurityEvent) -> SecurityResponse:
        """Process a security event and return response"""
        pass
    
    @abstractmethod
    async def configure(self, settings: Dict[str, Any]) -> bool:
        """Update module configuration"""
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get current module status"""
        pass
    
    def is_whitelisted(self, user_id: int) -> bool:
        """Check if user is whitelisted"""
        return user_id in self.config.whitelist
    
    def is_blacklisted(self, user_id: int) -> bool:
        """Check if user is blacklisted"""
        return user_id in self.config.blacklist
    
    def should_process_event(self, event: SecurityEvent) -> bool:
        """Determine if event should be processed"""
        if not self.enabled:
            return False
        
        if event.user_id and self.is_whitelisted(event.user_id):
            return False
        
        return True
    
    def update_stats(self, event: SecurityEvent, response: SecurityResponse):
        """Update module statistics"""
        self.stats["events_processed"] += 1
        
        if response.action != ActionType.ALLOW:
            self.stats["threats_detected"] += 1
            
        if response.action in [ActionType.TIMEOUT, ActionType.KICK, ActionType.BAN]:
            self.stats["actions_taken"] += 1
    
    def add_to_history(self, event: SecurityEvent):
        """Add event to history with size limit"""
        self.event_history.append(event)
        
        # Keep only last 1000 events
        if len(self.event_history) > 1000:
            self.event_history = self.event_history[-1000:]

class SecurityFramework:
    """Main security framework that manages all modules"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.modules: Dict[str, SecurityModule] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None
        self.alert_handlers: List[Callable] = []
        self.global_stats = {
            "total_events": 0,
            "total_threats": 0,
            "total_actions": 0,
            "modules_active": 0
        }
    
    def register_module(self, module: SecurityModule):
        """Register a security module"""
        self.modules[module.name] = module
        self.global_stats["modules_active"] = len([m for m in self.modules.values() if m.enabled])
        logger.info(f"Registered security module: {module.name}")
    
    def unregister_module(self, module_name: str):
        """Unregister a security module"""
        if module_name in self.modules:
            del self.modules[module_name]
            self.global_stats["modules_active"] = len([m for m in self.modules.values() if m.enabled])
            logger.info(f"Unregistered security module: {module_name}")
    
    async def process_event(self, event: SecurityEvent) -> List[SecurityResponse]:
        """Process event through all applicable modules"""
        responses = []
        
        for module in self.modules.values():
            if not module.should_process_event(event):
                continue
            
            try:
                response = await module.process_event(event)
                responses.append(response)
                
                module.update_stats(event, response)
                module.add_to_history(event)
                
                # Handle critical responses immediately
                if response.action in [ActionType.BAN, ActionType.LOCKDOWN]:
                    await self.execute_response(event, response)
                    
            except Exception as e:
                logger.error(f"Error in security module {module.name}: {e}")
                continue
        
        self.global_stats["total_events"] += 1
        return responses
    
    async def execute_response(self, event: SecurityEvent, response: SecurityResponse):
        """Execute a security response"""
        try:
            guild = self.bot.get_guild(event.guild_id)
            if not guild:
                return
            
            if event.user_id:
                member = guild.get_member(event.user_id)
                if not member:
                    return
            
            if response.action == ActionType.TIMEOUT and member:
                duration = response.duration or timedelta(minutes=10)
                await member.timeout(duration, reason=response.reason)
                
            elif response.action == ActionType.KICK and member:
                await member.kick(reason=response.reason)
                
            elif response.action == ActionType.BAN and member:
                duration = response.duration or None
                delete_days = response.metadata.get("delete_message_days", 0)
                await member.ban(reason=response.reason, delete_message_days=delete_days)
                
            elif response.action == ActionType.DELETE and event.channel_id:
                channel = guild.get_channel(event.channel_id)
                if channel and hasattr(channel, 'history'):
                    message_id = event.data.get("message_id")
                    if message_id:
                        try:
                            message = await channel.fetch_message(message_id)
                            await message.delete()
                        except discord.NotFound:
                            pass
                            
            elif response.action == ActionType.LOCKDOWN:
                # Implement server lockdown
                await self.execute_lockdown(guild, response)
                
            self.global_stats["total_actions"] += 1
            
        except Exception as e:
            logger.error(f"Error executing security response: {e}")
    
    async def execute_lockdown(self, guild: discord.Guild, response: SecurityResponse):
        """Execute server lockdown"""
        try:
            # Save current permissions
            lockdown_data = {
                "timestamp": datetime.now().isoformat(),
                "reason": response.reason,
                "original_permissions": {}
            }
            
            # Lock down text channels
            for channel in guild.text_channels:
                if not channel.permissions_for(guild.me).manage_permissions:
                    continue
                    
                # Save original permissions
                lockdown_data["original_permissions"][str(channel.id)] = {}
                
                overwrites = channel.overwrites
                for target, overwrite in overwrites.items():
                    if isinstance(target, discord.Role) and target.name == "@everyone":
                        # Save original permissions
                        lockdown_data["original_permissions"][str(channel.id)]["everyone"] = {
                            "send_messages": overwrite.send_messages,
                            "add_reactions": overwrite.add_reactions,
                            "create_public_threads": overwrite.create_public_threads
                        }
                        
                        # Apply lockdown
                        overwrite.send_messages = False
                        overwrite.add_reactions = False
                        overwrite.create_public_threads = False
                        
                        await channel.set_permissions(target, overwrite=overwrite, reason="Security lockdown")
            
            # Store lockdown data for restoration
            # This would typically be saved to database
            response.metadata["lockdown_data"] = lockdown_data
            
            logger.warning(f"Server lockdown executed for guild {guild.id}: {response.reason}")
            
        except Exception as e:
            logger.error(f"Error executing lockdown: {e}")
    
    def add_alert_handler(self, handler: Callable):
        """Add alert handler function"""
        self.alert_handlers.append(handler)
    
    async def send_alert(self, event: SecurityEvent, responses: List[SecurityResponse]):
        """Send security alerts to handlers"""
        for handler in self.alert_handlers:
            try:
                await handler(event, responses)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    
    async def start_processing(self):
        """Start event processing task"""
        if self.processing_task and not self.processing_task.done():
            return
            
        self.processing_task = asyncio.create_task(self._process_queue())
        logger.info("Security framework processing started")
    
    async def stop_processing(self):
        """Stop event processing task"""
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Security framework processing stopped")
    
    async def _process_queue(self):
        """Process events from queue"""
        while True:
            try:
                event = await self.event_queue.get()
                responses = await self.process_event(event)
                
                # Send alerts for significant responses
                significant_responses = [r for r in responses if r.action != ActionType.ALLOW]
                if significant_responses:
                    await self.send_alert(event, significant_responses)
                    
                self.event_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing security event: {e}")
    
    async def queue_event(self, event: SecurityEvent):
        """Add event to processing queue"""
        await self.event_queue.put(event)
    
    def get_framework_status(self) -> Dict[str, Any]:
        """Get overall framework status"""
        return {
            "modules_registered": len(self.modules),
            "modules_active": len([m for m in self.modules.values() if m.enabled]),
            "processing_active": self.processing_task and not self.processing_task.done(),
            "queue_size": self.event_queue.qsize(),
            "global_stats": self.global_stats,
            "module_stats": {name: module.stats for name, module in self.modules.items()}
        }

# Rate limiting utility
class RateLimiter:
    """Rate limiting utility for security modules"""
    
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[int, List[float]] = {}
    
    def is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited"""
        now = time.time()
        
        if user_id not in self.attempts:
            self.attempts[user_id] = []
        
        # Clean old attempts
        self.attempts[user_id] = [
            attempt for attempt in self.attempts[user_id]
            if now - attempt < self.window_seconds
        ]
        
        return len(self.attempts[user_id]) >= self.max_attempts
    
    def add_attempt(self, user_id: int):
        """Add attempt for user"""
        now = time.time()
        
        if user_id not in self.attempts:
            self.attempts[user_id] = []
        
        self.attempts[user_id].append(now)
    
    def get_remaining_time(self, user_id: int) -> int:
        """Get remaining cooldown time in seconds"""
        if user_id not in self.attempts or not self.attempts[user_id]:
            return 0
        
        oldest_attempt = min(self.attempts[user_id])
        elapsed = time.time() - oldest_attempt
        remaining = self.window_seconds - elapsed
        
        return max(0, int(remaining)) 