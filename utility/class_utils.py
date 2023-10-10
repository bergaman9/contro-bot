import discord

from .utils import async_initialize_mongodb, create_embed

class Paginator(discord.ui.View):
    def __init__(self, embed_list):
        super().__init__(timeout=120)
        self.embed_list = embed_list
        self.current_page = 0
        self.page_info.label = f"1/{len(self.embed_list)}"
        if len(self.embed_list) == 1:
            self.previous_button.disabled = True
            self.next_button.disabled = True

    async def send_initial_message(self, ctx):
        self.message = await ctx.send(embed=self.embed_list[self.current_page], view=self)

    def refresh_buttons(self):
        """Butonları yeniden ayarlar."""
        # Previous butonunu kontrol eder
        self.previous_button.disabled = self.current_page == 0

        # Next butonunu kontrol eder
        self.next_button.disabled = self.current_page == len(self.embed_list) - 1

        # Sayfa bilgisini günceller
        self.page_info.label = f"{self.current_page + 1}/{len(self.embed_list)}"

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id="previous_button")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        await self.show_page(interaction)

    @discord.ui.button(label="", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sayfa bilgisini gösterir."""
        pass

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="next_button")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.embed_list) - 1:
            self.current_page += 1
        await self.show_page(interaction)

    async def show_page(self, interaction: discord.Interaction):
        """Belirtilen sayfayı gösterir ve butonları günceller."""
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.embed_list[self.current_page], view=self)

    async def on_timeout(self):
        """Timeout bittiğinde bu fonksiyon çağrılır."""
        if hasattr(self, 'message') and self.message:
            await self.message.edit(view=None)


class DynamicButton(discord.ui.Button):
    def __init__(self, label, custom_id, **kwargs):
        super().__init__(label=label, custom_id=custom_id, **kwargs)

STYLE_MAPPING = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}

class DynamicView(discord.ui.View):
    def __init__(self, buttons_data):
        super().__init__()
        for index, data in enumerate(buttons_data, 0):  # index 0'dan başlar
            custom_id = f"button_{str(index).zfill(2)}"  # button_00, button_01, button_02, ...
            style_str = data.get("style", "primary")  # Varsayılan stil olarak "primary" kullanıldı.
            style = STYLE_MAPPING.get(style_str,
                                      discord.ButtonStyle.primary)  # Eğer stil bulunamazsa yine varsayılan olarak "primary" kullanılır.
            self.add_item(DynamicButton(label=data["label"], custom_id=custom_id, style=style, emoji=data.get("emoji", None), row=data.get("row", None)))


class LinkButton(discord.ui.Button):
    def __init__(self, label, url, **kwargs):
        super().__init__(label=label, url=url, **kwargs)


class ReportModal(discord.ui.Modal, title='Şikayet Et'):
    def __init__(self, message):
        super().__init__(timeout=None, custom_id="report_modal")
        self.message = message
        self.add_item(discord.ui.TextInput(label='Şikayetin nedir?', custom_id="report_field",
                                           placeholder="Şikayetinizi buraya yazın."))

    async def get_report_channel_id(self):
        mongo_db = await async_initialize_mongodb()
        settings = await mongo_db["settings"].find_one({})
        return settings.get("report_channel_id")

    async def on_submit(self, interaction) -> None:
        try:
            await interaction.response.defer()
            report_field_value = interaction.data["components"][0]["components"][0]["value"]
            print(report_field_value)
            report_channel_id = await self.get_report_channel_id()
            print(report_channel_id)
            if report_channel_id:
                report_channel = discord.utils.get(interaction.guild, id=report_channel_id)
                print("report_channel", report_channel)
                if not report_channel:
                    await interaction.followup.send("Şikayet kanalı bulunamadı.", ephemeral=True)
                    return
            else:
                report_channel = interaction.channel
            print(report_channel)


            description = f"**Şikayet:** {report_field_value} \n**Şikayet Edilen Mesaj:** [Link]({self.message.jump_url}) \n**Şikayet Eden:** {interaction.user.mention})"
            embed = discord.Embed(description=description, color=discord.Color.red())
            embed.set_author(name=f"{interaction.user.name} Şikayeti", icon_url=interaction.user.avatar.url)
            embed.set_thumbnail(url=interaction.user.avatar.url)
            embed.set_footer(text=f"ID: {interaction.user.id}")
            await report_channel.send(embed=embed, view=discord.ui.View().add_item(
                LinkButton(label="Mesaja Git", url=self.message.jump_url)))
            await interaction.followup.send(embed=create_embed("Şikayetiniz alındı.", discord.Color.green()), ephemeral=True)
        except Exception as e:
            print("An error occurred while reporting: ", e)