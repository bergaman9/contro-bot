"""User collection for MongoDB database operations."""
from typing import Optional, List
from .base import BaseCollection
from ..models.user import User
from ..connection import DatabaseConnection


class UserCollection(BaseCollection):
    """Collection for user operations."""
    
    def __init__(self, connection: DatabaseConnection):
        """Initialize user collection."""
        super().__init__(connection, User, 'users')
    
    async def find_by_user_id(self, user_id: int) -> Optional[User]:
        """Find user by Discord user ID."""
        return await self.find_one_by(user_id=user_id)
    
    async def get_or_create(self, user_id: int, username: str, discriminator: str = "0") -> User:
        """Get existing user or create new one."""
        user = await self.find_by_user_id(user_id)
        
        if not user:
            user = await self.create({
                'user_id': user_id,
                'username': username,
                'discriminator': discriminator
            })
        
        return user
    
    async def get_top_users_by_xp(self, limit: int = 10) -> List[User]:
        """Get top users by global XP."""
        return await self.find_by(
            sort=[('global_xp', -1)],
            limit=limit
        )
    
    async def get_users_by_badge(self, badge: str) -> List[User]:
        """Get all users with a specific badge."""
        docs = await self.db.find_many(
            self.collection_name,
            filter={'badges': badge}
        )
        return [User.from_dict(doc) for doc in docs]
    
    async def add_global_xp(self, user_id: int, amount: int) -> Optional[tuple[int, int]]:
        """Add global XP to user and return new XP and level."""
        user = await self.find_by_user_id(user_id)
        if user:
            new_xp, new_level = user.add_xp(amount)
            await self.update(user)
            return new_xp, new_level
        return None
    
    async def add_badge(self, user_id: int, badge: str) -> bool:
        """Add a badge to user."""
        return await self.update_one(
            filter={'user_id': user_id},
            update={'$addToSet': {'badges': badge}}
        )
    
    async def remove_badge(self, user_id: int, badge: str) -> bool:
        """Remove a badge from user."""
        return await self.update_one(
            filter={'user_id': user_id},
            update={'$pull': {'badges': badge}}
        ) 