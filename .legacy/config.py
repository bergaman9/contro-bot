import discord, time
from discord.ext import commands
from discord import app_commands
import psutil
import platform
import requests
from datetime import datetime, timedelta
import math

import asyncio

from core.class_utils import Paginator

# Add the missing create_embed function
def create_embed(description, color=discord.Color.blue()):
    """Create a simple embed with description and color"""
    return discord.Embed(description=description, color=color)

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
        # Make sure commands are synced on cog load
        self._sync_commands_task = self.bot.loop.create_task(self._sync_commands())
        
    async def _sync_commands(self):
        """Ensure commands are properly synced"""
        try:
            await self.bot.wait_until_ready()
            # Only sync if we're in the primary bot instance to avoid rate limiting
            if getattr(self.bot, 'is_primary_instance', True):
                await self.bot.tree.sync()
                print("Command tree successfully synced")
        except Exception as e:
            print(f"Error syncing command tree: {e}")

    @commands.hybrid_command(name="ping", description="Shows the latency between in the bot and the Discord API.", aliases=["latency"])
    async def ping(self, ctx: commands.Context):
        """Display latency and system information"""
        try:
            # Get basic info
            latency = round(self.bot.latency * 1000)  # latency in ms
            uptime = str(timedelta(seconds=int(round(time.time() - self.bot.startTime))))
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get server region/provider from ipwho.is
            try:
                ip_resp = requests.get("https://ipwho.is/").json()
                server_country = ip_resp.get("country", "N/A")
                server_city = ip_resp.get("city", "N/A")
                server_provider_name = ip_resp.get("connection", {}).get("isp", "N/A")
                server_flag = ip_resp.get("flag", {}).get("emoji", "")
                server_region = f"{server_flag} `{server_country}, {server_city}`" if server_flag else f"{server_country}, {server_city}"
                server_provider = f"🌐 `{server_provider_name}`"
            except Exception:
                server_region = server_provider = "N/A"
                
            # Get bot version if available
            version = getattr(self.bot, "version", "N/A")
            
            embed = discord.Embed(
                title="🏓 Ping & Hosting Info",
                color=0x45C2BE
            )
            
            embed.add_field(name='Ping', value=f'`{latency}ms`', inline=True)
            embed.add_field(name='Uptime', value=f'`{uptime}`', inline=True)
            embed.add_field(name='Bot Version', value=f'`{version}`', inline=True)
            
            embed.add_field(name='CPU Usage', value=f'`{cpu_percent}%`', inline=True)
            embed.add_field(name='RAM Usage', value=f'`{memory.percent}% ({memory.used / 1024**2:.1f}MB / {memory.total / 1024**2:.1f}MB)`', inline=True)
            embed.add_field(name='Disk Usage', value=f'`{disk.percent}% ({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)`', inline=True)
            
            embed.add_field(name='Discord.py', value=f'`{discord.__version__}`', inline=True)
            embed.add_field(name='Python', value=f'`{platform.python_version()}`', inline=True)
            embed.add_field(name='Platform', value=f'`{platform.system()} {platform.release()}`', inline=True)
            
            embed.add_field(name='Server Region', value=f'{server_region}', inline=True)
            embed.add_field(name='Server Provider', value=f'{server_provider}', inline=True)
            embed.add_field(name='Active Servers', value=f'`{len(self.bot.guilds)}`', inline=True)
            
            embed.add_field(name='Active Users', value=f'`{len(self.bot.users)}`', inline=True)
            embed.add_field(name='Active Commands', value=f'`{len(self.bot.commands)}`', inline=True)
            
            if self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)
                
            # Footer: user emoji (if exists) - username - date
            user_emoji = getattr(ctx.author, 'display_avatar', None)
            user_emoji_url = user_emoji.url if user_emoji else None
            now_str = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            footer_text = f"Requested by {ctx.author} - {now_str}"
            
            if user_emoji_url:
                embed.set_footer(text=footer_text, icon_url=user_emoji_url)
            else:
                embed.set_footer(text=footer_text)
                
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Error in ping command: {e}")
            await ctx.send(embed=discord.Embed(description="An error occurred while getting server status.", color=discord.Color.red()))

    @commands.hybrid_command(name="contro_guilds", description="Shows a list of all servers the bot is in.")
    @commands.is_owner()
    async def contro_guilds(self, ctx):
        """Shows a list of all servers the bot is in with detailed information."""
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

    @commands.hybrid_command(name="support", description="Shows information about the bot's support server.")
    async def support(self, ctx):
        """Provides links to the bot's support server, invite link, and other helpful resources."""
        embed = discord.Embed(title=f"Do you need help {ctx.author.name}?", description="You can join bot's support server: \nhttps://discord.gg/ynGqvsYxah", color=discord.Color.pink())
        await ctx.send(embed=embed, view=SupportView(self.bot))

    @commands.hybrid_command(name="version", description="Shows the current bot version and planned features.")
    async def version(self, ctx):
        """Displays information about the bot's current version and planned features."""
        view = VersionButtonView(self.bot)
        await view.send_initial_message(ctx, self.bot)

    @commands.hybrid_command(
        name="resource_monitor", 
        description="Configure resource monitoring settings"
    )
    @commands.is_owner()
    @app_commands.describe(
        interval="Monitoring interval in seconds (0 to disable)",
        action="Action to perform: configure, reset, or status"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Configure", value="configure"),
        app_commands.Choice(name="Reset Statistics", value="reset"),
        app_commands.Choice(name="Show Status", value="status")
    ])
    async def resource_monitor(self, ctx, interval: int = None, action: str = "configure"):
        """Configure the resource monitoring system"""
        if not hasattr(self.bot, 'resource_monitor'):
            await ctx.send(embed=create_embed("Resource monitoring is not available.", discord.Color.red()))
            return
        
        # Just show status
        if action == "status":
            status = "Active" if self.bot.resource_monitor.is_running else "Inactive"
            interval = self.bot.resource_monitor.interval
            cog_count = len(getattr(self.bot.resource_monitor, 'cog_metrics', {}))
            
            embed = discord.Embed(
                title="Resource Monitor Status",
                description="Current configuration of the resource monitoring system",
                color=discord.Color.blue()
            )
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Interval", value=f"{interval} seconds", inline=True)
            embed.add_field(name="Cogs Tracked", value=str(cog_count), inline=True)
            
            # Get memory usage if available
            if hasattr(self.bot.resource_monitor, "get_current_usage"):
                usage = self.bot.resource_monitor.get_current_usage()
                embed.add_field(
                    name="Bot Memory", 
                    value=f"{usage['bot']['memory_mb']:.2f} MB", 
                    inline=True
                )
                embed.add_field(
                    name="Bot CPU", 
                    value=f"{usage['bot']['cpu_percent']:.2f}%", 
                    inline=True
                )
                embed.add_field(
                    name="System Memory", 
                    value=f"{usage['system']['memory_percent']:.2f}%", 
                    inline=True
                )
            
            embed.set_footer(text="Use '/resources detailed' to view current statistics")
            
            await ctx.send(embed=embed)
            return
            
        # Reset statistics
        elif action == "reset":
            if hasattr(self.bot.resource_monitor, 'cog_metrics'):
                self.bot.resource_monitor.cog_metrics = {}
                self.bot.resource_monitor.cog_snapshots = {}
                await ctx.send(embed=create_embed("Resource monitoring statistics have been reset.", discord.Color.green()))
            return
            
        # Configure interval
        else:  # configure
            if interval is None:
                await ctx.send(embed=create_embed("Please specify an interval in seconds.", discord.Color.yellow()))
                return
                
            if interval <= 0:
                self.bot.resource_monitor.stop()
                await ctx.send(embed=create_embed("Resource monitoring disabled.", discord.Color.blue()))
                return
                
            self.bot.resource_monitor.interval = interval
            
            if not self.bot.resource_monitor.is_running:
                self.bot.resource_monitor.start()
                await ctx.send(embed=create_embed(f"Resource monitoring started with {interval}s interval.", discord.Color.green()))
            else:
                # Restart to apply new interval
                self.bot.resource_monitor.stop()
                self.bot.resource_monitor.interval = interval
                self.bot.resource_monitor.start()
                await ctx.send(embed=create_embed(f"Resource monitoring interval updated to {interval}s.", discord.Color.green()))

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        try:
            # Handle button interactions
            if interaction.type == discord.InteractionType.component:
                custom_id = interaction.data.get("custom_id")
                if custom_id == "idea_button":
                    await interaction.response.send_modal(IdeaModal())
                    return
            
            # Handle modal submissions
            elif interaction.type == discord.InteractionType.modal_submit:
                components = interaction.data.get('components', [])
                if not components:
                    return
                    
                component = components[0].get('components', [{}])[0]
                if component.get('custom_id') == "idea_text":
                    idea = component.get('value', '')
                    await self._handle_idea_submission(interaction, idea)
        except Exception as e:
            print(f"Error in on_interaction: {e}")
    
    async def _handle_idea_submission(self, interaction: discord.Interaction, idea: str):
        """Helper method to handle idea submissions"""
        try:
            # Create and send embed to the ideas channel
            embed = discord.Embed(description=idea, color=discord.Color.pink())
            embed.set_author(name=f"Idea of {interaction.user.name}", icon_url=interaction.user.avatar.url)
            
            # Get ideas channel and send message
            channel = self.bot.get_channel(970327943312191488)
            if not channel:
                await interaction.response.send_message(
                    embed=discord.Embed(title="Error", description="Ideas channel not found.", color=discord.Color.red()),
                    ephemeral=True
                )
                return
                
            message = await channel.send(embed=embed)
            
            # Send confirmation to user
            await interaction.response.send_message(
                embed=discord.Embed(title="Your idea has been sent to the developer.",
                                    description="Thank you for your idea.", color=discord.Color.pink()))
            
            # Add reactions to the idea message
            await message.add_reaction("👍")
            await message.add_reaction("👎")
            
            # Delete the interaction message after 30 seconds
            await asyncio.sleep(30)
            if interaction.message:
                await interaction.message.delete()
        except Exception as e:
            print(f"Error handling idea submission: {e}")

async def setup(bot):
    await bot.add_cog(Config(bot))