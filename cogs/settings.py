import discord
from discord import app_commands
from discord.ext import commands

from utility.utils import create_embed, initialize_mongodb


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    @commands.hybrid_command(name="set_report_channel", description="Set the channel where reports will be sent.")
    @app_commands.describe(channel="Channel to set.")
    @commands.has_permissions(manage_guild=True)
    async def set_report_channel(self, ctx, channel: discord.TextChannel):
        await ctx.defer()
        self.mongo_db['settings'].update_one(
            {"guild_id": ctx.guild.id},
            {
                "$set": {
                    "report_channel_id": channel.id
                }
            },
            upsert=True
        )
        await ctx.send(embed=create_embed(f"Report channel has been set to {channel.mention}.", discord.Colour.green()))


async def setup(bot):
    await bot.add_cog(Settings(bot))
