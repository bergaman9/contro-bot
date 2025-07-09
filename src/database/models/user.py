"""User model for database."""
from datetime import datetime
from typing import Optional, List
from .base import BaseModel


class User(BaseModel):
    """User model representing a Discord user."""
    
    def __init__(self, **kwargs):
        # Set defaults
        kwargs.setdefault('created_at', datetime.utcnow())
        kwargs.setdefault('updated_at', datetime.utcnow())
        kwargs.setdefault('global_xp', 0)
        kwargs.setdefault('global_level', 0)
        kwargs.setdefault('badges', [])
        kwargs.setdefault('settings', {})
        
        super().__init__(**kwargs)
        self._table_name = 'users'
    
    @property
    def user_id(self) -> int:
        """Get user ID."""
        return self._data.get('user_id', 0)
    
    @user_id.setter
    def user_id(self, value: int):
        """Set user ID."""
        self._data['user_id'] = value
    
    @property
    def username(self) -> str:
        """Get username."""
        return self._data.get('username', '')
    
    @username.setter
    def username(self, value: str):
        """Set username."""
        self._data['username'] = value
    
    @property
    def discriminator(self) -> str:
        """Get discriminator."""
        return self._data.get('discriminator', '0000')
    
    @discriminator.setter
    def discriminator(self, value: str):
        """Set discriminator."""
        self._data['discriminator'] = value
    
    @property
    def global_xp(self) -> int:
        """Get global XP."""
        return self._data.get('global_xp', 0)
    
    @global_xp.setter
    def global_xp(self, value: int):
        """Set global XP."""
        self._data['global_xp'] = value
        self._data['updated_at'] = datetime.utcnow()
    
    @property
    def global_level(self) -> int:
        """Get global level."""
        return self._data.get('global_level', 0)
    
    @global_level.setter  
    def global_level(self, value: int):
        """Set global level."""
        self._data['global_level'] = value
        self._data['updated_at'] = datetime.utcnow()
    
    def add_xp(self, amount: int) -> tuple[int, int]:
        """Add XP and calculate new level.
        
        Returns:
            Tuple of (new_xp, new_level)
        """
        self.global_xp += amount
        old_level = self.global_level
        new_level = self.calculate_level(self.global_xp)
        
        if new_level != old_level:
            self.global_level = new_level
        
        return self.global_xp, self.global_level
    
    @staticmethod
    def calculate_level(xp: int) -> int:
        """Calculate level from XP."""
        level = 0
        remaining_xp = xp
        
        while remaining_xp >= User.xp_for_next_level(level):
            remaining_xp -= User.xp_for_next_level(level)
            level += 1
        
        return level
    
    @staticmethod
    def xp_for_next_level(current_level: int) -> int:
        """Calculate XP required for next level."""
        return 5 * (current_level ** 2) + 50 * current_level + 100
    
    @property
    def badges(self) -> List[str]:
        """Get user badges."""
        return self._data.get('badges', [])
    
    def has_badge(self, badge: str) -> bool:
        """Check if user has a badge."""
        return badge in self.badges
    
    def add_badge(self, badge: str):
        """Add a badge to user."""
        if 'badges' not in self._data:
            self._data['badges'] = []
        if badge not in self._data['badges']:
            self._data['badges'].append(badge)
            self._data['updated_at'] = datetime.utcnow()
    
    def remove_badge(self, badge: str):
        """Remove a badge from user."""
        if 'badges' in self._data and badge in self._data['badges']:
            self._data['badges'].remove(badge)
            self._data['updated_at'] = datetime.utcnow() 