import discord
from discord.ext import commands
from discord.ui import Button, View

class HelpView(View):
    def __init__(self, embed_list):
        super().__init__(timeout=120)
        self.embed_list = embed_list
        self.current_page = 0
        self.page_info.label = f"1/{len(self.embed_list)}"  # Sayfa bilgisini başlangıçta ayarla
        self.message = None

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

    @discord.ui.button(label="Önceki", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
        await self.show_page(interaction)

    @discord.ui.button(label=f"1/4", style=discord.ButtonStyle.secondary, disabled=True)  # Başlangıç değeri 1/4 olarak ayarlandı
    async def page_info(self, interaction: discord.Interaction, button: Button):
        pass  # Bu buton sadece bilgi göstermek için var. Herhangi bir işlevi yok.

    @discord.ui.button(label="Sonraki", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < len(self.embed_list) - 1:
            self.current_page += 1
        await self.show_page(interaction)

    @discord.ui.button(label="Çıkış", style=discord.ButtonStyle.danger)
    async def exit_button(self, interaction: discord.Interaction, button: Button):
        await interaction.message.delete()

    async def show_page(self, interaction: discord.Interaction):
        """Belirtilen sayfayı gösterir ve butonları günceller."""
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.embed_list[self.current_page], view=self)

    async def on_timeout(self):
        """Timeout bittiğinde bu fonksiyon çağrılır."""
        if self.message:
            await self.message.edit(view=None)

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    COG_TITLES = {
        "ByeBye": "Bye Bye",
        "TemporaryChannels": "Geçici Kanal",
        "DropdownRoles": "Açılır Rol",
        "Fun": "Eğlence",
        "GameStats": "Oyun İstatistik",
        "Giveaway": "Çekiliş",
        "Invites": "Davet",
        "Moderation": "Moderasyon",

    }

    EXCLUDED_COGS = [
        "Owner",
        "Help",
    ]

    @commands.hybrid_command(name="help", description="Komutlar hakkında bilgi alın.")
    async def help(self, ctx, command: str = None):
        def format_cog_title(cog_name):
            # Özel başlık varsa onu döndür, yoksa cog ismini başlık haline getir
            return self.COG_TITLES.get(cog_name, cog_name.replace("_", " ").title())


        if not command:
            embed_list = []

            # Cogları al
            cogs = {cog_name: cog_obj for cog_name, cog_obj in self.bot.cogs.items() if cog_name not in self.EXCLUDED_COGS}

            for cog_name, cog_obj in cogs.items():
                formatted_title = format_cog_title(cog_name)
                embed = discord.Embed(title=f"{formatted_title} Komutları",
                                      description=f"{formatted_title} dosyasında bulunan komutlar:",
                                      color=discord.Color.pink())

                # Cog içindeki komutları al, ancak eşsiz komutları almak için set kullanın
                unique_commands = list({cmd.qualified_name: cmd for cmd in self.bot.all_commands.values() if
                                        cmd.cog_name == cog_name}.values())
                commands_in_cog = [command for command in unique_commands if command.parent is None]

                for cmd_obj in commands_in_cog:
                    embed.add_field(name=f"/{cmd_obj.name}", value=cmd_obj.description or "Açıklama yok.", inline=False)

                    # Eğer embed alan sayısı 25'e ulaşırsa (Discord sınırlaması) yeni bir embed oluştur
                    if len(embed.fields) == 25:
                        embed_list.append(embed)
                        embed = discord.Embed(title=f"{formatted_title} Komutları (devam)",
                                              description=f"{formatted_title} Cog'unda bulunan komutlar:",
                                              color=discord.Color.pink())

                # Kalan son komutları da ekleyelim
                if len(embed.fields) > 0:
                    embed_list.append(embed)

            view = HelpView(embed_list)
            await view.send_initial_message(ctx)


        else:
            # Belirli bir komut için yardım almak istiyorsa
            cmd_obj = self.bot.all_commands.get(command.lower())
            if cmd_obj:
                embed = discord.Embed(title=f"/{command}", description=cmd_obj.description or "Açıklama yok.",
                                      color=discord.Color.pink())

                # Komutun takma adları varsa ekleyin
                if cmd_obj.aliases:
                    aliases = ', '.join([f"`{alias}`" for alias in cmd_obj.aliases])
                    embed.add_field(name="Aliases", value=aliases, inline=False)

                await ctx.send(embed=embed)

            else:
                await ctx.send(f"'{command}' adında bir komut bulunamadı.")


async def setup(bot):
    await bot.add_cog(Help(bot))
