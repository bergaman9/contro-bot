import discord
from discord.ext import commands

from utils import create_embed, initialize_mongodb

class Report(discord.ui.Modal, title='Satış Yap'):
    name = discord.ui.TextInput(label='İsim')
    age = discord.ui.TextInput(label='Yaş', style=discord.TextStyle.short, max_length=2)
    username = discord.ui.TextInput(label='Kullanıcı Adı', required=False)

class ReportButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    @discord.ui.button(label="Kayıt Ol", style=discord.ButtonStyle.green)
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(Report())

class Modals(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = int(member.guild.id)
        guild_config = self.mongo_db['register'].find_one({"guild_id": guild_id})
        if guild_config is None:
            return
        modal_embed = guild_config["modal_embed"]
        channel_id = guild_config["channel_id"]
        channel = self.bot.get_channel(channel_id)
        if modal_embed:
            message = await channel.send(embed=create_embed(description=f"{member.mention} kayıt olmak için aşağıdaki butona basabilirsin.", color=discord.Color.green()), view=ReportButton())
            self.mongo_db["modals"].insert_one({"_id": message.id, "guild_id": guild_id, "user_id": member.id})

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        if interaction.type == discord.InteractionType.modal_submit:

            member = interaction.user

            name = interaction.data["components"][0]["components"][0]["value"]
            age = interaction.data["components"][1]["components"][0]["value"]
            username = interaction.data["components"][2]["components"][0]["value"]

            # Do necessary checks (e.g., age is a number) and then edit the member's nickname
            if age.isdigit():
                try:
                    await self.register_by_age(interaction, member, age)
                    record = self.mongo_db['register'].find_one({"guild_id": interaction.guild.id})
                    if record is None:
                        return
                    nickname_edit = record.get("nickname_edit", True)
                    username_edit = record.get("username_edit", True)
                    if nickname_edit and username_edit:
                        nickname = f"{name.title()} | {age} | {username}" if username else f"{name.title()} | {age}"
                        try:
                            await member.edit(nick=nickname)
                        except discord.Forbidden:
                            await interaction.response.send_message(embed=create_embed("I don't have permission to change nicknames.",
                                                              discord.Colour.red()))
                        except discord.HTTPException:
                            await interaction.response.send_message(embed=create_embed("Failed to change the nickname.", discord.Colour.red()))
                    elif nickname_edit:
                        nickname = f"{name.title()} | {age}"
                        try:
                            await member.edit(nick=nickname)
                        except discord.Forbidden:
                            await interaction.response.send_message(embed=create_embed("I don't have permission to change nicknames.",
                                                              discord.Colour.red()))
                        except discord.HTTPException:
                            await interaction.response.send_message(embed=create_embed("Failed to change the nickname.", discord.Colour.red()))
                    elif username_edit and username:
                        try:
                            await member.edit(username=username)
                        except discord.HTTPException:
                            await interaction.response.send_message(embed=create_embed("Failed to change the username.", discord.Colour.red()))

                    # await member.edit(nick=f"{name.title()} | {age}")
                    # await interaction.response.send_message(
                    #     embed=create_embed(description=f"Kayıt başarılı, {member.mention}",
                    #                        color=discord.Color.green()), ephemeral=True)
                    self.mongo_db["modals"].delete_one({"_id": interaction.message.id})
                except:
                    await interaction.response.send_message(
                        embed=create_embed(description=f"Kayıt başarısız, {member.mention}", color=discord.Color.red()),
                        ephemeral=True)


            else:
                await interaction.response.send_message(
                    embed=create_embed(description="Yaşınızı sayı olarak giriniz.", color=discord.Color.red()),
                    ephemeral=True)

        if interaction.message.id in [message["_id"] for message in self.mongo_db["modals"].find()]:
            await interaction.response.send_modal(Report())

    async def register_by_age(self, interaction, member, age):
        record = self.mongo_db['register'].find_one({"guild_id": interaction.guild.id})
        if record is None:
            return

        age_role = record.get("age_roles", True)
        if age_role:
            registration_channel = self.bot.get_channel(record["channel_id"])

            role_18_plus = discord.utils.get(interaction.guild.roles, name="18+")
            role_18_minus = discord.utils.get(interaction.guild.roles, name="18-")
            role_unregistered = discord.utils.get(interaction.guild.roles, name="Kayıtsız Üye")

            embed2 = create_embed(
                f"Burası kayıt kanalı değil! {registration_channel.mention} kanalını kullanmalısınız.",
                discord.Colour.red())
            embed3 = create_embed("Kayıt tamamlanamadı!", discord.Colour.red())

            if interaction.channel.id == record["channel_id"]:
                if 18 <= int(age) <= 99:
                    try:
                        await member.add_roles(role_18_plus)
                        await member.remove_roles(role_18_minus, role_unregistered)
                        await interaction.response.send_message(embed=create_embed(
                            f"{member.mention} için {role_18_plus.mention} rolü verilerek kaydı tamamlandı!",
                            discord.Colour.blurple()))
                    except:
                        await interaction.response.send_message(embed=embed3)
                elif 0 <= int(age) <= 17:
                    try:
                        await member.add_roles(role_18_minus)
                        await member.remove_roles(role_18_plus, role_unregistered)
                        await interaction.response.send_message(embed=create_embed(
                            f"{member.mention} için {role_18_minus.mention} rolü verilerek kaydı tamamlandı!",
                            discord.Colour.blurple()))
                    except:
                        await interaction.response.send_message(embed=embed3)
            else:
                await interaction.response.send_message(embed=embed2)

        # Give roles from given_roles list
        given_roles = record.get("given_roles", [])
        for role_mention in given_roles:
            role_id = int(role_mention.strip("<@&>"))
            role_to_give = interaction.guild.get_role(role_id)
            if role_to_give:
                try:
                    await member.add_roles(role_to_give)
                    await interaction.response.send_message(
                        embed=create_embed(f"{role_to_give.mention} role has been given to {member.mention}.",
                                           discord.Colour.green()))
                except discord.Forbidden:
                    await interaction.response.send_message(
                        embed=create_embed(f"I don't have permission to give {role_to_give.mention} role.",
                                           discord.Colour.red()))

        # Take roles from taken_roles list
        taken_roles = record.get("taken_roles", [])
        for role_mention in taken_roles:
            role_id = int(role_mention.strip("<@&>"))
            role_to_take = interaction.guild.get_role(role_id)
            if role_to_take in member.roles:
                try:
                    await member.remove_roles(role_to_take)
                    await interaction.response.send_message(
                        embed=create_embed(f"{role_to_take.mention} role has been taken from {member.mention}.",
                                           discord.Colour.green()))
                except discord.Forbidden:
                    await interaction.response.send_message(
                        embed=create_embed(f"I don't have permission to take {role_to_take.mention} role.",
                                           discord.Colour.red()))


async def setup(bot):
    await bot.add_cog(Modals(bot))