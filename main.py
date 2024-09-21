import asyncio
import os
import time
from datetime import timedelta

import discord
import dotenv
from discord.ext import commands

from utils import create_embed

dotenv.load_dotenv()
TOKEN = os.getenv("CONTRO_TOKEN")


class Bot(commands.Bot):

    def __init__(self) -> None:
        intents = discord.Intents.all()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix=">", intents=intents, help_command=None)

    # async def setup_hook(self) -> None:
    #     # Lavalink sunucularını bir liste içerisinde tanımla
    #     lavalink_servers = [
    #         {"uri": "wss://narco.buses.rocks:2269", "password": "glasshost1984", "secure": False},
    #         {"uri": "wss://lava.horizxon.tech:80", "password": "horizxon.tech", "secure": False},
    #         {"uri": "wss://104.167.222.158:11487", "password": "reedrouxmusicisgay", "secure": False},
    #         {"uri": "wss://lava1.horizxon.tech:443", "password": "horizxon.tech", "secure": True},
    #         {"uri": "wss://lava2.horizxon.tech:443", "password": "horizxon.tech", "secure": True},
    #     ]
    #
    #     # SpotifyClient'ı bir kere oluştur
    #     sc = spotify.SpotifyClient(
    #         client_id='0c7f24e228844860a8a920d2e69ed11d',
    #         client_secret='be5c4415a8bc461a83f744822a803edf'
    #     )
    #
    #     # Her bir sunucuya bağlanmayı dene
    #     for server in lavalink_servers:
    #         try:
    #             node: wavelink.Node = wavelink.Node(uri=server["uri"], password=server["password"], secure=False)
    #             await wavelink.NodePool.connect(client=self, nodes=[node], spotify=sc)
    #             print(f"Connected to lavalink {node.uri}")
    #             break  # Eğer başarılı bir bağlantı kurulduysa döngüyü kır
    #         except Exception as e:
    #             print(f"Failed to connect to {server['uri']}. Error: {e}")


bot = Bot()


@bot.event
async def on_ready():
    bot.startTime = time.time()
    await bot.change_presence(status=discord.Status.online,
                              activity=discord.Activity(type=discord.ActivityType.watching,
                                                        name=f'{len(bot.guilds)} server'))
    await bot.tree.sync()
    count = len(bot.guilds)
    print(f'Logged on as {count}, your bot {bot.user}!')


@bot.tree.command(name="hello", description="Hello")
async def hello(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.send_message(f"Hello {user}")


@bot.event
async def on_message(message):
    # komutları mesaj olarak görmesin diye
    await bot.process_commands(message)


@bot.event
async def on_member_update(before, after):
    guild_id = 306081207278501890
    guild = bot.get_guild(guild_id)
    if after.guild == guild:
        if discord.utils.get(after.roles, name="Çavuş") and discord.utils.get(before.roles, name="Er"):
            await after.remove_roles(discord.utils.get(after.roles, name="Er"))

        if discord.utils.get(after.roles, name="Çavuş") is None and discord.utils.get(before.roles,
                                                                                      name="Çavuş") is not None:
            await after.add_roles(discord.utils.get(after.guild.roles, name="Er"))

    # if after.guild == guild:
    #     # Check if the member is a Çavuş, Subay, or Vekil
    #     is_cavus_or_higher = any(role.name in ["Çavuş", "Subay", "Vekil"] for role in after.roles)
    #
    #     # Check if the member has the Çekiliş role
    #     has_cekilis_role = discord.utils.get(after.roles, name="Çekiliş") is not None
    #
    #     if is_cavus_or_higher and not has_cekilis_role:
    #         # Add the "Çekiliş" role if they have Çavuş, Subay, or Vekil role but not the Çekiliş role
    #         role = discord.utils.get(after.guild.roles, name="Çekiliş")
    #         await after.add_roles(role)
    #     elif not is_cavus_or_higher and has_cekilis_role:
    #         # Remove the "Çekiliş" role if they don't have Çavuş, Subay, or Vekil role but have the Çekiliş role
    #         role = discord.utils.get(after.guild.roles, name="Çekiliş")
    #         await after.remove_roles(role)


@bot.command()
async def uptime(ctx):
    uptime = str(timedelta(seconds=int(round(time.time() - bot.startTime))))
    embed = discord.Embed(title="Uptime", description=uptime, color=ctx.author.color)
    await ctx.send(embed=embed)


@bot.command()
@commands.is_owner()
async def load(ctx, extension):
    await bot.load_extension(f'cogs.{extension}')
    await ctx.send(create_embed(description=f"Loaded cog!", color=discord.Color.green()))


@bot.command()
@commands.is_owner()
async def unload(ctx, extension):
    await bot.unload_extension(f'cogs.{extension}')
    await ctx.send(embed=create_embed(description=f"Unloaded cog!", color=discord.Color.green()))


@bot.command()
@commands.is_owner()
async def reload(ctx, extension):
    try:
        await bot.reload_extension(f'cogs.{extension}')
        await bot.tree.sync()
        await ctx.send(embed=create_embed(description=f"Reloaded cog!", color=discord.Color.green()))
    except Exception as e:
        await ctx.send(embed=create_embed(description=f"Error: {e}", color=discord.Color.red()))


async def cogs_load():
    for fn in os.listdir("./cogs"):
        if fn.endswith(".py"):
            await bot.load_extension(f"cogs.{fn[:-3]}")


async def main():
    await cogs_load()
    await bot.start(TOKEN)


asyncio.run(main())
