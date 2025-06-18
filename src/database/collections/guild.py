"""Guild collection for MongoDB database operations."""
from typing import Optional, List, Any
from .base import BaseCollection
from ..models.guild import Guild
from ..connection import DatabaseConnection


class GuildCollection(BaseCollection):
    """Collection for guild operations."""
    
    def __init__(self, connection: DatabaseConnection):
        """Initialize guild collection."""
        super().__init__(connection, Guild, 'guilds')
    
    async def find_by_guild_id(self, guild_id: int) -> Optional[Guild]:
        """Find guild by Discord guild ID."""
        return await self.find_one_by(guild_id=guild_id)
    
    async def get_or_create(self, guild_id: int, name: str) -> Guild:
        """Get existing guild or create new one."""
        guild = await self.find_by_guild_id(guild_id)
        
        if not guild:
            guild = await self.create({
                'guild_id': guild_id,
                'name': name
            })
        
        return guild
    
    async def find_by_feature(self, feature: str) -> List[Guild]:
        """Find all guilds with a specific feature."""
        docs = await self.db.find_many(
            self.collection_name,
            filter={'features': feature}
        )
        return [Guild.from_dict(doc) for doc in docs]
    
    async def update_prefix(self, guild_id: int, prefix: str) -> bool:
        """Update guild prefix."""
        return await self.update_one(
            filter={'guild_id': guild_id},
            update={'$set': {'prefix': prefix}}
        )
    
    async def update_language(self, guild_id: int, language: str) -> bool:
        """Update guild language."""
        return await self.update_one(
            filter={'guild_id': guild_id},
            update={'$set': {'language': language}}
        )
    
    async def update_setting(self, guild_id: int, key: str, value: Any) -> bool:
        """Update a specific guild setting."""
        return await self.update_one(
            filter={'guild_id': guild_id},
            update={'$set': {f'settings.{key}': value}}
        )
    
    async def add_feature(self, guild_id: int, feature: str) -> bool:
        """Add a feature to guild."""
        return await self.update_one(
            filter={'guild_id': guild_id},
            update={'$addToSet': {'features': feature}}
        )
    
    async def remove_feature(self, guild_id: int, feature: str) -> bool:
        """Remove a feature from guild."""
        return await self.update_one(
            filter={'guild_id': guild_id},
            update={'$pull': {'features': feature}}
        )
    
    async def get_active_guilds(self, days: int = 30) -> List[Guild]:
        """Get guilds active in the last N days."""
        from datetime import datetime, timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        docs = await self.db.find_many(
            self.collection_name,
            filter={'updated_at': {'$gte': cutoff}},
            sort=[('updated_at', -1)]
        )
        return [Guild.from_dict(doc) for doc in docs] 