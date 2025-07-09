import discord
import logging
import traceback
from typing import Optional, Union
from discord.ext import commands

from .formatting import create_embed

logger = logging.getLogger('error_handler')

async def handle_interaction_error(
    interaction: discord.Interaction, 
    error: Exception,
    response_message: Optional[str] = None,
    log_error: bool = True
) -> bool:
    """
    Handle an interaction error gracefully
    
    Args:
        interaction: The Discord interaction that failed
        error: The exception that was raised
        response_message: Optional custom message to show the user
        log_error: Whether to log the error details
    
    Returns:
        bool: True if handled successfully, False otherwise
    """
    if log_error:
        # Get user and guild info for logging
        user_info = f"{interaction.user} (ID: {interaction.user.id})" if interaction.user else "Unknown user"
        guild_info = f"{interaction.guild.name} (ID: {interaction.guild.id})" if interaction.guild else "DM"
        
        # Format component info
        component_info = "Unknown"
        custom_id = "Unknown"
        
        try:
            if hasattr(interaction, 'data') and interaction.data:
                component_type = interaction.data.get('component_type', 'Unknown')
                custom_id = interaction.data.get('custom_id', 'Unknown')
                component_info = f"Type: {component_type}, ID: {custom_id}"
        except Exception:
            pass
            
        # Get the error traceback
        error_tb = traceback.format_exc()
        
        # Log the error details
        logger.error(
            f"Interaction error: {error.__class__.__name__}\n"
            f"User: {user_info} | Guild: {guild_info}\n" 
            f"Component: {component_info}\n"
            f"Error details: {str(error)}\n"
            f"Traceback:\n{error_tb}"
        )
    
    # Create a user-friendly error message
    if not response_message:
        response_message = f"❌ An error occurred: {str(error)}"
    
    # Try to respond to the user
    try:
        if not interaction.response.is_done():
            # If the interaction hasn't been responded to yet
            await interaction.response.send_message(
                embed=create_embed(description=response_message, color=discord.Color.red()),
                ephemeral=True
            )
        else:
            # If the interaction has already been responded to
            await interaction.followup.send(
                embed=create_embed(description=response_message, color=discord.Color.red()),
                ephemeral=True
            )
        return True
    except Exception as respond_error:
        logger.error(f"Failed to respond to interaction error: {respond_error}")
        return False

def setup_error_handlers(bot):
    """
    Set up global error handlers for a bot instance
    
    Args:
        bot: The Discord bot instance
    """
    # Register global error handler for application commands
    @bot.event
    async def on_application_command_error(ctx, error):
        await handle_interaction_error(ctx.interaction, error)
    
    # Register global error handler for normal command errors
    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
            
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                embed=create_embed(
                    description="❌ You don't have permission to use this command.",
                    color=discord.Color.red()
                )
            )
            return
            
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                embed=create_embed(
                    description=f"❌ Command on cooldown. Try again in {error.retry_after:.1f} seconds.",
                    color=discord.Color.orange()
                )
            )
            return
            
        # Log the error
        logger.error(f"Command error in {ctx.command}: {error}\n{traceback.format_exc()}")
        
        # Send a user-friendly error message
        await ctx.send(
            embed=create_embed(
                description=f"❌ An error occurred: {str(error)}",
                color=discord.Color.red()
            )
        )
    
    logger.info("Global error handlers have been set up")

class ErrorLogger:
    """Utility class for logging errors with context"""
    
    @staticmethod
    def log(error, context=None, should_print=True):
        """
        Log an error with optional context information
        
        Args:
            error: The exception to log
            context: Optional context information (string or dict)
            should_print: Whether to also print the error to console
        """
        error_message = f"Error: {error.__class__.__name__}: {str(error)}"
        
        if context:
            if isinstance(context, dict):
                context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            else:
                context_str = str(context)
            error_message = f"{error_message}\nContext: {context_str}"
        
        error_tb = traceback.format_exc()
        logger.error(f"{error_message}\n{error_tb}")
        
        if should_print:
            print(f"\n❌ {error_message}")
