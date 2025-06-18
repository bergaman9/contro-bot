"""Formatting and presentation utilities."""
import discord
from datetime import datetime

def create_embed(description, color, title=None, footer=None):
    """Create a Discord embed with the specified description, color, and optional title and footer."""
    embed = discord.Embed(description=description, colour=color)
    if title:
        embed.title = title
    if footer:
        embed.set_footer(text=footer)
    return embed

def hex_to_int(hex_color):
    """Convert a hex color to an integer."""
    hex_color = hex_color.lstrip('#')  # Remove '#' if present
    return int(hex_color, 16)

def format_number(number, round_digits=1):
    """Format a number with K, M, B suffix for thousands, millions, billions"""
    if number is None:
        return "0"
    
    number = float(number)
    
    if number < 1000:
        return str(int(number) if number.is_integer() else round(number, round_digits))
    elif number < 1000000:
        return f"{round(number/1000, round_digits)}K"
    elif number < 1000000000:
        return f"{round(number/1000000, round_digits)}M"
    else:
        return f"{round(number/1000000000, round_digits)}B"

def format_timestamp(timestamp, format_type="f"):
    """
    Format a timestamp for Discord's timestamp formatting.
    Format types:
    - t: Short Time (e.g., 9:41 PM)
    - T: Long Time (e.g., 9:41:30 PM)
    - d: Short Date (e.g., 30/06/2021)
    - D: Long Date (e.g., 30 June 2021)
    - f: Short Date/Time (e.g., 30 June 2021 9:41 PM)
    - F: Long Date/Time (e.g., Wednesday, 30 June 2021 9:41 PM)
    - R: Relative Time (e.g., 2 months ago, in an hour)
    """
    if isinstance(timestamp, datetime):
        unix_timestamp = int(timestamp.timestamp())
    else:
        unix_timestamp = int(timestamp)
    
    return f"<t:{unix_timestamp}:{format_type}>"

def calculate_how_long_ago_member_joined(member):
    """Calculate how long ago a member joined the server."""
    time_difference = datetime.utcnow() - member.joined_at.replace(tzinfo=None)
    
    years, days_remainder = divmod(time_difference.days, 365)
    days = days_remainder
    hours, remainder = divmod(time_difference.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if years > 0:
        return f"{years} years ago" if years > 1 else "1 year ago"
    if days > 0:
        return f"{days} days ago" if days > 1 else "1 day ago"
    if hours > 0:
        return f"{hours} hours ago" if hours > 1 else "1 hour ago"
    if minutes > 0:
        return f"{minutes} minutes ago" if minutes > 1 else "1 minute ago"
    return f"{seconds} seconds ago" if seconds > 0 else "just now"

def calculate_how_long_ago_member_created(member):
    """Calculate how long ago a member's Discord account was created."""
    time_difference = datetime.utcnow() - member.created_at.replace(tzinfo=None)
    
    years, days_remainder = divmod(time_difference.days, 365)
    days = days_remainder
    hours, remainder = divmod(time_difference.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if years > 0:
        return f"{years} years ago" if years > 1 else "1 year ago"
    if days > 0:
        return f"{days} days ago" if days > 1 else "1 day ago"
    if hours > 0:
        return f"{hours} hours ago" if hours > 1 else "1 hour ago"
    if minutes > 0:
        return f"{minutes} minutes ago" if minutes > 1 else "1 minute ago"
    return f"{seconds} seconds ago" if seconds > 0 else "just now"

def check_video_url(message_content):
    """Check if a message content contains a video URL."""
    video_platforms = ["youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", "twitch.tv"]
    message_content = message_content.strip().lower()
    for platform in video_platforms:
        if platform in message_content:
            return True
    return False

# Add other formatting/time-related functions here
