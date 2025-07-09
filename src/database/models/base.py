"""Base model for database models."""
from datetime import datetime
from typing import Dict, Any, Optional
import json


class BaseModel:
    """Base class for all database models."""
    
    def __init__(self, **kwargs):
        """Initialize model with data."""
        self._data = kwargs
        self._original_data = kwargs.copy()
        self._table_name = self.__class__.__name__.lower() + 's'
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create model instance from dictionary."""
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self._data.copy()
    
    def to_json(self) -> str:
        """Convert model to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @property
    def is_modified(self) -> bool:
        """Check if model has been modified."""
        return self._data != self._original_data
    
    def get_modified_fields(self) -> Dict[str, Any]:
        """Get only modified fields."""
        modified = {}
        for key, value in self._data.items():
            if key not in self._original_data or self._original_data[key] != value:
                modified[key] = value
        return modified
    
    def reset_modifications(self):
        """Reset modification tracking."""
        self._original_data = self._data.copy()
    
    def __getattr__(self, name: str) -> Any:
        """Get attribute from data."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name)
    
    def __setattr__(self, name: str, value: Any):
        """Set attribute in data."""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value
    
    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}({self._data})" 