"""Guild model for database."""
from datetime import datetime
from typing import Optional, Dict, Any
from .base import BaseModel


class Guild(BaseModel):
    """Guild model representing a Discord server."""
    
    def __init__(self, **kwargs):
        # Set defaults
        kwargs.setdefault('prefix', '!')
        kwargs.setdefault('language', 'en')
        kwargs.setdefault('created_at', datetime.utcnow())
        kwargs.setdefault('updated_at', datetime.utcnow())
        kwargs.setdefault('settings', {})
        kwargs.setdefault('features', [])
        
        super().__init__(**kwargs)
        self._table_name = 'guilds'
    
    @property
    def guild_id(self) -> int:
        """Get guild ID."""
        return self._data.get('guild_id', 0)
    
    @guild_id.setter
    def guild_id(self, value: int):
        """Set guild ID."""
        self._data['guild_id'] = value
    
    @property
    def name(self) -> str:
        """Get guild name."""
        return self._data.get('name', '')
    
    @name.setter
    def name(self, value: str):
        """Set guild name."""
        self._data['name'] = value
    
    @property
    def prefix(self) -> str:
        """Get command prefix."""
        return self._data.get('prefix', '!')
    
    @prefix.setter
    def prefix(self, value: str):
        """Set command prefix."""
        self._data['prefix'] = value
    
    @property
    def language(self) -> str:
        """Get guild language."""
        return self._data.get('language', 'en')
    
    @language.setter
    def language(self, value: str):
        """Set guild language."""
        self._data['language'] = value
    
    @property
    def settings(self) -> Dict[str, Any]:
        """Get guild settings."""
        return self._data.get('settings', {})
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting."""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any):
        """Set a specific setting."""
        if 'settings' not in self._data:
            self._data['settings'] = {}
        self._data['settings'][key] = value
        self._data['updated_at'] = datetime.utcnow()
    
    def has_feature(self, feature: str) -> bool:
        """Check if guild has a feature enabled."""
        return feature in self._data.get('features', [])
    
    def add_feature(self, feature: str):
        """Add a feature to the guild."""
        if 'features' not in self._data:
            self._data['features'] = []
        if feature not in self._data['features']:
            self._data['features'].append(feature)
            self._data['updated_at'] = datetime.utcnow()
    
    def remove_feature(self, feature: str):
        """Remove a feature from the guild."""
        if 'features' in self._data and feature in self._data['features']:
            self._data['features'].remove(feature)
            self._data['updated_at'] = datetime.utcnow() 