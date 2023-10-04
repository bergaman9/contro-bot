import discord
from discord import app_commands
from discord.ext import commands
import pymongo
import datetime

from utils import create_embed, initialize_mongodb

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id:
            return

        starboard_data = self.mongo_db.starboard.find_one({"guild_id": str(payload.guild_id)})
        if not starboard_data:
            return

        if str(payload.emoji) != starboard_data["emoji"]:
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        starboard_channel = self.bot.get_channel(int(starboard_data["channel_id"]))

        for reaction in message.reactions:
            if str(reaction.emoji) == starboard_data["emoji"] and reaction.count >= starboard_data["count"]:
                starboard_msg_id = starboard_data.get("messages", {}).get(str(message.id))
                embed = discord.Embed(description=message.content, color=discord.Color.gold())
                embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)
                embed.add_field(name="Original Message",
                                value=f"[Jump!](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})")

                if starboard_msg_id:
                    starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                    if not starboard_msg:
                        del starboard_data["messages"][str(message.id)]
                        self.mongo_db.starboard.update_one({"guild_id": str(payload.guild_id)},
                                                           {"$set": starboard_data})
                        return
                    await starboard_msg.edit(embed=embed)
                else:
                    sent_msg = await starboard_channel.send(embed=embed)
                    if "messages" not in starboard_data:
                        starboard_data["messages"] = {}
                    starboard_data["messages"][str(message.id)] = sent_msg.id
                    self.mongo_db.starboard.update_one({"guild_id": str(payload.guild_id)}, {"$set": starboard_data})
                break

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not payload.guild_id:
            return

        starboard_data = self.mongo_db.starboard.find_one({"guild_id": str(payload.guild_id)})
        if not starboard_data or str(payload.emoji) != starboard_data["emoji"]:
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        emoji_found = False

        for reaction in message.reactions:
            if str(reaction.emoji) == starboard_data["emoji"]:
                emoji_found = True
                if reaction.count < starboard_data["count"]:
                    starboard_msg_id = starboard_data.get("messages", {}).get(str(message.id))
                    if starboard_msg_id:
                        starboard_channel = self.bot.get_channel(int(starboard_data["channel_id"]))
                        try:
                            starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                            print("Starboard Message to delete:", starboard_msg)
                            await starboard_msg.delete()
                        except Exception as e:
                            print("Error:", e)
                        del starboard_data["messages"][str(message.id)]
                        self.mongo_db.starboard.update_one({"guild_id": str(payload.guild_id)},
                                                           {"$set": starboard_data})
                    break

        # Eğer ilgili emoji message.reactions içinde bulunamazsa, bu demek oluyor ki reaksiyon sayısı 0'dır.
        if not emoji_found:
            starboard_msg_id = starboard_data.get("messages", {}).get(str(message.id))
            if starboard_msg_id:
                starboard_channel = self.bot.get_channel(int(starboard_data["channel_id"]))
                try:
                    starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                    print("Starboard Message to delete:", starboard_msg)
                    await starboard_msg.delete()
                except Exception as e:
                    print("Error:", e)
                del starboard_data["messages"][str(message.id)]
                self.mongo_db.starboard.update_one({"guild_id": str(payload.guild_id)}, {"$set": starboard_data})

    @commands.hybrid_command(name="add_starboard", description="Add starboard to your server.")
    async def add_starboard(self, ctx, channel: discord.TextChannel, emoji: str, count: int):
        # Starboard ayarını ekleyin veya güncelleyin
        self.mongo_db.starboard.update_one(
            {"guild_id": str(ctx.guild.id)},
            {
                "$set": {
                    "channel_id": str(channel.id),
                    "emoji": emoji,
                    "count": count
                }
            },
            upsert=True
        )

        await ctx.send(embed=create_embed(
            description=f"Starboard set up successfully in {channel.mention} with {emoji} and {count} reactions!",
            color=discord.Color.green()))

    @commands.hybrid_command(name="remove_starboard", description="Remove starboard from your server.")
    async def remove_starboard(self, ctx):
        self.mongo_db.starboard.delete_one({"guild_id": str(ctx.guild.id)})
        await ctx.send(embed=create_embed(description="Starboard system has been removed from this server.",
                                          color=discord.Color.green()))


async def setup(bot):
    await bot.add_cog(Starboard(bot))