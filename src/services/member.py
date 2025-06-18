"""Member service for business logic."""
from typing import Optional, List, Dict, Any, Tuple
from .base import BaseService
from ..database.collections import MemberCollection
from ..database.models import Member
import discord


class MemberService(BaseService):
    """Service for member-related operations."""
    
    def __init__(self, db):
        """Initialize member service."""
        super().__init__(db)
        self.member_collection = MemberCollection(db)
    
    async def get_member(self, guild_id: int, user_id: int) -> Optional[Member]:
        """Get member by guild and user ID."""
        try:
            return await self.member_collection.find_by_ids(guild_id, user_id)
        except Exception as e:
            self.log_error(f"Error getting member {user_id} in guild {guild_id}", exc_info=e)
            return None
    
    async def ensure_member_exists(self, guild_id: int, user_id: int) -> Member:
        """Ensure member exists in database."""
        try:
            return await self.member_collection.get_or_create(guild_id, user_id)
        except Exception as e:
            self.log_error(f"Error ensuring member exists: {user_id} in guild {guild_id}", exc_info=e)
            raise
    
    async def add_xp(self, guild_id: int, user_id: int, amount: int) -> Optional[Tuple[int, int]]:
        """Add XP to member and return new XP and level."""
        try:
            result = await self.member_collection.add_xp(guild_id, user_id, amount)
            if result:
                new_xp, new_level = result
                self.log_info(f"Added {amount} XP to member {user_id} in guild {guild_id}. New: {new_xp} XP, Level {new_level}")
            return result
        except Exception as e:
            self.log_error(f"Error adding XP to member {user_id} in guild {guild_id}", exc_info=e)
            return None
    
    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> List[Member]:
        """Get guild XP leaderboard."""
        try:
            return await self.member_collection.get_top_members_by_xp(guild_id, limit)
        except Exception as e:
            self.log_error(f"Error getting leaderboard for guild {guild_id}", exc_info=e)
            return []
    
    async def increment_message_count(self, guild_id: int, user_id: int):
        """Increment message count for a member."""
        try:
            await self.member_collection.increment_message_count(guild_id, user_id)
        except Exception as e:
            self.log_error(f"Error incrementing message count for {user_id} in guild {guild_id}", exc_info=e)
    
    async def add_warning(self, guild_id: int, user_id: int, reason: str, moderator_id: int) -> bool:
        """Add a warning to member."""
        try:
            success = await self.member_collection.add_warning(guild_id, user_id, reason, moderator_id)
            if success:
                self.log_info(f"Added warning to member {user_id} in guild {guild_id}: {reason}")
            return success
        except Exception as e:
            self.log_error(f"Error adding warning to member {user_id} in guild {guild_id}", exc_info=e)
            return False
    
    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Get member warnings."""
        member = await self.get_member(guild_id, user_id)
        return member.warnings if member else []
    
    async def get_members_with_warnings(self, guild_id: int) -> List[Member]:
        """Get all members with warnings in a guild."""
        try:
            return await self.member_collection.get_members_with_warnings(guild_id)
        except Exception as e:
            self.log_error(f"Error getting members with warnings in guild {guild_id}", exc_info=e)
            return []
    
    async def get_member_stats(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Get member statistics."""
        member = await self.get_member(guild_id, user_id)
        if not member:
            return {
                'exists': False,
                'xp': 0,
                'level': 0,
                'total_messages': 0,
                'warnings': [],
                'warning_count': 0
            }
        
        from ..database.models.user import User
        return {
            'exists': True,
            'xp': member.xp,
            'level': member.level,
            'total_messages': member.total_messages,
            'warnings': member.warnings,
            'warning_count': len(member.warnings),
            'next_level_xp': User.xp_for_next_level(member.level),
            'join_date': member.join_date,
            'created_at': member.created_at
        }
    
    async def get_guild_stats(self, guild_id: int) -> Dict[str, int]:
        """Get guild member statistics."""
        try:
            total_members = await self.member_collection.count_guild_members(guild_id)
            members_with_warnings = len(await self.get_members_with_warnings(guild_id))
            
            # Get active members (with messages in last 30 days)
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=30)
            active_members = await self.member_collection.count(
                guild_id=guild_id,
                updated_at={'$gte': cutoff}
            )
            
            return {
                'total_members': total_members,
                'active_members': active_members,
                'inactive_members': total_members - active_members,
                'members_with_warnings': members_with_warnings
            }
        except Exception as e:
            self.log_error(f"Error getting guild stats for {guild_id}", exc_info=e)
            return {
                'total_members': 0,
                'active_members': 0,
                'inactive_members': 0,
                'members_with_warnings': 0
            } 