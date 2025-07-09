"""Ping command cog."""
import discord
from discord.ext import commands
from ..base import BaseCog
from ...utils.helpers.time import Timer


class PingCog(BaseCog):
    """Cog for ping command."""
    
    def __init__(self, bot):
        super().__init__(bot)
    
    @discord.slash_command(
        name="ping",
        description="Check bot latency"
    )
    async def ping(self, ctx: discord.ApplicationContext):
        """Check bot latency."""
        with Timer() as timer:
            # Initial response
            embed = discord.Embed(
                title="🏓 Pong!",
                description="Calculating latency...",
                color=discord.Color.blue()
            )
            await ctx.respond(embed=embed)
            
        # Calculate latencies
        api_latency = timer.elapsed_ms
        ws_latency = self.bot.latency * 1000
        
        # Update with results
        embed = discord.Embed(
            title="🏓 Pong!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="WebSocket Latency",
            value=f"{ws_latency:.1f}ms",
            inline=True
        )
        embed.add_field(
            name="API Latency",
            value=f"{api_latency:.1f}ms",
            inline=True
        )
        
        # Add status indicator
        total_latency = ws_latency + api_latency
        if total_latency < 100:
            status = "🟢 Excellent"
        elif total_latency < 200:
            status = "🟡 Good"
        elif total_latency < 500:
            status = "🟠 Fair"
        else:
            status = "🔴 Poor"
        
        embed.add_field(
            name="Status",
            value=status,
            inline=True
        )
        
        await ctx.edit(embed=embed)
    
    @commands.command(name="ping", aliases=["p"])
    async def ping_prefix(self, ctx: commands.Context):
        """Check bot latency (prefix version)."""
        with Timer() as timer:
            message = await ctx.send("🏓 Pinging...")
        
        api_latency = timer.elapsed_ms
        ws_latency = self.bot.latency * 1000
        
        await message.edit(
            content=f"🏓 Pong! WebSocket: {ws_latency:.1f}ms | API: {api_latency:.1f}ms"
        )


def setup(bot):
    """Load the cog."""
    bot.add_cog(PingCog(bot)) 