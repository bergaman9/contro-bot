"""Community cogs module."""

async def setup(bot):
    """Setup function for community cogs."""
    from .autorole import AutoRole
    from .leveling import Levelling
    from .registration import Register
    from .welcome import Welcomer
    
    await bot.add_cog(AutoRole(bot))
    await bot.add_cog(Levelling(bot))
    await bot.add_cog(Register(bot))
    await bot.add_cog(Welcomer(bot))
