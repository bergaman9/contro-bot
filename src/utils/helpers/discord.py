"""Discord-specific helper utilities."""
import discord
from discord.ext import commands
from typing import Optional, Union, List
import re


def get_member_display_name(member: discord.Member) -> str:
    """Get the best display name for a member."""
    return member.display_name or member.name


def get_user_avatar_url(user: Union[discord.User, discord.Member]) -> str:
    """Get user's avatar URL or default avatar."""
    return user.display_avatar.url if user.display_avatar else user.default_avatar.url


def create_embed(
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[discord.Color] = None,
    thumbnail: Optional[str] = None,
    image: Optional[str] = None,
    author: Optional[dict] = None,
    footer: Optional[dict] = None,
    fields: Optional[List[dict]] = None,
    timestamp: Optional[bool] = False
) -> discord.Embed:
    """Create a Discord embed with common styling."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or discord.Color.blue()
    )
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    if image:
        embed.set_image(url=image)
    
    if author:
        embed.set_author(
            name=author.get('name', ''),
            icon_url=author.get('icon_url', ''),
            url=author.get('url', '')
        )
    
    if footer:
        embed.set_footer(
            text=footer.get('text', ''),
            icon_url=footer.get('icon_url', '')
        )
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get('name', ''),
                value=field.get('value', ''),
                inline=field.get('inline', True)
            )
    
    if timestamp:
        embed.timestamp = discord.utils.utcnow()
    
    return embed


def parse_user_mention(mention: str) -> Optional[int]:
    """Parse a user mention and return the user ID."""
    match = re.match(r'<@!?(\d+)>', mention)
    return int(match.group(1)) if match else None


def parse_channel_mention(mention: str) -> Optional[int]:
    """Parse a channel mention and return the channel ID."""
    match = re.match(r'<#(\d+)>', mention)
    return int(match.group(1)) if match else None


def parse_role_mention(mention: str) -> Optional[int]:
    """Parse a role mention and return the role ID."""
    match = re.match(r'<@&(\d+)>', mention)
    return int(match.group(1)) if match else None


async def get_or_fetch_user(bot: commands.Bot, user_id: int) -> Optional[discord.User]:
    """Get a user from cache or fetch from API."""
    user = bot.get_user(user_id)
    if user is None:
        try:
            user = await bot.fetch_user(user_id)
        except discord.NotFound:
            return None
    return user


async def get_or_fetch_member(guild: discord.Guild, member_id: int) -> Optional[discord.Member]:
    """Get a member from cache or fetch from API."""
    member = guild.get_member(member_id)
    if member is None:
        try:
            member = await guild.fetch_member(member_id)
        except discord.NotFound:
            return None
    return member


async def get_or_fetch_channel(bot: commands.Bot, channel_id: int) -> Optional[discord.abc.GuildChannel]:
    """Get a channel from cache or fetch from API."""
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            return None
    return channel


def check_permissions(
    member: discord.Member,
    permissions: List[str],
    require_all: bool = True
) -> bool:
    """Check if member has required permissions.
    
    Args:
        member: The member to check
        permissions: List of permission names (e.g., ['manage_messages', 'kick_members'])
        require_all: If True, member must have all permissions. If False, any permission is enough.
    """
    member_perms = member.guild_permissions
    
    if require_all:
        return all(getattr(member_perms, perm, False) for perm in permissions)
    else:
        return any(getattr(member_perms, perm, False) for perm in permissions)


def format_permissions(permissions: discord.Permissions) -> List[str]:
    """Format permissions into readable list."""
    return [
        perm.replace('_', ' ').title()
        for perm, value in permissions
        if value
    ]


def is_bot_mentioned(message: discord.Message) -> bool:
    """Check if the bot is mentioned in a message."""
    return message.guild and message.guild.me in message.mentions


async def safe_delete_message(message: discord.Message, delay: Optional[float] = None) -> bool:
    """Safely delete a message, handling errors."""
    try:
        await message.delete(delay=delay)
        return True
    except (discord.NotFound, discord.Forbidden):
        return False


async def safe_send(
    destination: Union[discord.abc.Messageable, discord.Interaction],
    content: Optional[str] = None,
    embed: Optional[discord.Embed] = None,
    ephemeral: bool = False,
    **kwargs
) -> Optional[discord.Message]:
    """Safely send a message to a destination."""
    try:
        if isinstance(destination, discord.Interaction):
            if destination.response.is_done():
                return await destination.followup.send(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral,
                    **kwargs
                )
            else:
                return await destination.response.send_message(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral,
                    **kwargs
                )
        else:
            return await destination.send(
                content=content,
                embed=embed,
                **kwargs
            )
    except discord.HTTPException:
        return None 