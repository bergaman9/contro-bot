import discord
from discord import app_commands
from discord.ext import commands

from utils import create_embed, initialize_mongodb, find_guild_in_register_collection, check_if_ctx_or_interaction

class RegisterModal(discord.ui.Modal, title='Kayıt Ol'):
    def __init__(self, include_username):
        super().__init__(timeout=None)
        self.add_item(discord.ui.TextInput(label='İsim'))
        self.add_item(discord.ui.TextInput(label='Yaş', style=discord.TextStyle.short, max_length=2))
        if include_username:
            self.add_item(discord.ui.TextInput(label='Kullanıcı Adı', required=False))

class RegisterView(discord.ui.View):
    def __init__(self, include_username):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Kayıt Ol", style=discord.ButtonStyle.green, custom_id="register_button"))
        self.include_username = include_username

class Register(commands.Cog):
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
        include_username = guild_config.get("include_username")
        if modal_embed:
            if include_username:
                await channel.send(embed=create_embed(description=f"{member.mention} kayıt olmak için aşağıdaki butona basabilirsin.", color=discord.Color.green()), view=RegisterView(include_username=True))
            else:
                await channel.send(embed=create_embed(description=f"{member.mention} kayıt olmak için aşağıdaki butona basabilirsin.", color=discord.Color.green()), view=RegisterView(include_username=False))

    @commands.hybrid_command(name="kayıt", description="Kayıt olmak için kullanılır.", aliases=["register"])
    @app_commands.describe(name="İsminizi girin.", age="Yaşınızı girin.", username="Kullanıcı adınızı girin.")
    async def kayıt(self, ctx, name, age, username=None):
        await self.register_handler(ctx, ctx.author, name, age, username)

    @commands.hybrid_command(name="kayıt_setup", description="Kayıt kanalını ve rollerini ayarlar.")
    @app_commands.describe(channel="Kayıt kanalı ayarlayın.", description="Kayıt kanalı için açıklama girin.", nickname_edit="Nickname düzenlemeyi ayarlayın.", username_edit="Username düzenlemeyi ayarlayın.", age_roles="Yaş rollerini etiketleyerek seçin.", given_roles="Verilecek rolleri etiketleyerek seçin.", taken_roles="Alınacak rolleri etiketleyerek seçin.", modal_embed="Modal embed ayarlayın.")
    async def kayıt_setup(self, ctx, channel: discord.TextChannel, description=None, nickname_edit: bool = False,
                          username_edit: bool = False, age_roles: bool = True, given_roles: str = None,
                          taken_roles: str = None, modal_embed: bool = False):
        if ctx.message.author.guild_permissions.manage_guild:
            record = self.mongo_db['register'].find_one({"guild_id": ctx.guild.id})
            if record is None:
                # If the record doesn't exist, insert a new record with the given parameters
                self.mongo_db['register'].insert_one({
                    "guild_id": ctx.guild.id,
                    "channel_id": channel.id,
                    "nickname_edit": nickname_edit,
                    "username_edit": username_edit,
                    "age_roles": age_roles,
                    "modal_embed": modal_embed,
                    "description": description
                })
                await ctx.send(embed=create_embed(
                    f"Kayıt kanalı {channel.mention} olarak ayarlandı. \n**Düzenleme özellikleri:** \n*Nickname Edit:* {nickname_edit}, *Username Edit:* {username_edit}, *Age Roles:* {age_roles}",
                    discord.Colour.green()))
            else:
                # If the record already exists, update the existing record with the given parameters
                self.mongo_db['register'].update_one(
                    {"guild_id": ctx.guild.id},
                    {"$set": {
                        "channel_id": channel.id,
                        "nickname_edit": nickname_edit,
                        "username_edit": username_edit,
                        "age_roles": age_roles,
                        "modal_embed": modal_embed,
                        "description": description
                    }}
                )
                await ctx.send(embed=create_embed(
                    f"Kayıt kanalı {channel.mention} olarak güncellendi. \n**Düzenleme özellikleri:** \n*Nickname Edit:* {nickname_edit}, *Username Edit:* {username_edit}, *Age Roles:* {age_roles}",
                    discord.Colour.green()))

            # Create 18+, 18- and Unregistered roles if they don't exist
            if age_roles:
                roles_to_create = [("18+", discord.Colour(0x9bacc5)), ("18-", discord.Colour(0xcc7e36)),
                                   ("Kayıtsız Üye", discord.Colour(0x86b4a4))]

                for role_name, role_color in roles_to_create:
                    existing_role = discord.utils.get(ctx.guild.roles, name=role_name)
                    if existing_role is None:
                        await ctx.guild.create_role(name=role_name, colour=role_color)
                        await ctx.send(embed=create_embed(f"Rol '{role_name}' oluşturuldu.", discord.Colour.green()))
                    else:
                        await ctx.send(embed=create_embed(f"Rol '{role_name}' zaten var. Yeni bir rol oluşturulmadı.",
                                                          discord.Colour.orange()))

            # Process given_roles and taken_roles if provided
            if given_roles:
                given_roles = [role.strip() for role in given_roles.split(',')]
                self.mongo_db['register'].update_one({"guild_id": ctx.guild.id}, {"$set": {"given_roles": given_roles}})
                await ctx.send(
                    embed=create_embed(f"Roles to be given after registration: {', '.join(given_roles)}",
                                       discord.Colour.green()))

            if taken_roles:
                taken_roles = [role.strip() for role in taken_roles.split(',')]
                self.mongo_db['register'].update_one({"guild_id": ctx.guild.id}, {"$set": {"taken_roles": taken_roles}})
                await ctx.send(
                    embed=create_embed(f"Roles to be taken after registration: {', '.join(taken_roles)}",
                                       discord.Colour.green()))
        else:
            await ctx.send(embed=create_embed("Bunu yapmaya iznin yok.", discord.Colour.red()))

    @commands.hybrid_command(name="kayıt_channel_show", description="Shows the registration channel.")
    async def kayıt_channel_show(self, ctx):
        if ctx.message.author.guild_permissions.manage_guild:
            record = self.mongo_db['register'].find_one({"guild_id": ctx.guild.id})
            if record is not None:
                channel_id = record.get("channel_id")
                nickname_edit = record.get("nickname_edit", True)
                username_edit = record.get("username_edit", True)

                embed = discord.Embed(title="Kayıt Kanalı ve Ayarları", color=discord.Colour.blurple())
                embed.add_field(name="Kayıt Kanalı", value=f"<#{int(channel_id)}>", inline=False)
                embed.add_field(name="Nickname Düzenleme", value="Aktif" if nickname_edit else "Pasif", inline=False)
                embed.add_field(name="Username Düzenleme", value="Aktif" if username_edit else "Pasif", inline=False)

                await ctx.send(embed=embed)
            else:
                await ctx.send(embed=create_embed("Kayıt kanalı ayarlanmadı.", discord.Colour.red()))
        else:
            await ctx.send(embed=create_embed("Bunu yapmaya iznin yok.", discord.Colour.red()))

    @commands.hybrid_command(name="kayıt_channel_set", description="Sets the age role registration channel.")
    @app_commands.describe(channel="Kayıt kanalı etiketleyin.")
    async def kayıt_channel_set(self, ctx, channel: discord.TextChannel):
        if ctx.message.author.guild_permissions.manage_guild:
            record = self.mongo_db['register'].find_one({"guild_id": ctx.guild.id})
            if record is None:
                self.mongo_db['register'].insert_one({"guild_id": ctx.guild.id, "channel_id": channel.id})
            else:
                self.mongo_db['register'].update_one({"guild_id": ctx.guild.id}, {"$set": {"channel_id": channel.id}})
            await ctx.send(
                embed=create_embed(f"Kayıt kanalı {channel.mention} olarak ayarlandı.", discord.Colour.green()))
        else:
            await ctx.send(embed=create_embed("Bunu yapmaya iznin yok.", discord.Colour.red()))

    @commands.hybrid_command(name="kayıt_channel_remove", description="Removes the age role registration channel.")
    @app_commands.describe(channel="Kayıt kanalını etiketleyin. Bilmiyorsanız /kayıt_channel_show ile öğrenebilirsiniz.")
    async def kayıt_channel_remove(self, ctx, channel: discord.TextChannel):
        if ctx.message.author.guild_permissions.manage_guild:
            record = self.mongo_db['register'].find_one({"guild_id": ctx.guild.id})
            if record is None:
                await ctx.send(embed=create_embed("Kayıt kanalı ayarlanmadı.", discord.Colour.red()))
            else:
                self.mongo_db['register'].delete_one({"guild_id": ctx.guild.id})
                await ctx.send(embed=create_embed("Kayıt kanalı kaldırıldı.", discord.Colour.green()))
        else:
            await ctx.send(embed=create_embed("Bunu yapmaya iznin yok.", discord.Colour.red()))

    @commands.hybrid_command(name="kayıt_settings", description="Changes registration settings.")
    async def kayıt_settings(self, ctx, nickname: bool = None, username: bool = None, given_roles: str = None,
                             taken_roles: str = None, age_roles: bool = None, modal_embed: bool = None):
        if ctx.message.author.guild_permissions.manage_guild:
            record = self.mongo_db['register'].find_one({"guild_id": ctx.guild.id})
            if record is None:
                self.mongo_db['register'].insert_one(
                    {"guild_id": ctx.guild.id, "channel_id": ctx.channel.id, "nickname_edit": True,
                     "username_edit": True})
                await ctx.send(embed=create_embed("Kayıt kanalı ayarlanmadı. Önce kayıt kanalını ayarlayın.",
                                                  discord.Colour.red()))
                return

            if nickname is not None:
                self.mongo_db['register'].update_one({"guild_id": ctx.guild.id}, {"$set": {"nickname_edit": nickname}})
                await ctx.send(
                    embed=create_embed(f"Nickname edit feature is turned {'on' if nickname else 'off'}.",
                                       discord.Colour.green()))

            if username is not None:
                self.mongo_db['register'].update_one({"guild_id": ctx.guild.id}, {"$set": {"username_edit": username}})
                await ctx.send(
                    embed=create_embed(f"Username edit feature is turned {'on' if username else 'off'}.",
                                       discord.Colour.green()))

            if given_roles is not None:
                given_roles = [role.strip() for role in given_roles.split(',')]
                self.mongo_db['register'].update_one({"guild_id": ctx.guild.id}, {"$set": {"given_roles": given_roles}})
                await ctx.send(
                    embed=create_embed(f"Roles to be given after registration: {', '.join(given_roles)}",
                                       discord.Colour.green()))

            if taken_roles is not None:
                taken_roles = [role.strip() for role in taken_roles.split(',')]
                self.mongo_db['register'].update_one({"guild_id": ctx.guild.id}, {"$set": {"taken_roles": taken_roles}})
                await ctx.send(
                    embed=create_embed(f"Roles to be taken after registration: {', '.join(taken_roles)}",
                                       discord.Colour.green()))

            if age_roles is not None:
                self.mongo_db['register'].update_one({"guild_id": ctx.guild.id},
                                                     {"$set": {"age_roles": age_roles}})
                await ctx.send(
                    embed=create_embed(f"Age-based roles feature is turned {'on' if age_roles else 'off'}.",
                                       discord.Colour.green()))

            if modal_embed is not None:
                self.mongo_db['register'].update_one({"guild_id": ctx.guild.id},
                                                     {"$set": {"modal_embed": modal_embed}})
                await ctx.send(
                    embed=create_embed(f"Modal embed feature is turned {'on' if modal_embed else 'off'}.",
                                       discord.Colour.green()))

        else:
            await ctx.send(embed=create_embed("Bunu yapmaya iznin yok.", discord.Colour.red()))

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
                    await self.register_handler(interaction, member, name, age, username)
                except:
                    await interaction.response.send_message(embed=create_embed(description=f"Kayıt başarısız, {member.mention}", color=discord.Color.red()), ephemeral=True)
            else:
                await interaction.response.send_message(embed=create_embed(description="Yaşınızı sayı olarak giriniz.", color=discord.Color.red()), ephemeral=True)

        if interaction.data.get("custom_id") == "register_button":
            guild_config = self.mongo_db['register'].find_one({"guild_id": interaction.guild.id})
            include_username = guild_config.get("username_edit")
            if include_username:
                await interaction.response.send_modal(RegisterModal(include_username=True))
            else:
                await interaction.response.send_modal(RegisterModal(include_username=False))
    async def register_handler(self, ctx_or_interaction, member, name, age, username=None):
        guild, send, channel = await check_if_ctx_or_interaction(ctx_or_interaction)

        await self.register_by_age(ctx_or_interaction, member, age)

        record = find_guild_in_register_collection(guild.id)
        if record is None:
            return

        # Logs the form values to the logging channel
        logging_channel_id = self.mongo_db['logger'].find_one({"guild_id": guild.id})["channel_id"]
        logging_channel = self.bot.get_channel(logging_channel_id)
        if logging_channel:
            embed = discord.Embed(title="Üye kayıt oldu", description=f"{member.mention} kayıt oldu.",
                                  color=discord.Color.green())
            embed.add_field(name="Form Bilgisi", value=f"{name.title()} {age} {username}", inline=True)
            await logging_channel.send(embed=embed)

        nickname_edit = record.get("nickname_edit", True)
        username_edit = record.get("username_edit", True)
        if nickname_edit and username_edit:
            nickname = f"{name.title()} | {age} | {username}" if username else f"{name.title()} | {age}"
            try:
                await member.edit(nick=nickname)
            except discord.Forbidden:
                await send(embed=create_embed("I don't have permission to change nicknames.", discord.Colour.red()))
            except discord.HTTPException:
                await send(embed=create_embed("Failed to change the nickname.", discord.Colour.red()))
        elif nickname_edit:
            nickname = f"{name.title()} | {age}"
            try:
                await member.edit(nick=nickname)
            except discord.Forbidden:
                await send(embed=create_embed("I don't have permission to change nicknames.", discord.Colour.red()))
            except discord.HTTPException:
                await send(embed=create_embed("Failed to change the nickname.", discord.Colour.red()))
        elif username_edit and username:
            try:
                await member.edit(username=username)
            except discord.HTTPException:
                await send(embed=create_embed("Failed to change the username.", discord.Colour.red()))

        # Give roles from given_roles list
        given_roles = record.get("given_roles", [])
        if given_roles:
            for role_mention in given_roles:
                role_id = int(role_mention.strip("<@&>"))
                role_to_give = guild.get_role(role_id)
                if role_to_give:
                    try:
                        await member.add_roles(role_to_give)
                        await send(
                            embed=create_embed(f"{role_to_give.mention} role has been given to {member.mention}.",
                                               discord.Colour.green()))
                    except discord.Forbidden:
                        await send(
                            embed=create_embed(f"I don't have permission to give {role_to_give.mention} role.",
                                               discord.Colour.red()))

        taken_roles = record.get("taken_roles", [])
        if taken_roles:
            for role_mention in taken_roles:
                role_id = int(role_mention.strip("<@&>"))
                role_to_take = guild.get_role(role_id)
                if role_to_take in member.roles:
                    try:
                        await member.remove_roles(role_to_take)
                        await send(
                            embed=create_embed(f"{role_to_take.mention} role has been taken from {member.mention}.",
                                               discord.Colour.green()))
                    except discord.Forbidden:
                        await send(
                            embed=create_embed(f"I don't have permission to take {role_to_take.mention} role.",
                                               discord.Colour.red()))
    async def register_by_age(self, ctx_or_interaction, member, age):
        guild, send, channel = await check_if_ctx_or_interaction(ctx_or_interaction)

        record = find_guild_in_register_collection(guild.id)
        if record is None:
            return

        age_role = record.get("age_roles", True)
        if age_role:
            registration_channel = self.bot.get_channel(record["channel_id"])

            role_18_plus = discord.utils.get(guild.roles, name="18+")
            role_18_minus = discord.utils.get(guild.roles, name="18-")
            role_unregistered = discord.utils.get(guild.roles, name="Kayıtsız Üye")

            channel_error = create_embed(f"Burası kayıt kanalı değil! {registration_channel.mention} kanalını kullanmalısınız.", discord.Colour.red())
            register_error = create_embed("Kayıt tamamlanamadı!", discord.Colour.red())

            if channel.id == record["channel_id"]:
                if 18 <= int(age) <= 99:
                    try:
                        await member.add_roles(role_18_plus)
                        await member.remove_roles(role_18_minus, role_unregistered)
                        await send(embed=create_embed(
                            f"{member.mention} için {role_18_plus.mention} rolü verilerek kaydı tamamlandı!",
                            discord.Colour.blurple()))
                    except:
                        await send(embed=register_error)
                elif 0 <= int(age) <= 17:
                    try:
                        await member.add_roles(role_18_minus)
                        await member.remove_roles(role_18_plus, role_unregistered)
                        await send(embed=create_embed(
                            f"{member.mention} için {role_18_minus.mention} rolü verilerek kaydı tamamlandı!",
                            discord.Colour.blurple()))
                    except:
                        await send(embed=register_error)
            else:
                await send(embed=channel_error)


async def setup(bot):
    await bot.add_cog(Register(bot))