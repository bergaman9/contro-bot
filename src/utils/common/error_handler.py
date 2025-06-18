"""
Error handling utilities for the bot.
This module provides centralized error handling for the bot.
"""
import discord
import logging
import traceback
import sys
from discord.ext import commands

logger = logging.getLogger('error_handler')

def setup_error_handlers(bot):
    """
    Set up global error handlers for the bot.
    
    Args:
        bot: The Discord bot instance
    """
    @bot.event
    async def on_error(event, *args, **kwargs):
        """Global error handler for events"""
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_message = f"Error in {event}: {exc_value}"
        
        # Log the error
        logger.error(error_message, exc_info=True)
        
        # Get the traceback
        tb = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        # Log detailed traceback
        logger.debug(f"Detailed traceback:\n{tb}")
    
    @bot.event
    async def on_command_error(ctx, error):
        """Global error handler for commands"""
        # Get original error if it's wrapped in CommandInvokeError
        error = getattr(error, 'original', error)
        
        # Skip command not found errors
        if isinstance(error, commands.CommandNotFound):
            return
        
        # Handle check failures
        if isinstance(error, commands.CheckFailure):
            await ctx.send("You don't have permission to use this command.", ephemeral=True)
            return
        
        # Handle missing arguments
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: `{error.param.name}`\nUse `help {ctx.command}` for more information.", ephemeral=True)
            return
        
        # Handle cooldowns
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f}s", ephemeral=True)
            return
        
        # Default error handler
        logger.error(f"Command error in {ctx.command}: {error}", exc_info=True)
        await ctx.send("An error occurred while processing your command. The error has been logged.", ephemeral=True)
    
    logger.info("Global error handlers have been set up") 