"""
Discord helper utilities for common operations.
This module provides helper functions for Discord-related operations.
"""
import discord
from discord.ext import commands
import logging
from typing import Optional, Union, List, Dict, Any, Tuple, TypeVar

logger = logging.getLogger(__name__)

# Type aliases for clarity
ContextOrInteraction = Union[commands.Context, discord.Interaction]
T = TypeVar('T')

def check_if_ctx_or_interaction(ctx_or_interaction: ContextOrInteraction) -> Tuple[bool, bool]:
    """
    Check if the provided object is a Context or Interaction and return appropriate flags.
    
    Args:
        ctx_or_interaction: Either a commands.Context or discord.Interaction object
        
    Returns:
        Tuple[bool, bool]: (is_context, is_interaction)
    """
    is_context = isinstance(ctx_or_interaction, commands.Context)
    is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
    
    return is_context, is_interaction

async def respond_to_ctx_or_interaction(
    ctx_or_interaction: ContextOrInteraction, 
    content: Optional[str] = None, 
    embed: Optional[discord.Embed] = None,
    view: Optional[discord.ui.View] = None,
    ephemeral: bool = False
) -> None:
    """
    Respond to either a Context or Interaction with consistent handling.
    
    Args:
        ctx_or_interaction: Either a commands.Context or discord.Interaction
        content: Text content to send
        embed: Embed to send
        view: View to attach
        ephemeral: Whether the response should be ephemeral (only applies to interactions)
    """
    is_context, is_interaction = check_if_ctx_or_interaction(ctx_or_interaction)
    
    try:
        if is_interaction:
            # Handle interaction response
            interaction = ctx_or_interaction
            
            # Check if we've already responded
            if interaction.response.is_done():
                # If we've already responded, use followup
                await interaction.followup.send(
                    content=content,
                    embed=embed,
                    view=view,
                    ephemeral=ephemeral
                )
            else:
                # Initial response
                await interaction.response.send_message(
                    content=content,
                    embed=embed,
                    view=view,
                    ephemeral=ephemeral
                )
        elif is_context:
            # Handle context response
            await ctx_or_interaction.send(
                content=content,
                embed=embed,
                view=view
            )
        else:
            logger.error(f"Unknown type for response: {type(ctx_or_interaction)}")
    
    except Exception as e:
        logger.error(f"Error responding to context/interaction: {e}")
        
        # Try fallback method if possible
        try:
            if hasattr(ctx_or_interaction, 'send'):
                await ctx_or_interaction.send(
                    content=content or "An error occurred while processing your request.",
                    embed=embed
                )
        except Exception as fallback_error:
            logger.error(f"Fallback response also failed: {fallback_error}")

def create_basic_embed(
    title: Optional[str] = None, 
    description: Optional[str] = None,
    color: Optional[discord.Color] = None,
    footer: Optional[str] = None,
    thumbnail: Optional[str] = None,
    image: Optional[str] = None
) -> discord.Embed:
    """
    Create a basic Discord embed with common parameters.
    
    Args:
        title: Title of the embed
        description: Description of the embed
        color: Color of the embed
        footer: Footer text
        thumbnail: URL for thumbnail
        image: URL for image
        
    Returns:
        discord.Embed: The created embed
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or discord.Color.blurple()
    )
    
    if footer:
        embed.set_footer(text=footer)
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
        
    if image:
        embed.set_image(url=image)
        
    return embed

# Other helper functions can be added here as needed
