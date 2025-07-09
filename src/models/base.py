"""
Base model class for the Discord bot.

This module provides the foundation for all data models with Pydantic
validation and MongoDB integration.
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId
import json


class PyObjectId(ObjectId):
    """Custom ObjectId field for Pydantic models."""
    
    @classmethod
    def __get_validators__(cls):
        """Get validators for the field."""
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        """Validate ObjectId value."""
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __modify_schema__(cls, field_schema):
        """Modify the schema for the field."""
        field_schema.update(type="string")


class BaseModel(BaseModel):
    """Base model class with common functionality."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic configuration."""
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        validate_assignment = True
    
    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        """Set updated_at to current time."""
        return datetime.utcnow()
    
    def to_dict(self, exclude_none: bool = True, exclude_defaults: bool = False) -> Dict[str, Any]:
        """Convert model to dictionary."""
        data = self.dict(
            by_alias=True,
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults
        )
        
        # Convert ObjectId to string
        if '_id' in data and isinstance(data['_id'], ObjectId):
            data['_id'] = str(data['_id'])
        
        return data
    
    def to_json(self, exclude_none: bool = True, exclude_defaults: bool = False) -> str:
        """Convert model to JSON string."""
        data = self.to_dict(exclude_none=exclude_none, exclude_defaults=exclude_defaults)
        return json.dumps(data, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create model from dictionary."""
        # Convert string ID to ObjectId if needed
        if '_id' in data and isinstance(data['_id'], str):
            try:
                data['_id'] = ObjectId(data['_id'])
            except Exception:
                pass
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseModel':
        """Create model from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update model with new data."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def copy(self, **kwargs) -> 'BaseModel':
        """Create a copy of the model with optional updates."""
        return self.__class__(**{**self.dict(), **kwargs})
    
    def get_id(self) -> str:
        """Get the ID as a string."""
        return str(self.id) if self.id else None
    
    def is_new(self) -> bool:
        """Check if this is a new model (no ID set)."""
        return self.id is None
    
    def get_created_timestamp(self) -> float:
        """Get created timestamp as Unix timestamp."""
        return self.created_at.timestamp()
    
    def get_updated_timestamp(self) -> float:
        """Get updated timestamp as Unix timestamp."""
        return self.updated_at.timestamp()
    
    def get_age_seconds(self) -> float:
        """Get the age of the model in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    def get_age_minutes(self) -> float:
        """Get the age of the model in minutes."""
        return self.get_age_seconds() / 60
    
    def get_age_hours(self) -> float:
        """Get the age of the model in hours."""
        return self.get_age_minutes() / 60
    
    def get_age_days(self) -> float:
        """Get the age of the model in days."""
        return self.get_age_hours() / 24
    
    def format_created_at(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format created_at timestamp."""
        return self.created_at.strftime(format_str)
    
    def format_updated_at(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format updated_at timestamp."""
        return self.updated_at.strftime(format_str)
    
    def to_mongo_document(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        data = self.to_dict(exclude_none=True)
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        return data
    
    @classmethod
    def from_mongo_document(cls, document: Dict[str, Any]) -> 'BaseModel':
        """Create model from MongoDB document."""
        if document is None:
            return None
        
        # Convert MongoDB document to model
        data = {}
        for key, value in document.items():
            if key == '_id':
                data['id'] = value
            else:
                data[key] = value
        
        return cls.from_dict(data)
    
    def validate_field(self, field_name: str, value: Any) -> bool:
        """Validate a specific field value."""
        try:
            field = self.__fields__.get(field_name)
            if field:
                field.validate(value, {}, loc=field_name)
            return True
        except Exception:
            return False
    
    def get_field_value(self, field_name: str, default: Any = None) -> Any:
        """Get a field value safely."""
        return getattr(self, field_name, default)
    
    def set_field_value(self, field_name: str, value: Any) -> bool:
        """Set a field value safely."""
        try:
            if hasattr(self, field_name):
                setattr(self, field_name, value)
                return True
        except Exception:
            pass
        return False
    
    def has_field(self, field_name: str) -> bool:
        """Check if model has a specific field."""
        return hasattr(self, field_name)
    
    def get_field_names(self) -> List[str]:
        """Get all field names."""
        return list(self.__fields__.keys())
    
    def get_required_fields(self) -> List[str]:
        """Get required field names."""
        return [
            name for name, field in self.__fields__.items()
            if field.required
        ]
    
    def get_optional_fields(self) -> List[str]:
        """Get optional field names."""
        return [
            name for name, field in self.__fields__.items()
            if not field.required
        ]
    
    def get_field_info(self, field_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific field."""
        field = self.__fields__.get(field_name)
        if field:
            return {
                'name': field_name,
                'type': str(field.type_),
                'required': field.required,
                'default': field.default,
                'description': field.field_info.description
            }
        return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            'model_name': self.__class__.__name__,
            'fields': len(self.__fields__),
            'required_fields': len(self.get_required_fields()),
            'optional_fields': len(self.get_optional_fields()),
            'field_names': self.get_field_names()
        }
    
    def __str__(self) -> str:
        """String representation of the model."""
        return f"{self.__class__.__name__}(id={self.get_id()})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the model."""
        return f"{self.__class__.__name__}(id={self.get_id()}, created_at={self.format_created_at()})"


# Utility functions for working with models
def create_model_id() -> PyObjectId:
    """Create a new ObjectId for models."""
    return PyObjectId()


def is_valid_object_id(obj_id: str) -> bool:
    """Check if a string is a valid ObjectId."""
    try:
        ObjectId(obj_id)
        return True
    except Exception:
        return False


def convert_to_object_id(obj_id: Any) -> Optional[ObjectId]:
    """Convert value to ObjectId safely."""
    if obj_id is None:
        return None
    
    if isinstance(obj_id, ObjectId):
        return obj_id
    
    if isinstance(obj_id, str):
        try:
            return ObjectId(obj_id)
        except Exception:
            return None
    
    return None


def convert_to_string_id(obj_id: Any) -> Optional[str]:
    """Convert value to string ID safely."""
    if obj_id is None:
        return None
    
    if isinstance(obj_id, str):
        return obj_id
    
    if isinstance(obj_id, ObjectId):
        return str(obj_id)
    
    return str(obj_id) 