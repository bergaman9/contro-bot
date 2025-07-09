"""
Formatting utilities for Discord messages, embeds, and other content.
"""
import discord
import re
import datetime
import logging
from typing import Optional, Union, Dict, Any, List

def create_embed(
    title: Optional[str] = None, 
    description: Optional[str] = None,
    color: Optional[Union[discord.Color, int]] = None,
    author: Optional[Dict[str, Any]] = None,
    fields: Optional[List[Dict[str, Any]]] = None,
    footer: Optional[Dict[str, Any]] = None,
    image: Optional[str] = None,
    thumbnail: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None
) -> discord.Embed:
    """
    Create a Discord embed with specified parameters.
    
    Args:
        title: The title of the embed
        description: The description content
        color: The color of the embed sidebar
        author: Dict with 'name', 'url' (optional), 'icon_url' (optional)
        fields: List of dicts with 'name', 'value', 'inline' (optional)
        footer: Dict with 'text', 'icon_url' (optional)
        image: URL of the main image
        thumbnail: URL of the thumbnail image
        timestamp: Datetime for the embed timestamp
        
    Returns:
        discord.Embed: The created embed
    """
    # Default color if none provided
    if color is None:
        color = discord.Color.blurple()
    
    # Create the embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=timestamp
    )
    
    # Add author if provided
    if author:
        name = author.get('name', '')
        url = author.get('url')
        icon_url = author.get('icon_url')
        embed.set_author(name=name, url=url, icon_url=icon_url)
    
    # Add fields if provided
    if fields:
        for field in fields:
            name = field.get('name', '')
            value = field.get('value', '')
            inline = field.get('inline', False)
            embed.add_field(name=name, value=value, inline=inline)
    
    # Add footer if provided
    if footer:
        text = footer.get('text', '')
        icon_url = footer.get('icon_url')
        embed.set_footer(text=text, icon_url=icon_url)
    
    # Add images if provided
    if image:
        embed.set_image(url=image)
        
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    return embed

def truncate_text(text: str, max_length: int = 2000, suffix: str = '...') -> str:
    """
    Truncate text to the specified maximum length, adding a suffix if truncated.
    
    Args:
        text: The text to truncate
        max_length: Maximum length allowed
        suffix: Suffix to add when truncated
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def format_timestamp(timestamp: Union[int, float, datetime.datetime], format_type: str = 'f') -> str:
    """
    Format a timestamp for Discord display.
    
    Args:
        timestamp: Unix timestamp or datetime object
        format_type: Discord timestamp format (t, T, d, D, f, F, R)
        
    Returns:
        str: Formatted Discord timestamp
    """
    if isinstance(timestamp, datetime.datetime):
        timestamp = int(timestamp.timestamp())
    
    return f"<t:{int(timestamp)}:{format_type}>"

def sanitize_mentions(text: str) -> str:
    """
    Sanitize Discord mentions in a text string.
    
    Args:
        text: Text to sanitize
        
    Returns:
        str: Sanitized text with escaped mentions
    """
    # Escape @everyone and @here
    text = text.replace('@everyone', '@\u200beveryone')
    text = text.replace('@here', '@\u200bhere')
    
    # Escape user/role/channel mentions
    text = re.sub(r'<@(!?&?\d+)>', '<@\u200b\\1>', text)
    
    return text

def create_progress_bar(progress: float, length: int = 10, 
                       filled_char: str = '■', empty_char: str = '□') -> str:
    """
    Create a text-based progress bar.
    
    Args:
        progress: Progress value between 0 and 1
        length: Number of characters in the bar
        filled_char: Character for filled portion
        empty_char: Character for empty portion
        
    Returns:
        str: Text progress bar
    """
    # Ensure progress is between 0 and 1
    progress = max(0, min(1, progress))
    
    # Calculate filled and empty lengths
    filled_length = int(progress * length)
    empty_length = length - filled_length
    
    # Construct the bar
    bar = filled_char * filled_length + empty_char * empty_length
    
    return bar

def hex_to_int(hex_string: str) -> int:
    """
    Convert a hexadecimal color string to an integer.
    
    Args:
        hex_string: Hex color string (with or without # prefix)
        
    Returns:
        int: Integer representation of the color
    """
    # Remove '#' if present
    if hex_string.startswith('#'):
        hex_string = hex_string[1:]
        
    # Validate hexadecimal format
    if not all(c in '0123456789ABCDEFabcdef' for c in hex_string):
        raise ValueError(f"Invalid hexadecimal color string: {hex_string}")
    
    # Convert to integer
    return int(hex_string, 16)

def calculate_how_long_ago_member_joined(member) -> str:
    """
    Calculate and format how long ago a member joined the server.
    
    Args:
        member: discord.Member object
        
    Returns:
        str: Formatted time string
    """
    if not member.joined_at:
        return "Unknown"
        
    now = datetime.datetime.now(datetime.timezone.utc)
    joined = member.joined_at
    
    # Calculate time difference
    delta = now - joined
    
    # Format the difference in a human-readable way
    days = delta.days
    years = days // 365
    months = (days % 365) // 30
    remaining_days = days % 30
    
    if years > 0:
        return f"{years} year{'s' if years != 1 else ''}, {months} month{'s' if months != 1 else ''}, {remaining_days} day{'s' if remaining_days != 1 else ''}"
    elif months > 0:
        return f"{months} month{'s' if months != 1 else ''}, {remaining_days} day{'s' if remaining_days != 1 else ''}"
    else:
        return f"{remaining_days} day{'s' if remaining_days != 1 else ''}"

def calculate_how_long_ago_member_created(member) -> str:
    """
    Calculate and format how long ago a member created their account.
    
    Args:
        member: discord.Member object
        
    Returns:
        str: Formatted time string
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    created = member.created_at
    
    # Calculate time difference
    delta = now - created
    
    # Format the difference in a human-readable way
    days = delta.days
    years = days // 365
    months = (days % 365) // 30
    remaining_days = days % 30
    
    if years > 0:
        return f"{years} year{'s' if years != 1 else ''}, {months} month{'s' if months != 1 else ''}, {remaining_days} day{'s' if remaining_days != 1 else ''}"
    elif months > 0:
        return f"{months} month{'s' if months != 1 else ''}, {remaining_days} day{'s' if remaining_days != 1 else ''}"
    else:
        return f"{remaining_days} day{'s' if remaining_days != 1 else ''}"
