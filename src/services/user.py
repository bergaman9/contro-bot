"""User service for business logic."""
from typing import Optional, List, Dict, Any
from .base import BaseService
from ..database.repositories import UserRepository
from ..database.models import User
import discord


class UserService(BaseService):
    """Service for user-related operations."""
    
    def __init__(self, db):
        """Initialize user service."""
        super().__init__(db)
        self.user_repo = UserRepository(db)
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        try:
            return await self.user_repo.find_by_user_id(user_id)
        except Exception as e:
            self.log_error(f"Error getting user {user_id}", exc_info=e)
            return None
    
    async def ensure_user_exists(self, discord_user: discord.User) -> User:
        """Ensure user exists in database."""
        try:
            return await self.user_repo.get_or_create(
                user_id=discord_user.id,
                username=discord_user.name,
                discriminator=discord_user.discriminator or "0"
            )
        except Exception as e:
            self.log_error(f"Error ensuring user exists: {discord_user.id}", exc_info=e)
            raise
    
    async def add_xp(self, user_id: int, amount: int) -> Optional[tuple[int, int]]:
        """Add XP to user and return new XP and level."""
        try:
            result = await self.user_repo.add_global_xp(user_id, amount)
            if result:
                new_xp, new_level = result
                self.log_info(f"Added {amount} XP to user {user_id}. New: {new_xp} XP, Level {new_level}")
            return result
        except Exception as e:
            self.log_error(f"Error adding XP to user {user_id}", exc_info=e)
            return None
    
    async def get_leaderboard(self, limit: int = 10) -> List[User]:
        """Get XP leaderboard."""
        try:
            return await self.user_repo.get_top_users_by_xp(limit)
        except Exception as e:
            self.log_error("Error getting leaderboard", exc_info=e)
            return []
    
    async def has_badge(self, user_id: int, badge: str) -> bool:
        """Check if user has a specific badge."""
        user = await self.get_user(user_id)
        return user.has_badge(badge) if user else False
    
    async def add_badge(self, user_id: int, badge: str) -> bool:
        """Add a badge to user."""
        try:
            success = await self.user_repo.add_badge(user_id, badge)
            if success:
                self.log_info(f"Added badge '{badge}' to user {user_id}")
            return success
        except Exception as e:
            self.log_error(f"Error adding badge to user {user_id}", exc_info=e)
            return False
    
    async def remove_badge(self, user_id: int, badge: str) -> bool:
        """Remove a badge from user."""
        try:
            success = await self.user_repo.remove_badge(user_id, badge)
            if success:
                self.log_info(f"Removed badge '{badge}' from user {user_id}")
            return success
        except Exception as e:
            self.log_error(f"Error removing badge from user {user_id}", exc_info=e)
            return False
    
    async def get_users_by_badge(self, badge: str) -> List[User]:
        """Get all users with a specific badge."""
        try:
            return await self.user_repo.get_users_by_badge(badge)
        except Exception as e:
            self.log_error(f"Error getting users with badge '{badge}'", exc_info=e)
            return []
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics."""
        user = await self.get_user(user_id)
        if not user:
            return {
                'exists': False,
                'xp': 0,
                'level': 0,
                'badges': [],
                'badge_count': 0
            }
        
        return {
            'exists': True,
            'xp': user.global_xp,
            'level': user.global_level,
            'badges': user.badges,
            'badge_count': len(user.badges),
            'next_level_xp': User.xp_for_next_level(user.global_level),
            'created_at': user.created_at
        } 