import random

import discord
from discord.ext import commands, tasks

from utility.class_utils import Paginator
from utility.utils import initialize_mongodb, create_embed, prepare_leaderboard_embeds


class Levelling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        self.voice_xp_loop.start()  # Arka plan görevini başlat

    @tasks.loop(seconds=60)
    async def voice_xp_loop(self):
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue

                if member.voice and not member.voice.self_mute and not member.voice.afk:
                    user_data = self.mongo_db["users"].find_one({"user_id": str(member.id)})
                    channel_id = str(member.voice.channel.id)

                    if not user_data:
                        self.mongo_db["users"].insert_one({
                            "user_id": str(member.id),
                            "guilds": {
                                str(guild.id): {
                                    "xp": random.randint(1, 5),
                                    "level": 1,
                                    "total_voice_time": 60,
                                    "voice_channels": {channel_id: 60}
                                }
                            }
                        })
                    else:
                        guild_data = user_data["guilds"].get(str(guild.id), {})
                        new_xp = guild_data.get("xp", 0) + random.randint(1, 5)
                        new_level = guild_data.get("level", 1)
                        new_voice_time = guild_data.get("total_voice_time", 0) + 60

                        # Kanal süreleri için
                        channels_time = guild_data.get("voice_channels", {})
                        channels_time[channel_id] = channels_time.get(channel_id, 0) + 60

                        if new_xp >= 5 * (new_level ** 2) + 50 * new_level + 100:
                            new_level += 1
                            new_xp = 0

                            level_up_channel_id = self.mongo_db['settings'].find_one({"guild_id": str(guild.id)}).get(
                                "level_channel_id")
                            if level_up_channel_id:
                                level_up_channel = discord.utils.get(guild.channels, id=int(level_up_channel_id))
                            if level_up_channel:
                                await level_up_channel.send(f"🎉 Tebrikler {member.mention}! Seviye {new_level} oldun.")

                        self.mongo_db["users"].update_one(
                            {"user_id": str(member.id)},
                            {"$set": {
                                f"guilds.{str(guild.id)}.xp": new_xp,
                                f"guilds.{str(guild.id)}.level": new_level,
                                f"guilds.{str(guild.id)}.total_voice_time": new_voice_time,
                                f"guilds.{str(guild.id)}.voice_channels": channels_time
                            }}
                        )

    @voice_xp_loop.before_loop
    async def before_voice_xp_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        try:
            user_data = self.mongo_db["users"].find_one({"user_id": str(message.author.id)})
            guild_id = str(message.guild.id)
            channel_id = str(message.channel.id)

            if not user_data:
                self.mongo_db["users"].insert_one({
                    "user_id": str(message.author.id),
                    "guilds": {
                        guild_id: {
                            "xp": 1,
                            "level": 1,
                            "total_message_count": 1,
                            "text_channels": {channel_id: 1}
                        }
                    }
                })
            else:
                guild_data = user_data["guilds"].get(guild_id, {
                    "xp": 0,
                    "level": 1,
                    "total_message_count": 0,
                    "text_channels": {}
                })

                guild_data["xp"] += 1
                guild_data["total_message_count"] += 1
                guild_data["text_channels"][channel_id] = guild_data["text_channels"].get(channel_id, 0) + 1

                if guild_data["xp"] >= 5 * (guild_data["level"] ** 2) + 50 * guild_data["level"] + 100:
                    guild_data["level"] += 1
                    guild_data["xp"] = 0

                    level_up_channel_id = self.mongo_db['settings'].find_one({"guild_id": guild_id})["level_channel_id"]
                    if level_up_channel_id:
                        level_up_channel = discord.utils.get(message.guild.channels, id=level_up_channel_id)
                        if level_up_channel:
                            await level_up_channel.send(
                                f"🎉 Tebrikler {message.author.mention}! Seviye {guild_data['level']} oldun.")

                self.mongo_db["users"].update_one(
                    {"user_id": str(message.author.id)},
                    {"$set": {
                        f"guilds.{guild_id}.xp": guild_data["xp"],
                        f"guilds.{guild_id}.level": guild_data["level"],
                        f"guilds.{guild_id}.total_message_count": guild_data["total_message_count"],
                        f"guilds.{guild_id}.text_channels": guild_data["text_channels"]
                    }}
                )

        except Exception as e:
            print(e)

    @commands.hybrid_command(name="rank", description="Shows the level info of the member.", aliases=["level"])
    async def rank(self, ctx, member: discord.Member = None):
        if not member:
            member = ctx.author

        user_data = self.mongo_db["users"].find_one({"user_id": str(member.id)})

        if not user_data or str(ctx.guild.id) not in user_data["guilds"]:
            return await ctx.send(embed=create_embed(description="Üye verisi bulunamadı.", color=discord.Color.red()))

        guild_data = user_data["guilds"][str(ctx.guild.id)]

        xp = guild_data["xp"]
        level = guild_data["level"]
        voice_time = guild_data.get("total_voice_time", 0)  # Ses kanalında geçirilen toplam süre (varsayılan olarak 0)
        total_message_count = guild_data.get("total_message_count", 0)  # Toplam mesaj sayısı (varsayılan olarak 0)
        next_level_xp = 5 * (level ** 2) + 50 * level + 100
        voice_time_dk = int(voice_time / 60)

        description = f"""
        **Member ID**: `{member.id}`\n
        **XP:** `{xp}`/`{next_level_xp}`
        **Level:** `{level}`\n
        **Total Voice Time:** `{voice_time_dk} minutes`
        **Total Message:** `{total_message_count} messages`
        """
        embed = discord.Embed(description=description, color=member.color)
        embed.set_thumbnail(url=member.avatar.url)
        embed.set_author(name=f"Level info for {member.name}", icon_url=member.avatar.url)
        embed.set_footer(text=f"{member.guild.name}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="level_leaderboard", description="Shows the level leaderboard of the server.")
    async def leaderboard(self, ctx):
        embed_list = prepare_leaderboard_embeds(self.mongo_db, ctx.guild)
        view = Paginator(embed_list)
        await ctx.send(embed=embed_list[0], view=view)

    @commands.hybrid_command(name="set_level_channel", description="Sets the level channel.")
    @commands.has_permissions(manage_guild=True)
    async def set_level_channel(self, ctx, channel: discord.TextChannel):
        try:
            self.mongo_db['settings'].update_one(
                {"guild_id": ctx.guild.id},
                {
                    "$set": {
                        "level_channel_id": channel.id
                    }
                },
                upsert=True
            )
            await ctx.send(
                embed=create_embed(f"Level channel has been set to {channel.mention}.", color=discord.Color.green()))
        except Exception as e:
            print(e)


async def setup(bot):
    await bot.add_cog(Levelling(bot))
