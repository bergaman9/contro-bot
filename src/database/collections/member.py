"""Member collection for MongoDB database operations."""
from typing import Optional, List, Tuple
from .base import BaseCollection
from ..models.member import Member
from ..connection import DatabaseConnection


class MemberCollection(BaseCollection):
    """Collection for member operations."""
    
    def __init__(self, connection: DatabaseConnection):
        """Initialize member collection."""
        super().__init__(connection, Member, 'members')
    
    async def find_by_ids(self, guild_id: int, user_id: int) -> Optional[Member]:
        """Find member by guild and user IDs."""
        return await self.find_one_by(guild_id=guild_id, user_id=user_id)
    
    async def get_or_create(self, guild_id: int, user_id: int) -> Member:
        """Get existing member or create new one."""
        member = await self.find_by_ids(guild_id, user_id)
        
        if not member:
            member = await self.create({
                'guild_id': guild_id,
                'user_id': user_id
            })
        
        return member
    
    async def get_top_members_by_xp(self, guild_id: int, limit: int = 10) -> List[Member]:
        """Get top members by XP in a guild."""
        return await self.find_by(
            guild_id=guild_id,
            sort=[('xp', -1)],
            limit=limit
        )
    
    async def get_guild_members(self, guild_id: int, limit: Optional[int] = None, skip: int = 0) -> List[Member]:
        """Get all members in a guild."""
        docs = await self.db.find_many(
            self.collection_name,
            filter={'guild_id': guild_id},
            limit=limit,
            skip=skip
        )
        return [Member.from_dict(doc) for doc in docs]
    
    async def count_guild_members(self, guild_id: int) -> int:
        """Count members in a guild."""
        return await self.count(guild_id=guild_id)
    
    async def add_xp(self, guild_id: int, user_id: int, amount: int) -> Optional[Tuple[int, int]]:
        """Add XP to member and calculate level."""
        member = await self.get_or_create(guild_id, user_id)
        
        # Add XP
        member.xp += amount
        
        # Calculate new level (using same formula as User)
        from ..models.user import User
        new_level = User.calculate_level(member.xp)
        
        if new_level != member.level:
            member.level = new_level
        
        await self.update(member)
        return member.xp, member.level
    
    async def get_members_with_warnings(self, guild_id: int) -> List[Member]:
        """Get all members with warnings in a guild."""
        docs = await self.db.find_many(
            self.collection_name,
            filter={
                'guild_id': guild_id,
                'warnings': {'$exists': True, '$ne': []}
            }
        )
        return [Member.from_dict(doc) for doc in docs]
    
    async def add_warning(self, guild_id: int, user_id: int, reason: str, moderator_id: int) -> bool:
        """Add a warning to member."""
        from datetime import datetime
        
        warning = {
            'reason': reason,
            'moderator_id': moderator_id,
            'timestamp': datetime.utcnow()
        }
        
        return await self.update_one(
            filter={'guild_id': guild_id, 'user_id': user_id},
            update={
                '$push': {'warnings': warning},
                '$inc': {'warning_count': 1}
            }
        )
    
    async def clear_member_data(self, guild_id: int, user_id: int) -> bool:
        """Clear all data for a member."""
        return await self.delete_one(
            self.collection_name,
            filter={'guild_id': guild_id, 'user_id': user_id}
        )
    
    async def increment_message_count(self, guild_id: int, user_id: int) -> bool:
        """Increment message count for a member."""
        return await self.update_one(
            filter={'guild_id': guild_id, 'user_id': user_id},
            update={'$inc': {'total_messages': 1}}
        ) 