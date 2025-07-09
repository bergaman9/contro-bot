"""Member model for database."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from .base import BaseModel


class Member(BaseModel):
    """Member model representing a guild member."""
    
    def __init__(self, **kwargs):
        # Set defaults
        kwargs.setdefault('created_at', datetime.utcnow())
        kwargs.setdefault('updated_at', datetime.utcnow())
        kwargs.setdefault('xp', 0)
        kwargs.setdefault('level', 0)
        kwargs.setdefault('total_messages', 0)
        kwargs.setdefault('roles', [])
        kwargs.setdefault('warnings', [])
        kwargs.setdefault('notes', [])
        
        super().__init__(**kwargs)
        self._table_name = 'members'
    
    @property
    def guild_id(self) -> int:
        """Get guild ID."""
        return self._data.get('guild_id', 0)
    
    @guild_id.setter
    def guild_id(self, value: int):
        """Set guild ID."""
        self._data['guild_id'] = value
    
    @property
    def user_id(self) -> int:
        """Get user ID."""
        return self._data.get('user_id', 0)
    
    @user_id.setter
    def user_id(self, value: int):
        """Set user ID."""
        self._data['user_id'] = value
    
    @property
    def xp(self) -> int:
        """Get guild XP."""
        return self._data.get('xp', 0)
    
    @xp.setter
    def xp(self, value: int):
        """Set guild XP."""
        self._data['xp'] = value
        self._data['updated_at'] = datetime.utcnow()
    
    @property
    def level(self) -> int:
        """Get guild level."""
        return self._data.get('level', 0)
    
    @level.setter
    def level(self, value: int):
        """Set guild level."""
        self._data['level'] = value
        self._data['updated_at'] = datetime.utcnow()
    
    @property
    def total_messages(self) -> int:
        """Get total messages sent."""
        return self._data.get('total_messages', 0)
    
    def increment_messages(self):
        """Increment message count."""
        self._data['total_messages'] = self.total_messages + 1
        self._data['updated_at'] = datetime.utcnow()
    
    @property
    def warnings(self) -> List[Dict[str, Any]]:
        """Get member warnings."""
        return self._data.get('warnings', [])
    
    def add_warning(self, reason: str, moderator_id: int):
        """Add a warning to member."""
        if 'warnings' not in self._data:
            self._data['warnings'] = []
        
        warning = {
            'id': len(self._data['warnings']) + 1,
            'reason': reason,
            'moderator_id': moderator_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self._data['warnings'].append(warning)
        self._data['updated_at'] = datetime.utcnow()
    
    def remove_warning(self, warning_id: int) -> bool:
        """Remove a warning by ID."""
        if 'warnings' not in self._data:
            return False
        
        for i, warning in enumerate(self._data['warnings']):
            if warning.get('id') == warning_id:
                self._data['warnings'].pop(i)
                self._data['updated_at'] = datetime.utcnow()
                return True
        
        return False
    
    @property
    def notes(self) -> List[Dict[str, Any]]:
        """Get moderator notes."""
        return self._data.get('notes', [])
    
    def add_note(self, content: str, moderator_id: int):
        """Add a moderator note."""
        if 'notes' not in self._data:
            self._data['notes'] = []
        
        note = {
            'id': len(self._data['notes']) + 1,
            'content': content,
            'moderator_id': moderator_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self._data['notes'].append(note)
        self._data['updated_at'] = datetime.utcnow()
    
    @property
    def join_date(self) -> Optional[datetime]:
        """Get member join date."""
        join_date = self._data.get('join_date')
        if join_date and isinstance(join_date, str):
            return datetime.fromisoformat(join_date)
        return join_date
    
    @join_date.setter
    def join_date(self, value: datetime):
        """Set member join date."""
        self._data['join_date'] = value.isoformat() if value else None 