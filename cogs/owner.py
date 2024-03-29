import math

import discord
from discord import app_commands
from discord.ext import commands

from utility.class_utils import Paginator, ReportModal
from utils import initialize_mongodb


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = initialize_mongodb()
        self.report_menu = app_commands.ContextMenu(
            name='Şikayet Et',
            callback=self.report_message,
        )
        self.bot.tree.add_command(self.report_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.report_menu.name, type=self.report_menu.type)

    async def report_message(self, interaction: discord.Interaction, message: discord.Message) -> None:
        await interaction.response.send_modal(ReportModal(message=message))

    @commands.hybrid_command(name="contro_guilds", description="Shows guilds.")
    @commands.is_owner()
    async def contro_guilds(self, ctx):
        try:
            await ctx.defer()
            guilds_sorted = sorted(self.bot.guilds, key=lambda g: g.created_at,
                                   reverse=True)  # Sunucuları tarihe göre sırala

            each_page = 7
            pages = math.ceil(len(guilds_sorted) / each_page)
            embeds = []

            for page in range(pages):
                embed = discord.Embed(title=f"Server List ({len(guilds_sorted)})", color=discord.Color.pink())
                start_idx = page * each_page
                end_idx = start_idx + each_page

                for guild in guilds_sorted[start_idx:end_idx]:
                    try:
                        invites = await guild.invites()
                        first_invite = invites[0].url if invites else 'No invite link'
                    except Exception:  # Tüm exceptionları yakalamak için genel bir Exception kullanın
                        first_invite = 'No invite link'
                    member = await guild.fetch_member(783064615012663326)
                    embed.add_field(
                        name=f"{guild.name} ({guild.member_count})",
                        value=f"*Owner:* <@{guild.owner_id}> \n*Join Date:* {member.joined_at.strftime('%m/%d/%Y, %H:%M:%S')} \n*Invite:* {first_invite}",
                        inline=False
                    )
                embed.set_footer(text=f"Page: {page + 1}/{pages}")
                embeds.append(embed)

            view = Paginator(embeds)
            await view.send_initial_message(ctx)
        except Exception as e:
            print(e)


async def setup(bot):
    await bot.add_cog(Owner(bot))
