"""Utility cogs module."""

# This allows loading the cogs as a package
from . import info, general, ai_chat, tickets, temp_channels, starboard, invites, interface, bump


async def setup(bot):
    """Setup function for loading all utility cogs."""
    # Load individual cogs
    await bot.load_extension("src.cogs.utility.info")
    await bot.load_extension("src.cogs.utility.general")
    # Add other utility cogs as needed
