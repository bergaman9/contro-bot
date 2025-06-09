"""Discord-specific utility functions."""
import discord
from .formatting import create_embed
import re
import logging
from discord.ext import commands
from typing import Union, Optional

# Logger setup
logger = logging.getLogger(__name__)

async def create_text_channel(guild, channel_name, category_name="Games"):
    """Create a text channel in the specified guild and category."""
    category = get_category_by_name(guild, category_name)
    await guild.create_text_channel(channel_name, category=category)
    channel = get_channel_by_name(guild, channel_name)
    return channel

async def create_voice_channel(guild, channel_name, category_name="Voice Channels", user_limit=None):
    """Create a voice channel in the specified guild and category."""
    category = get_category_by_name(guild, category_name)
    await guild.create_voice_channel(channel_name, category=category, user_limit=user_limit)
    channel = get_channel_by_name(guild, channel_name)
    return channel

async def get_invite_link(guild):
    """Get or create an invite link for the specified guild."""
    invites = await guild.invites()
    if invites:
        return invites[0].url
    else:
        try:
            link = await guild.text_channels[0].create_invite()
            return link.url
        except discord.Forbidden:
            return "No permission to create invite"

def get_channel_by_name(guild, channel_name):
    """Get a channel by name from the specified guild."""
    channel = None
    for c in guild.channels:
        if c.name == channel_name.lower():
            channel = c
            break
    return channel

def get_category_by_name(guild, category_name):
    """Get a category by name from the specified guild."""
    category = None
    for c in guild.channels:
        if c.name == category_name and isinstance(c, discord.CategoryChannel):
            category = c
            break
    return category

async def check_if_ctx_or_interaction(ctx_or_interaction):
    """Handle both Context and Interaction objects uniformly."""
    if isinstance(ctx_or_interaction, discord.ext.commands.Context):
        guild = ctx_or_interaction.guild
        send = ctx_or_interaction.send
        channel = ctx_or_interaction.channel
        followup_send = None
    elif isinstance(ctx_or_interaction, discord.Interaction):
        guild = ctx_or_interaction.guild
        send = ctx_or_interaction.response.send_message
        followup_send = ctx_or_interaction.followup.send
        channel = ctx_or_interaction.channel
    else:
        raise ValueError("Unknown context received")

    return guild, send, channel, followup_send

def generate_members_of_role_embeds(members, role):
    """Generate a list of embeds showing members with a specific role."""
    members_per_embed = 20
    embeds = []

    for i in range(0, len(members), members_per_embed):
        current_members = members[i:i + members_per_embed]
        embed = discord.Embed(title=f"{role.name} Rolündeki Üyeler", color=role.color)

        # Add members to embed
        member_string = "\n".join(member.mention for member in current_members)
        embed.description = member_string

        embeds.append(embed)

    return embeds

def get_channel_from_mention(bot, mention_or_id, guild=None):
    """
    Get a channel from a mention string or ID
    
    Args:
        bot: The Discord bot instance
        mention_or_id: A channel mention (<#123456789>) or a channel ID (as string or int)
        guild: Optional guild to limit channel search to
        
    Returns:
        The channel object if found, otherwise None
    """
    # Check if it's a mention
    if isinstance(mention_or_id, str):
        # Try to match channel mention format
        match = re.match(r'<#(\d+)>', mention_or_id)
        if match:
            channel_id = int(match.group(1))
        else:
            # Try to convert to int if it's a plain ID
            try:
                channel_id = int(mention_or_id)
            except ValueError:
                return None
    elif isinstance(mention_or_id, int):
        channel_id = mention_or_id
    else:
        return None
    
    # First try to get from the specific guild if provided
    if guild:
        channel = guild.get_channel(channel_id)
        if channel:
            return channel
    
    # Then try from all available guilds
    return bot.get_channel(channel_id)

def is_bot_admin(ctx_or_interaction):
    """Check if the user is a bot admin."""
    if isinstance(ctx_or_interaction, commands.Context):
        user_id = ctx_or_interaction.author.id
    else:  # Assume it's an Interaction
        user_id = ctx_or_interaction.user.id
        
    # Get bot admins from config
    try:
        bot = ctx_or_interaction.bot
        admins = getattr(bot, 'config', {}).get('admins', [])
        return user_id in admins
    except Exception as e:
        logger.error(f"Error checking if user is admin: {e}")
        return False

def is_guild_owner(ctx_or_interaction):
    """Check if the user is the guild owner."""
    if isinstance(ctx_or_interaction, commands.Context):
        return ctx_or_interaction.author.id == ctx_or_interaction.guild.owner_id
    else:  # Assume it's an Interaction
        return ctx_or_interaction.user.id == ctx_or_interaction.guild.owner_id

def get_user_permissions(guild, member):
    """Get a list of permission names the member has in the guild."""
    if not guild or not member:
        return []
        
    permissions = member.guild_permissions
    return [perm for perm, value in permissions if value]

def check_required_permissions(ctx_or_interaction, required_permissions):
    """Check if the user has all the required permissions."""
    if isinstance(ctx_or_interaction, commands.Context):
        permissions = ctx_or_interaction.author.guild_permissions
    else:  # Assume it's an Interaction
        permissions = ctx_or_interaction.user.guild_permissions
        
    return all(getattr(permissions, perm, False) for perm in required_permissions)

async def send_paginated_embed(ctx_or_interaction, embed_text, title=None, color=None, 
                         max_chars=2000, footer=None, author=None, thumbnail=None):
    """Send a long text as paginated embeds."""
    # Set defaults
    color = color or discord.Color.blue()
    
    # Split the content into chunks respecting Discord's embed limits
    chunks = []
    current_chunk = ""
    
    # Split by newlines to keep paragraphs together when possible
    paragraphs = embed_text.split("\n")
    
    for paragraph in paragraphs:
        # Check if adding this paragraph would exceed the limit
        if len(current_chunk) + len(paragraph) + 1 > max_chars:
            # If the current chunk is not empty, add it to chunks
            if current_chunk:
                chunks.append(current_chunk)
                
            # Start a new chunk with this paragraph
            current_chunk = paragraph
        else:
            # Add to current chunk with newline if not empty
            if current_chunk:
                current_chunk += "\n" + paragraph
            else:
                current_chunk = paragraph
    
    # Add the last chunk if not empty
    if current_chunk:
        chunks.append(current_chunk)
    
    # Create embeds for each chunk
    embeds = []
    for i, chunk in enumerate(chunks):
        embed = discord.Embed(description=chunk, color=color)
        
        # Only add title to the first page
        if i == 0 and title:
            embed.title = title
            
        # Add page number to footer if multiple pages
        if len(chunks) > 1:
            page_footer = f"Page {i+1}/{len(chunks)}"
            if footer:
                page_footer = f"{footer} • {page_footer}"
            embed.set_footer(text=page_footer)
        elif footer:
            embed.set_footer(text=footer)
            
        # Only add author and thumbnail to first page
        if i == 0:
            if author:
                embed.set_author(name=author.name, icon_url=author.avatar.url if author.avatar else None)
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
                
        embeds.append(embed)
    
    # Send embeds
    for embed in embeds:
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed)
        else:  # Interaction
            # For first embed use the original interaction
            if embed == embeds[0] and not ctx_or_interaction.response.is_done():
                await ctx_or_interaction.response.send_message(embed=embed)
            else:
                # For additional embeds, follow up
                await ctx_or_interaction.followup.send(embed=embed)
                
# Add other Discord-related functions here
