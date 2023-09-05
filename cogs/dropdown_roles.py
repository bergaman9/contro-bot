import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from utils import create_embed, initialize_mongodb

class Dropdown(discord.ui.Select):
    def __init__(self, roles, emojis, descriptions, min_val: int, max_val: int, placeholder: str = 'Bir rol seçin.'):
        options = []
        descriptions = list(descriptions.split(',')) if descriptions else [None] * len(roles)
        emojis = emojis if emojis else [None] * len(roles)
        for role, emoji, description in zip(roles, emojis, descriptions):
            print(role.name, emoji, description, type(description))
            options.append(discord.SelectOption(label=role.name, value=role.id, emoji=emoji, description=description))
        self.callback_options = options
        super().__init__(placeholder=placeholder, min_values=min_val, max_values=max_val, options=options)


class DropdownView(discord.ui.View):
    def __init__(self, roles, emojis, descriptions, min_val: int, max_val: int, placeholder: str = 'Bir rol seçin.'):
        super().__init__()
        self.add_item(Dropdown(roles, emojis, descriptions, min_val, max_val, placeholder))

class DropdownRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongodb = initialize_mongodb()

    @commands.hybrid_command(name="dropdown_roles", description="Give roles with dropdown.")
    @app_commands.describe(roles="The roles to add to the dropdown.")
    @commands.has_permissions(manage_guild=True)
    async def dropdown_roles(self, ctx: commands.Context, roles: commands.Greedy[discord.Role], emojis: commands.Greedy[discord.Emoji] = None, descriptions: str = None, description: str = "Lütfen aşağıdaki açılır menüden bir rol seçin.", min_val: int = 0, max_val: int = 1, color: str = "eb45a0", placeholder: str = 'Bir rol seçin.'):
        await ctx.send(embed=create_embed(description="Dropdown roller oluşturuldu.", color=discord.Color.pink()), ephemeral=True)
        message = await ctx.channel.send(embed=create_embed(description=description, color=int(color, 16)), view=DropdownView(roles, emojis, descriptions, min_val, max_val, placeholder))
        self.mongodb["dropdown_roles"].insert_one({"_id": message.id, "guild_id": ctx.guild.id, "values": [str(r.id) for r in roles]})


    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        if interaction.message.id in [message["_id"] for message in self.mongodb["dropdown_roles"].find()]:
            member = interaction.user

            dropdown_values = self.mongodb["dropdown_roles"].find_one({"_id": interaction.message.id})["values"]

            roles_to_remove = [r for r in member.roles if r.id in [int(value) for value in dropdown_values if value != "none"]]

            response_message = ""

            if len(roles_to_remove) > 0:
                await member.remove_roles(*roles_to_remove)
                removed_roles_mentions = [role.mention for role in roles_to_remove]
                if len(removed_roles_mentions) == 1:
                    response_message += f'{" ".join(removed_roles_mentions)} rolü {member.mention} üyesinden alındı.\n'
                else:
                    response_message += f'{" ".join(removed_roles_mentions)} rolleri {member.mention} üyesinden alındı.\n'

            for value in interaction.data["values"]:
                if value != "none":
                    role = discord.utils.get(interaction.guild.roles, id=int(value))
                    await member.add_roles(role)
                    response_message += f'{role.mention} rolü {member.mention} üyesine verildi.\n'

            await interaction.response.send_message(embed=create_embed(description=response_message, color=discord.Color.green()), ephemeral=True)


async def setup(bot):
    await bot.add_cog(DropdownRoles(bot))