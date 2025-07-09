"""Moderation cogs module."""

async def setup(bot):
    """Setup function for moderation cogs."""
    from .actions import ModerationActions
    from .logging import EventLogger
    
    await bot.add_cog(ModerationActions(bot))
    await bot.add_cog(EventLogger(bot))
