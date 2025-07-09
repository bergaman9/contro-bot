"""Utility cogs module."""

# This allows loading the cogs as a package
from . import info, general, ai_chat, tickets, temp_channels, starboard, invites, interface, bump


async def setup(bot):
    """Setup function for loading all utility cogs."""
    from .info import InfoUtility
    from .general import Utility
    from .custom_commands_manager import CustomCommandsManager
    
    await bot.add_cog(InfoUtility(bot))
    await bot.add_cog(Utility(bot))
    await bot.add_cog(CustomCommandsManager(bot))
