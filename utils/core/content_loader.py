import os
import asyncio
import logging
from utils.database.content_manager import content_manager

logger = logging.getLogger(__name__)

def read_markdown_file(filename, content_dir='contents'):
    """DEPRECATED: Use content_manager instead"""
    # For backward compatibility, try to get from content manager
    try:
        # This is a sync function calling async, so we need to handle it
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context already
            return f"Please use await content_manager.get_content() instead"
        else:
            # Create a new event loop for sync context
            content = asyncio.run(content_manager.get_content("default", filename))
            return content
    except Exception as e:
        logger.error(f"Error in read_markdown_file: {e}")
        return f"Error loading content: {filename}"

def load_content(filename, section_index=None, content_dir='contents'):
    """DEPRECATED: Use content_manager instead"""
    # For backward compatibility
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context already
            return f"Please use await content_manager.get_content() instead"
        else:
            # Create a new event loop for sync context
            content = asyncio.run(content_manager.get_content("default", filename, section_index))
            return content
    except Exception as e:
        logger.error(f"Error in load_content: {e}")
        return f"Error loading content: {filename}"

# New async functions that should be used instead
async def async_load_content(guild_id, content_key, section_index=None):
    """Load content asynchronously from MongoDB"""
    return await content_manager.get_content(str(guild_id), content_key, section_index)

async def async_set_content(guild_id, content_key, content):
    """Set content asynchronously in MongoDB"""
    return await content_manager.set_content(str(guild_id), content_key, content)
