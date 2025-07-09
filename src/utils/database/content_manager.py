import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from pathlib import Path
from src.utils.database.connection import get_async_db, initialize_mongodb

logger = logging.getLogger(__name__)

class ContentManager:
    """Manages server-specific content in MongoDB"""
    
    def __init__(self):
        self.db = None
        self.default_contents = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize the content manager"""
        if self._initialized:
            return
            
        self.db = get_async_db()
        if self.db is None:
            logger.error("Failed to initialize database connection")
            return
            
        # Load default contents from md files
        await self.load_default_contents()
        
        # Ensure indexes
        await self.ensure_indexes()
        
        self._initialized = True
        logger.info("ContentManager initialized successfully")
        
    async def ensure_indexes(self):
        """Create indexes for better performance"""
        try:
            await self.db.server_contents.create_index([("guild_id", 1)])
            await self.db.server_contents.create_index([("guild_id", 1), ("content_key", 1)])
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            
    async def load_default_contents(self):
        """Load default contents from md files"""
        content_dir = Path(__file__).parent.parent.parent / "data" / "contents"
        
        content_files = {
            "server": "server.md",
            "commands": "commands.md",
            "roles": "roles.md",
            "channels": "channels.md",
            "services": "services.md",
            "rules": "rules.md",
            "announcements": "announcements.md",
            "version": "version.md"
        }
        
        for key, filename in content_files.items():
            file_path = content_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.default_contents[key] = content
                        logger.info(f"Loaded default content for '{key}'")
                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")
                    
    async def get_content(self, guild_id: str, content_key: str, section_index: Optional[int] = None) -> str:
        """Get content for a specific guild and content key"""
        if not self._initialized:
            await self.initialize()
            
        # Try to get custom content first
        custom_content = await self.db.server_contents.find_one({
            "guild_id": guild_id,
            "content_key": content_key
        })
        
        if custom_content and custom_content.get("content"):
            content = custom_content["content"]
        else:
            # Fall back to default content
            content = self.default_contents.get(content_key, f"Content not found: {content_key}")
            
        # Handle section splitting
        if "---" in content and section_index is not None:
            sections = content.split("---")
            sections = [section.strip() for section in sections]
            
            if 0 <= section_index < len(sections):
                return sections[section_index]
            else:
                return f"Section {section_index} not found"
                
        return content
        
    async def set_content(self, guild_id: str, content_key: str, content: str) -> bool:
        """Set custom content for a specific guild"""
        if not self._initialized:
            await self.initialize()
            
        try:
            await self.db.server_contents.update_one(
                {
                    "guild_id": guild_id,
                    "content_key": content_key
                },
                {
                    "$set": {
                        "content": content,
                        "updated_at": datetime.utcnow(),
                        "updated_by": "system"
                    }
                },
                upsert=True
            )
            logger.info(f"Updated content '{content_key}' for guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting content: {e}")
            return False
            
    async def get_all_contents(self, guild_id: str) -> Dict[str, str]:
        """Get all contents for a guild"""
        if not self._initialized:
            await self.initialize()
            
        contents = {}
        
        # Get all custom contents
        custom_contents = await self.db.server_contents.find({"guild_id": guild_id}).to_list(None)
        for item in custom_contents:
            contents[item["content_key"]] = item["content"]
            
        # Fill in missing contents with defaults
        for key, default_content in self.default_contents.items():
            if key not in contents:
                contents[key] = default_content
                
        return contents
        
    async def import_default_for_guild(self, guild_id: str) -> bool:
        """Import all default contents for a specific guild"""
        if not self._initialized:
            await self.initialize()
            
        try:
            for key, content in self.default_contents.items():
                await self.set_content(guild_id, key, content)
            logger.info(f"Imported default contents for guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error importing defaults: {e}")
            return False
            
    async def reset_content(self, guild_id: str, content_key: str) -> bool:
        """Reset a specific content to default"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Delete custom content
            await self.db.server_contents.delete_one({
                "guild_id": guild_id,
                "content_key": content_key
            })
            logger.info(f"Reset content '{content_key}' for guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error resetting content: {e}")
            return False
            
    async def reset_all_contents(self, guild_id: str) -> bool:
        """Reset all contents to defaults for a guild"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Delete all custom contents
            result = await self.db.server_contents.delete_many({"guild_id": guild_id})
            logger.info(f"Reset {result.deleted_count} contents for guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error resetting all contents: {e}")
            return False

# Global instance
content_manager = ContentManager() 