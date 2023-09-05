import discord
from discord.ext import commands
from discord import app_commands
from discord import ui

from utils import create_embed, initialize_mongodb
from messages import kurallar_text, destek_text, duyurular_text, komutlar_text, roller_text, kanallar_text, sunucu_text_page, sunucu_text_page2, sunucu_hizmetleri_text, botlar_text, uye_komutlar_text

class Bionluk(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    async def create_invite(self, guild):
        invite = await guild.text_channels[0].create_invite()
        return f'''<:blank:1035876485082382426>
<:start:1048034909937213562><:end:1048034908347564113> **DAVET LİNKİ** <:start:1048034909937213562><:end:1048034908347564113>
{invite.url}
        '''

    @app_commands.command(name="bionluk", description="Bionluk işim için kullandığım bilgilendirme mesajlarının toplu halini atar.")
    @commands.is_owner()
    async def bionluk(self, interaction):

        channel_names = [
            ("🎉・çekilişler", "giveaways"),
            ("🎫・destek", "support"),
            ("🎮・oyunlar", "games"),
            ("➕ kanal oluştur", "temporary"),
            ("📺・yayınlar", "streams"),
            ("📢・duyurular", "announcements"),
            ("🥳 Etkinlik", "activity"),
            ("🧠・tartışmalar", "forum"),
            ("📜・kurallar", "rules"),
            ("🤖・komutlar", "commands"),
            ("🎭・roller", "roles"),
            ("💬・sohbet", "general")
        ]

        role_names = [
            ("Bot", "bot"),
            ("Yönetici", "admin"),
            ("Süper Moderatör", "sup_mod"),
            ("Emektar", "emektar"),
            ("Moderatör", "mod"),
            ("Deneme Moderatör", "trial_mod"),
            ("Organizatör", "organizer"),
            ("Destek", "support"),
            ("VIP", "vip"),
            ("Server Booster", "booster"),
            ("Üye", "member"),
            ("Kayıtsız Üye", "unregistered_member"),
            ("Bronz", "bronz"),
            ("Gümüş", "silver"),
            ("Altın", "gold"),
            ("Trityum", "tritium"),
            ("Elmas", "diamond"),
            ("Müdavim", "mudavim"),
            ("Uykucu", "sleep"),
            ("DJ", "dj")
        ]

        roles_mentions = {}
        for role_name, role_code in role_names:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            roles_mentions[role_code] = role.mention if role else "—"

        channels_mentions = {}
        for channel_name, channel_code in channel_names:
            channel = discord.utils.get(interaction.guild.channels, name=channel_name)
            channels_mentions[channel_code] = channel.mention if channel else "—"


        view = ui.View()
        view.add_item(ui.Button(label="Önemli Bot Komutları", url="https://medium.com/@bergaman9/%C3%B6nemli-discord-komutlar%C4%B1-3a4598cde13a", style=discord.ButtonStyle.link, emoji="🔗"))

        view2 = ui.View()
        view2.add_item(ui.Button(label="Discord Bot Özellikleri", url="https://medium.com/@bergaman9/2023-y%C4%B1l%C4%B1nda-sunucunuzda-olmas%C4%B1-gereken-discord-botlar%C4%B1-e895de2052dc", style=discord.ButtonStyle.link, emoji="🔗"))

        komutlar_embed = discord.Embed(title="DİSCORD KOMUTLARI", description=komutlar_text, color=0xfad100)
        botlar_embed = discord.Embed(title="BOT ÖZELLİKLERİ", description=botlar_text, color=0x00e9b4)
        roller_embed = discord.Embed(title="SUNUCU ROLLERİ", description=roller_text.format(**roles_mentions), color=0xff1f1f)
        kanallar_embed = discord.Embed(title="SUNUCU KANALLARI", description=kanallar_text.format(**channels_mentions), color=0x00e9b4)

        sunucu_hizmetleri_embed = discord.Embed(title="BERGAMAN SUNUCU HİZMETLERİ", description=sunucu_hizmetleri_text, color=0xffffff)
        sunucu_hizmetleri_embed.set_thumbnail(url="https://i.imgur.com/fntLhGX.png")

        all_mentions = {**channels_mentions, **roles_mentions}
        sunucu_embed = discord.Embed(title="SUNUCU ÖZELLİKLERİ", description=sunucu_text_page.format(**all_mentions, guild_id=interaction.guild.id), color=0xf47fff)
        sunucu_embed.set_footer(text="Sayfa 1/2")
        sunucu_embed.set_thumbnail(url=interaction.guild.icon.url)

        sunucu_embed2 = discord.Embed(title="SUNUCU ÖZELLİKLERİ", description=sunucu_text_page2.format(**all_mentions, guild_id=interaction.guild.id), color=0xf47fff)
        sunucu_embed2.set_footer(text="Sayfa 2/2")
        sunucu_embed2.set_thumbnail(url=interaction.guild.icon.url)

        await interaction.response.send_message(embed=create_embed(description="Mesajlar gönderildi!", color=discord.Color.green()), ephemeral=True)
        await interaction.channel.send(embed=sunucu_embed)
        await interaction.channel.send(embed=sunucu_embed2)
        await interaction.channel.send(embed=komutlar_embed, view=view)
        await interaction.channel.send(embed=botlar_embed, view=view2)
        await interaction.channel.send(embed=roller_embed)
        await interaction.channel.send(embed=kanallar_embed)
        await interaction.channel.send(embed=sunucu_hizmetleri_embed)


    @app_commands.command(name="duyurular", description="Bionluk işim için kullandığım duyuru mesajlarının toplu halini atar.")
    @commands.is_owner()
    async def duyurular(self, interaction):

        role_names = [
            ("Bot", "bot"),
            ("Yönetici", "admin"),
            ("Süper Moderatör", "sup_mod"),
            ("Emektar", "emektar"),
            ("Moderatör", "mod"),
            ("Deneme Moderatör", "trial_mod"),
            ("Organizatör", "organizer"),
            ("Destek", "support"),
            ("VIP", "vip"),
            ("Server Booster", "booster"),
            ("Üye", "member"),
            ("Kayıtsız Üye", "unregistered_member"),
            ("Bronz", "bronz"),
            ("Gümüş", "silver"),
            ("Altın", "gold"),
            ("Trityum", "tritium"),
            ("Elmas", "diamond"),
            ("Müdavim", "mudavim"),
            ("Uykucu", "sleep"),
            ("DJ", "dj")
        ]

        roles_mentions = {}
        for role_name, role_code in role_names:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            roles_mentions[role_code] = role.mention if role else "—"

        roller_embed = discord.Embed(
            title="SUNUCU ROLLERİ",
            description=roller_text.format(**roles_mentions),
            color=0xff1f1f
        )
        komutlar_embed = discord.Embed(
            title="ÜYELER İÇİN DİSCORD KOMUTLARI",
            description=uye_komutlar_text,
            color=0x00e9b4
        )
        duyurular_embed = discord.Embed(
            title="SUNUCU DUYURULARI",
            description=duyurular_text,
            color=0xff1f1f
        )

        await interaction.response.send_message(embed=create_embed(description="Mesajlar gönderildi!", color=discord.Color.green()), ephemeral=True)
        await interaction.channel.send(embed=duyurular_embed)
        await interaction.channel.send(embed=roller_embed)
        await interaction.channel.send(embed=komutlar_embed)


    @app_commands.command(name="kurallar", description="Bionluk işim için kullandığım kurallar mesajlarının toplu halini atar.")
    @commands.is_owner()
    async def kurallar(self, interaction):

        destek_channel = discord.utils.get(interaction.guild.channels, name="🎫・destek")

        destek_channel = destek_channel.mention if destek_channel else "—"

        kurallar_embed = discord.Embed(title="SUNUCU KURALLARI", description=kurallar_text, color=0xff1f1f)
        destek_embed = discord.Embed(title="DESTEK", description=destek_text.format(destek=destek_channel), color=0xff1f1f)

        invite_link = await self.create_invite(interaction.guild)

        await interaction.response.send_message(embed=create_embed(description="Mesajlar gönderildi!", color=discord.Color.green()), ephemeral=True)
        await interaction.channel.send(embed=kurallar_embed)
        await interaction.channel.send(embed=destek_embed)
        await interaction.channel.send(invite_link)


    async def update_topic(self, channel, new_topic):
        await channel.edit(topic=new_topic)

    @app_commands.command(name="set_topics", description="Bionluk işim için kullandığım kanalların açıklamalarını düzenlemeye yarayan komut.")
    @commands.is_owner()
    async def set_topics(self, interaction):
        await interaction.response.defer()

        channel_data = [
            ("🎉・çekilişler", "Çekilişlerin düzenlendiği kanal."),
            ("🎫・destek", "Üyelerin ticket açarak destek alabildiği kanal."),
            ("🎮・oyunlar", "Oyunlar gerçek hayatı taklit eden harika teknoloji ürünleridir."),
            ("📺・yayınlar", "Twitch yayınlarının duyurulduğu kanal."),
            ("📢・duyurular", "Sunucu hakkında yapılan duyuruları buradan takip edebilirsiniz."),
            ("🧠・tartışmalar",
             "Çeşitli konularda tartışmak, soru sormak, çözüm aramak ve bilgilendirmek için konular açabilirsiniz. Kurallara aykırı içerikler paylaşmak yasaktır."),
            ("🤖・komutlar", "Komutları kullanabileceğiniz kanal."),
            ("📜・kurallar", "Sunucu kurallarını buradan okuyabilirsiniz."),
            ("💬・sohbet", "Kurallar çerçevesinde her konudan konuşabilirsiniz."),
            ("🎭・roller", "Reaksiyon rollerinizi alabileceğiniz kanal."),
            ("👋・hoş-geldin", "Sunucuya yeni katılan üyeleri karşıladığımız kanal."),
            ("📷・görseller", "Kurallara aykırı bir şey olmadığı sürece herhangi bir görsel paylaşabilirsiniz."),
            ("🎥・videolar", "Kurallara aykırı bir şey olmadığı sürece herhangi bir video paylaşabilirsiniz."),
            ("🍿・dizi-film",
             "Dizi ve filmler üzerine her şeyi konuşabilirsiniz. Spoiler içeren mesajlar için ||böyle|| yazınız."),
            ("🎵・müzik", "Müzik çalmak için **m!play [link]** komutunu kullanabilirsiniz.")
        ]

        for channel_name, description in channel_data:
            channel = discord.utils.get(interaction.guild.channels, name=channel_name)
            if channel is not None:
                await self.update_topic(channel, description)

        await interaction.response.send_message("Kanal açıklamaları düzenlendi.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Bionluk(bot))