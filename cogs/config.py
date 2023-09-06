import discord, time
from discord.ext import commands
from discord import app_commands
import psutil

from datetime import datetime, timedelta
import datetime

import asyncio


class IdeaModal(discord.ui.Modal, title='Share Idea'):
    idea = discord.ui.TextInput(label='Your idea about bot.', placeholder="Write your idea here.", min_length=10, max_length=1000, row=3, custom_id="idea_text")

class SupportView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Support Server", url="https://discord.gg/ynGqvsYxah"))
        self.add_item(discord.ui.Button(label="Invite Bot", url=f"https://discord.com/api/oauth2/authorize?client_id={bot.application_id}&permissions=8&scope=bot"))
        self.add_item(discord.ui.Button(label="Vote Bot", url="https://top.gg/bot/869041978467201280/vote"))
        self.add_item(discord.ui.Button(label="Share Idea", style=discord.ButtonStyle.green, custom_id="idea_button"))

class VersionButtonView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.message = None
        self.add_item(discord.ui.Button(label="Support Server", url="https://discord.gg/ynGqvsYxah", style=discord.ButtonStyle.url))
        self.add_item(discord.ui.Button(label="Invite Bot",
                                        url=f"https://discord.com/api/oauth2/authorize?client_id={bot.application_id}&permissions=8&scope=bot",
                                        style=discord.ButtonStyle.url))

    async def send_initial_message(self, ctx, bot):
        self.embed_text = """
        * Welcomer Messages with Image \n - `welcomer_set` `welcomer_remove`
        \n* Partner System \n - `partner_add` `partner_remove`
        \n* Game Stats \n - `topgames` `playing`
        \n* Dropdown Roles \n - `dropdown_roles`
        \n* Advanced Logging System \n - `set_log_channel` `remove_log_channel`
        \n* New Fun Commands 
        \n* Reminders \n - `alarm` `reminder`
        \n* Custom Give Roles \n - `give_roles` `give_roles_remove` `give_roles_settings`
        """

        self.embed = discord.Embed(title="Contro Bot Version v1.1",
                              description="You can see the new features on v1.1 of the bot below",
                              color=discord.Color.pink())
        self.embed.add_field(name="New Features", value=self.embed_text, inline=False)
        self.embed.set_thumbnail(url=bot.user.avatar.url)
        self.message = await ctx.send(embed=self.embed, view=self)

    @discord.ui.button(label="v1.0", style=discord.ButtonStyle.blurple)
    async def version_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.on_button_clicked(interaction)

    async def on_button_clicked(self, interaction: discord.Interaction):
        # Ephemeral mesaj gönderin
        self.embed = discord.Embed(title="Contro Bot Version v1.0",
                              description="This bot is v1.0 version and so many features will be added in the future.",
                              color=discord.Color.pink())
        self.embed.add_field(name="**Added in v1.0:**",
                        value="- Partner System \n- New Fun Commands \n- Logging System")
        self.embed.add_field(name="**Planned features:**",
                        value="- Temporary Voice and Text Channels \n- Text and Voice Level System \n- Advanced Logging System \n- Web Dashboard \n- Translation to TR, ENG, GER")

        await interaction.response.send_message(embed=self.embed, ephemeral=True)

    async def on_timeout(self):
        """Timeout bittiğinde bu fonksiyon çağrılır."""
        if self.message:
            await self.message.edit(view=None)

class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Shows the latency between in the bot and the Discord API.")
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)  # latency in ms
        cpu_percent = psutil.cpu_percent(interval=1)
        ram_percent = psutil.virtual_memory().percent

        embed = discord.Embed(title='Ping & Hosting Info', color=discord.Color.pink())
        embed.add_field(name='Ping', value=f'{latency}ms', inline=True)
        embed.add_field(name='CPU Usage', value=f'{cpu_percent}%', inline=True)
        embed.add_field(name='RAM Usage', value=f'{ram_percent}%', inline=True)
        embed.add_field(name='Hosting Region', value='🇪🇺 Europe', inline=True)
        embed.add_field(name='Hosting Provider', value='🐳 DigitalOcean', inline=True)
        embed.add_field(name='Uptime', value=str(timedelta(seconds=int(round(time.time() - self.bot.startTime)))),
                        inline=True)
        embed.add_field(name='Active Servers', value=f'{len(self.bot.guilds)}', inline=True)
        embed.add_field(name='Active Users', value=f'{len(self.bot.users)}', inline=True)
        embed.add_field(name='Active Commands', value=f'{len(self.bot.commands)}', inline=True)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="support", description="Shows the support server.")
    async def support(self, ctx):
        embed = discord.Embed(title="Do you need help " + ctx.author.name +"?", description="You can join bot's support server: \nhttps://discord.gg/ynGqvsYxah", color=discord.Color.pink())
        await ctx.send(embed=embed, view=SupportView(self.bot))

    @commands.hybrid_command(name="version", description="Version and planned features of the bot.")
    async def version(self, ctx):
        view = VersionButtonView(self.bot)
        await view.send_initial_message(ctx, self.bot)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.data.get("custom_id") == "idea_button":
                await interaction.response.send_modal(IdeaModal())

        if interaction.type == discord.InteractionType.modal_submit:
            if interaction.data.get('components')[0].get('components')[0].get('custom_id') == "idea_text":
                idea = interaction.data.get('components')[0].get('components')[0].get('value')
                print(idea)
                embed = discord.Embed(description=idea, color=discord.Color.pink())
                embed.set_author(name="Idea of " + interaction.user.name, icon_url=interaction.user.avatar.url)
                channel = self.bot.get_channel(970327943312191488)
                message = await channel.send(embed=embed)
                await interaction.response.send_message(
                    embed=discord.Embed(title="Your idea has been sent to the developer.",
                                        description="Thank you for your idea.", color=discord.Color.pink()))
                await message.add_reaction("👍")
                await message.add_reaction("👎")
                await asyncio.sleep(30)
                await interaction.message.delete()

async def setup(bot):
    await bot.add_cog(Config(bot))