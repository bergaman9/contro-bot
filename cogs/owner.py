import discord
from discord.ext import commands
import math
from utils import initialize_mongodb

class GuildsView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=120)  # 2 minutes timeout
        self.embeds = embeds
        self.current_page = 0
        self.max_pages = len(embeds) - 1  # Sayfa sayısını doğru bir şekilde ayarladık
        self.page_info.label = f"1/{len(self.embeds)}"  # Sayfa bilgisini başlangıçta ayarla
        self.message = None

    async def send_initial_message(self, ctx):
        self.message = await ctx.send(embed=self.embeds[self.current_page], view=self)

    def refresh_buttons(self):
        """Butonları yeniden ayarlar."""
        # Previous butonunu kontrol eder
        self.previous_button.disabled = self.current_page == 0

        # Next butonunu kontrol eder
        self.next_button.disabled = self.current_page == len(self.embeds) - 1

        # Sayfa bilgisini günceller
        self.page_info.label = f"{self.current_page + 1}/{len(self.embeds)}"

    @discord.ui.button(label="Önceki", style=discord.ButtonStyle.primary, custom_id="previous_button")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.show_page(interaction)

    @discord.ui.button(label=f"1/4", style=discord.ButtonStyle.secondary,
                       disabled=True)  # Başlangıç değeri 1/4 olarak ayarlandı
    async def page_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass  # Bu buton sadece bilgi göstermek için var. Herhangi bir işlevi yok.

    @discord.ui.button(label="Sonraki", style=discord.ButtonStyle.primary, custom_id="next_button")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.current_page < self.max_pages:
                self.current_page += 1
                await self.show_page(interaction)
        except Exception as e:
            print(e)

    async def show_page(self, interaction: discord.Interaction):
        """Belirtilen sayfayı gösterir ve butonları günceller."""
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    async def on_timeout(self):
        """Timeout bittiğinde bu fonksiyon çağrılır."""
        if self.message:
            await self.message.edit(view=None)

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = initialize_mongodb()

    @commands.hybrid_command(name="contro_guilds", description="Shows guilds.")
    @commands.is_owner()
    async def contro_guilds(self, ctx):
        try:
            await ctx.defer()
            guilds_sorted = sorted(self.bot.guilds, key=lambda g: g.created_at,
                                   reverse=True)  # Sunucuları tarihe göre sırala

            each_page = 10
            pages = math.ceil(len(guilds_sorted) / each_page)
            embeds = []

            for page in range(pages):
                embed = discord.Embed(title=f"Server List ({len(guilds_sorted)})", color=discord.Color.pink())
                start_idx = page * each_page
                end_idx = start_idx + each_page

                for guild in guilds_sorted[start_idx:end_idx]:
                    try:
                        invites = await guild.invites()  # invites'ı await ile al
                        first_invite = invites[0].url if invites else 'No invite link'  # Eğer varsa ilk daveti al
                    except:
                        first_invite = 'No invite link'
                    member = await guild.fetch_member(783064615012663326)
                    embed.add_field(
                        name=f"{guild.name} ({guild.member_count})",
                        value=f"*Owner:* <@{guild.owner_id}> \n*Join Date:* {member.joined_at.strftime('%m/%d/%Y, %H:%M:%S')} \n*Invite:* {first_invite}",
                        inline=False
                    )
                embed.set_footer(text=f"Page: {page + 1}/{pages}")
                embeds.append(embed)

            view = GuildsView(embeds)
            await view.send_initial_message(ctx)
        except Exception as e:
            print(e)


async def setup(bot):
    await bot.add_cog(Owner(bot))