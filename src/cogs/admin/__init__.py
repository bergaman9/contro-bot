"""Admin cogs module."""

async def setup(bot):
    """Setup function for admin cogs."""
    from .bot_management import BotSettings
    from .server_setup import ServerSetup
    from .settings import Settings
    
    await bot.add_cog(BotSettings(bot))
    await bot.add_cog(ServerSetup(bot))
    await bot.add_cog(Settings(bot))
