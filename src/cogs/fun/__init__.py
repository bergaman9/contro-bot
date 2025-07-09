"""Fun cogs module."""

async def setup(bot):
    """Setup function for fun cogs."""
    from .game_stats import GameStats
    from .spin import Spin
    from .giveaways import Giveaways
    from .games import Fun
    
    await bot.add_cog(GameStats(bot))
    await bot.add_cog(Spin(bot))
    await bot.add_cog(Giveaways(bot))
    await bot.add_cog(Fun(bot))
