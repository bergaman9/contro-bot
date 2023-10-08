import io
import re
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utility.class_utils import DynamicView
from utility.db_utils import fetch_buttons_from_db, fetch_fields_from_db, fetch_application_fields_from_db, fetch_suggest_fields_from_db, insert_buttons_into_db, parse_interaction_data, fetch_fields_by_data_source, fetch_fields_from_db, fetch_buttons_for_guild
from utility.utils import create_embed, initialize_mongodb, hex_to_int


TEXT_STYLE_MAPPING = {
    "short": discord.TextStyle.short,
    "paragraph": discord.TextStyle.paragraph
}


class TicketModal(discord.ui.Modal):
    def __init__(self, data_source: str, title: str, guild_id: str):
        super().__init__(title=title, custom_id="ticket_modal")
        self.data_source = data_source
        self.guild_id = guild_id
        self.initialize_fields()

    def initialize_fields(self):
        try:
            data_list = fetch_fields_by_data_source(self.data_source, self.guild_id)

            if not data_list:
                raise ValueError("No data found")

            for index, data in enumerate(data_list):
                style_str = data.get('style', 'short')  # Varsayılan olarak 'short' kullanıldı.
                text_style = TEXT_STYLE_MAPPING.get(style_str,
                                                    discord.TextStyle.short)  # Eğer stil bulunamazsa varsayılan olarak 'short' kullanılır.

                field = discord.ui.TextInput(
                    label=data['label'],
                    placeholder=data['placeholder'],
                    custom_id=f"field_{index:02}",
                    max_length=data.get('max_length', None),
                    style=text_style
                )

                setattr(self, f"field_{index:02}", field)
                dynamic_field = getattr(self, f"field_{index:02}")
                self.add_item(dynamic_field)

        except:
            self.field_01 = discord.ui.TextInput(label='Destek almak istediğiniz konu nedir?',
                                                 placeholder="Yanıtınızı giriniz.", custom_id="field_01")
            self.add_item(self.field_01)


class TicketCloseButton(discord.ui.Button):
    def __init__(self, **kwargs):
        self.mongo_db = initialize_mongodb()
        super().__init__(style=discord.ButtonStyle.green, label="Kapat", emoji="<:lock:1147769998866133022>",
                         custom_id="close_ticket", **kwargs)

    async def close_ticket(self, interaction: discord.Interaction):
        support_roles_data = self.mongo_db['settings'].find_one({"guild_id": interaction.guild.id})
        user_has_permission = False

        if support_roles_data and 'support_roles' in support_roles_data:
            support_roles = support_roles_data['support_roles']

            for role_id in support_roles:
                role = discord.utils.get(interaction.guild.roles, id=role_id)
                if role and role in interaction.user.roles:
                    user_has_permission = True
                    break

        if not user_has_permission:
            default_support_role = discord.utils.get(interaction.guild.roles, name='Destek')
            if default_support_role and default_support_role in interaction.user.roles:
                user_has_permission = True

        if user_has_permission:
            channel = interaction.channel
            channel_id = channel.id

            record = self.mongo_db["logger"].find_one({"guild_id": interaction.guild.id})

            if not record:
                print("Veritabanından kayıt bulunamadı!")
                return

            logs_channel_id = record.get("channel_id")
            print(f"Logs Channel ID: {logs_channel_id}")

            logs_channel = interaction.guild.get_channel(logs_channel_id)

            if not logs_channel:
                print(f"{logs_channel_id} ID'sine sahip bir kanal bulunamadı!")
                return

            print(logs_channel)

            closing_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

            transcript = ""
            async for message in channel.history(limit=100):  # Adjust limit as needed
                transcript += f"{message.author}: {message.content}\n"

            transcript_file = discord.File(io.StringIO(transcript),
                                           filename=f"transcript{channel.name}-{closing_time}.txt")

            if logs_channel:
                embed = discord.Embed(title="Ticket Silindi",
                                      description=f"Ticket kanalı {interaction.user.mention} tarafından silindi.",
                                      color=discord.Color.red())
                await logs_channel.send(embed=embed, file=transcript_file)

            self.mongo_db["tickets"].delete_one({"_id": channel_id})

            await interaction.channel.delete()
            return
        else:
            await interaction.response.send_message(
                embed=create_embed(description="Bu işlemi gerçekleştirmek için yetkiniz yok.",
                                   color=discord.Color.red()), ephemeral=True)


class TicketCloseButtonView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketCloseButton())


class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    @commands.hybrid_command(name="send_ticket_message", description="Sends a ticket message.")
    async def send_ticket_message(self, ctx, title="DESTEK",
                                  description="Yetkililerle iletişime geçmek için aşağıdaki butona basarak ticket açabilirsiniz.",
                                  color="ff1a60"):
        embed = discord.Embed(title=title, description=description, color=hex_to_int(color))
        buttons_data = fetch_buttons_for_guild(ctx.guild.id)
        if not buttons_data:
            await ctx.send(embed=create_embed(description="Bu sunucu için ticket butonu bulunamadı.",
                                              color=discord.Color.red()), ephemeral=True)
            return
        view = DynamicView(buttons_data)
        await ctx.channel.send(embed=embed, view=view)
        await ctx.send(embed=create_embed(description="Ticket mesajınız oluşturulmuştur.",
                                          color=discord.Color.green()), ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id") == "close_ticket":  # custom_id kontrolü
            await TicketCloseButton().close_ticket(interaction)

        if interaction.data.get("custom_id") == "ticket_modal":
            try:
                user_ticket_count = self.mongo_db["tickets"].count_documents(
                    {"user_id": interaction.user.id, "guild_id": interaction.guild.id})

                if user_ticket_count >= 1:
                    query = self.mongo_db["tickets"].find_one(
                        {"user_id": interaction.user.id, "guild_id": interaction.guild.id})
                    await interaction.response.send_message(
                        embed=create_embed(description=f"Zaten bir ticketiniz var: {query['channel']} ",
                                           color=discord.Color.red()), ephemeral=True)
                    return

                member = interaction.user
                guild = interaction.guild

                description = await parse_interaction_data(interaction, "field_00", "field_01", "field_02", "field_03", "field_04")

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True),
                    member: discord.PermissionOverwrite(read_messages=True)
                }

                # Veritabanından support rollerini çekin
                support_roles_data = self.mongo_db['settings'].find_one({"guild_id": guild.id})
                if support_roles_data and 'support_roles' in support_roles_data:
                    pass
                else:
                    # Fallback: Eğer veritabanında bu bilgi yoksa varsayılan olarak "Destek" adında bir rol ara, yoksa oluştur.
                    support_role = discord.utils.get(guild.roles, name='Destek')
                    if not support_role:
                        support_role = await guild.create_role(name='Destek', color=discord.Color.green())
                    overwrites[support_role] = discord.PermissionOverwrite(read_messages=True)

                category_id = self.mongo_db["settings"].find_one({"guild_id": guild.id})["ticket_category_channel"]
                category = guild.get_channel(category_id)
                if category is None:
                    category = await guild.create_category(name="DESTEK")

                channel_name = f"{member.name}-ticket"  # You can customize the channel name here
                channel = await guild.create_text_channel(name=channel_name, category=category,
                                                          overwrites=overwrites)

                # Create and send an embed message to the new channel
                await channel.send(
                    f"Merhaba {member.mention}! \nYetkililer en kısa sürede size yardımcı olacaktır.")
                embed = discord.Embed(title="Üyenin Form Yanıtı", description=description,
                                      color=discord.Color.green())
                await channel.send(embed=embed, view=TicketCloseButtonView())

                # Create and send an embed to the logs channel
                logs_channel_id = self.mongo_db["logger"].find_one({"guild_id": guild.id})["channel_id"]
                logs_channel = self.bot.get_channel(logs_channel_id)
                if logs_channel:
                    log_embed = discord.Embed(
                        title="Yeni Ticket Oluşturuldu",
                        description=f"{interaction.user.mention} tarafından ticket oluşturulmuştur.",
                        color=discord.Color.blue()
                    )
                    log_embed.add_field(name="Ticket Kanalı", value=channel.mention, inline=True)
                    log_embed.add_field(name="Üyenin Form Yanıtı", value=description, inline=True)
                    await logs_channel.send(embed=log_embed)

                # Here, you can insert the new ticket info into your database if you want
                self.mongo_db["tickets"].insert_one({
                    "_id": channel.id,
                    "guild_id": guild.id,
                    "user_id": member.id,
                    "text": description,
                    "channel": channel.mention
                })

                await interaction.response.send_message(
                    embed=create_embed(description=f"Ticket başarılı bir şekilde oluşturuldu: {channel.mention}",
                                       color=discord.Color.green()),
                    ephemeral=True
                )
            except Exception as e:
                print(f"An error occurred: {e}")

        try:
            custom_id = interaction.data.get("custom_id")

            match = re.match(r"button_(\d+)", custom_id)
            if not match:
                print(f"Invalid custom_id format: {custom_id}")
                return

            index = int(match.group(1))
            buttons = fetch_buttons_for_guild(interaction.guild.id)

            if 0 <= index < len(buttons):
                button_data = buttons[index]
                data_source = button_data.get("data_source", "default")
                await interaction.response.send_modal(
                    TicketModal(data_source=data_source, title=button_data["label"], guild_id=str(interaction.guild.id)))
            else:
                print(f"No button matched for custom_id: {custom_id}")
        except Exception as e:
            print(f"An error occurred: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        # Eğer silinen kanal bir ticket kanalıysa, veritabanından da sil
        ticket_data = self.mongo_db["tickets"].find_one({"_id": channel.id})
        if ticket_data:
            self.mongo_db["tickets"].delete_one({"_id": channel.id})

    @commands.hybrid_command(name="set_ticket_category", description="Sets the support category channel.")
    @app_commands.describe(channel="Kanal seçin.")
    @commands.has_permissions(manage_guild=True)
    async def set_ticket_category(self, ctx, channel: discord.CategoryChannel):
        await ctx.defer()
        self.mongo_db['settings'].update_one(
            {"guild_id": ctx.guild.id},
            {
                "$set": {
                    "ticket_category_channel": channel.id
                }
            },
            upsert=True
        )
        await ctx.send(
            embed=create_embed(f"Ticket kategorisi {channel.mention} olarak ayarlandı.", discord.Colour.green()))

    @commands.hybrid_command(name="set_ticket_roles", description="Sets the support roles.")
    @app_commands.describe(roles="The roles to add to the dropdown.")
    @commands.has_permissions(manage_guild=True)
    async def set_ticket_roles(self, ctx: commands.Context, roles: commands.Greedy[discord.Role]):
        await ctx.defer()
        self.mongo_db['settings'].update_one(
            {"guild_id": ctx.guild.id},
            {
                "$set": {
                    "support_roles": [role.id for role in roles]
                }
            },
            upsert=True
        )
        await ctx.send(
            embed=create_embed(f"Ticket rolleri {', '.join([role.mention for role in roles])} olarak ayarlandı.",
                               discord.Colour.green()))


async def setup(bot):
    await bot.add_cog(Ticket(bot))
