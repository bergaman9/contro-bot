import discord, time
from discord.ext import commands

class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # add emojis if someone write message to a channel in a server
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == 1155715329318719520:
            # Botun kendi mesajlarına reaksiyon koymaması için kontrol
            if message.author.id == 783064615012663326:
                return

            # Belirli bir role sahip olmayan kişilere reaksiyon koymak için kontrol
            if not discord.utils.get(message.author.roles, id=1155705648944779299):
                await message.add_reaction("✅")
                await message.add_reaction("❌")

    # if special role react to message, give role to user and change his nickname to message content
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # Kanal ID kontrolü
        if payload.channel_id == 1155715329318719520:
            # Mesajı ve reaksiyonu ekleyen üyeyi al
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            reacting_member = discord.utils.get(channel.guild.members, id=payload.user_id)  # Reaksiyon ekleyen üye
            message_author = message.author  # Mesajı atan üye
            # Yetkili kontrolü
            if discord.utils.get(reacting_member.roles, id=1155705648944779299):
                if str(payload.emoji) == "✅":
                    # Üyeye yeni rol ver
                    whitelist_role = discord.utils.get(message_author.guild.roles, id=1155706346025529347)
                    interview_role = discord.utils.get(message_author.guild.roles, id=1155706356775538719)
                    new_member_role = discord.utils.get(message_author.guild.roles, id=1155706350958018613)
                    unregistered_role = discord.utils.get(message_author.guild.roles, id=1155706361749966950)
                    await message_author.remove_roles(unregistered_role, interview_role)
                    await message_author.add_roles(whitelist_role, new_member_role)
                    # Mesajı atan üyenin ismini mesaj içeriğiyle değiştir
                    await message_author.edit(nick=message.content)
                elif str(payload.emoji) == "❌":
                    # Üyeye isminin uygunsuz olduğuna dair kanala ve özelden mesaj at
                    await channel.send(f"{message_author.mention}, gönderdiğiniz isim uygunsuz. Lütfen uygun bir isim gönderin.")
                    await message_author.send("Gönderdiğiniz isim uygunsuz. Lütfen uygun bir isim gönderin.")
            elif discord.utils.get(reacting_member.roles, id=1155705648944779299) is None:
                # if reacting member is not bot
                if reacting_member.id != 783064615012663326:
                    await message.remove_reaction(payload.emoji, reacting_member)
                    await channel.send(f"{reacting_member.mention}, bu mesajı sadece yetkililer kullanabilir.")


async def setup(bot):
    await bot.add_cog(Custom(bot))
