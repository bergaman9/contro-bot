"""
Example cog demonstrating Application Manager usage
Shows how to use database, cache, and configuration from the central manager
"""

import discord
from discord.ext import commands
from .base import BaseCog, require_feature, log_command


class ExampleCog(BaseCog):
    """Example cog showing Application Manager integration."""
    
    def __init__(self, bot):
        super().__init__(bot)
    
    @commands.command(name="example_ping")
    @log_command("example_ping")
    async def example_ping(self, ctx):
        """Simple ping command from example cog."""
        await ctx.send(f"🏓 Pong! Latency: {round(self.bot.latency * 1000)}ms")
    
    @commands.command(name="stats")
    @require_feature("game_logs")
    @log_command("stats")
    async def stats(self, ctx):
        """Get bot statistics using database and cache."""
        # Get cached stats first
        cache_key = f"stats:{ctx.guild.id}"
        cached_stats = await self.cache_get(cache_key)
        
        if cached_stats:
            await ctx.send(f"📊 **Cached Stats:**\n{cached_stats}")
            return
        
        # Get from database
        db = self.get_database()
        if not db:
            await ctx.send("❌ Database not available.")
            return
        
        try:
            # Get guild stats
            guild_collection = db.get_collection("guilds")
            guild_stats = await guild_collection.find_one({"guild_id": ctx.guild.id})
            
            # Get user stats
            user_collection = db.get_collection("users")
            user_count = await user_collection.count_documents({"guild_id": ctx.guild.id})
            
            stats_text = f"""
📊 **Server Statistics**
👥 Members: {ctx.guild.member_count}
👤 Users in DB: {user_count}
🎮 Guild Settings: {'Configured' if guild_stats else 'Not configured'}
            """.strip()
            
            # Cache for 5 minutes
            await self.cache_set(cache_key, stats_text, ttl=300)
            
            await ctx.send(stats_text)
            
        except Exception as e:
            await self.log_error(e, "stats_command", guild_id=ctx.guild.id)
            await ctx.send("❌ Error fetching statistics.")
    
    @commands.command(name="config")
    @commands.has_permissions(administrator=True)
    @log_command("config")
    async def config(self, ctx):
        """Show current configuration."""
        config = self.get_config()
        if not config:
            await ctx.send("❌ Configuration not available.")
            return
        
        embed = discord.Embed(
            title="🤖 Bot Configuration",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Environment",
            value=config.environment,
            inline=True
        )
        embed.add_field(
            name="Debug Mode",
            value="✅ Enabled" if config.debug else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="API Status",
            value="✅ Enabled" if config.api.enabled else "❌ Disabled",
            inline=True
        )
        
        # Feature flags
        features = []
        if config.features.ai_chat:
            features.append("🤖 AI Chat")
        if config.features.game_logs:
            features.append("🎮 Game Logs")
        if config.features.leveling:
            features.append("📊 Leveling")
        if config.features.moderation:
            features.append("🛡️ Moderation")
        
        embed.add_field(
            name="Enabled Features",
            value="\n".join(features) if features else "None",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="cache")
    @commands.has_permissions(administrator=True)
    @log_command("cache")
    async def cache_info(self, ctx):
        """Show cache information."""
        cache = self.get_cache()
        if not cache:
            await ctx.send("❌ Cache not available.")
            return
        
        try:
            stats = await cache.get_stats()
            
            embed = discord.Embed(
                title="💾 Cache Information",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Status",
                value="✅ Enabled" if stats.get("enabled") else "❌ Disabled",
                inline=True
            )
            embed.add_field(
                name="Redis Connected",
                value="✅ Yes" if stats.get("redis_connected") else "❌ No",
                inline=True
            )
            embed.add_field(
                name="Memory Cache Size",
                value=str(stats.get("memory_cache_size", 0)),
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self.log_error(e, "cache_info")
            await ctx.send("❌ Error fetching cache information.")
    
    @commands.command(name="db")
    @commands.has_permissions(administrator=True)
    @log_command("database")
    async def database_info(self, ctx):
        """Show database information."""
        db = self.get_database()
        if not db:
            await ctx.send("❌ Database not available.")
            return
        
        try:
            stats = await db.get_stats()
            
            embed = discord.Embed(
                title="🗄️ Database Information",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="Database",
                value=stats.get("database", "Unknown"),
                inline=True
            )
            embed.add_field(
                name="Collections",
                value=str(stats.get("collections", 0)),
                inline=True
            )
            embed.add_field(
                name="Data Size",
                value=f"{stats.get('data_size', 0) / 1024 / 1024:.2f} MB",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self.log_error(e, "database_info")
            await ctx.send("❌ Error fetching database information.")


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(ExampleCog(bot)) 