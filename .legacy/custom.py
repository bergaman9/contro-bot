import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List

from core.db import initialize_mongodb
from core.discord_helpers import create_embed, check_if_ctx_or_interaction

class RegisterButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Kayıt Ol", style=discord.ButtonStyle.primary, custom_id="rgs_btn"))

class RegisterModal(discord.ui.Modal, title='Register'):
    name = discord.ui.TextInput(label="Name", placeholder="Enter your name", required=True)
    username = discord.ui.TextInput(label="Username", placeholder="Enter your username", required=True)

class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    @commands.hybrid_command(name="rgm", description="Sends a registration message with a button for users to register.")
    @app_commands.describe()
    async def register_message(self, ctx):
        """Sends a registration message with a button that allows users to open a registration form."""
        try:
            embed = discord.Embed(title="**KAYIT OL**", description="Kayıt olmak için aşağıdaki butonu kullanabilirsiniz.", color=0x8A865D)
            await ctx.channel.send(embed=embed, view=RegisterButton())
        except Exception as e:
            await ctx.send(f"Bir hata oluştu: {e}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction):

        if interaction.data.get("custom_id") == "rgs_modal":
            try:
                name = interaction.data['components'][0]['components'][0]['value']
                username = interaction.data['components'][1]['components'][0]['value']
                member = interaction.guild.get_member(interaction.user.id)
                await member.edit(nick=f"{name.capitalize()} / {username}")
                await interaction.response.send_message(f"Başarıyla kayıt oldunuz, {name.capitalize()} / {username}!", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Bir hata oluştu: {e}", ephemeral=True)


        if interaction.data.get("custom_id") == "rgs_btn":
            try:
                await interaction.response.send_modal(RegisterModal())
            except Exception as e:
                await interaction.response.send_message(f"Bir hata oluştu: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Custom(bot))