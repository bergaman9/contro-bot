import discord
from discord.ext import commands
import pymongo
import os

from utils import get_invite_link, initialize_mongodb

class Partners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    @commands.hybrid_command(name="partner", description="Join partner system.")
    @commands.cooldown(1, 604800, commands.BucketType.guild)
    @commands.has_permissions(manage_guild=True)
    async def partner(self, ctx, description=None):
        partner_channel = self.mongo_db["partners"].find_one({"guild_id": str(ctx.guild.id)})["channel_id"]
        invite_link = await get_invite_link(ctx.guild)  # Assuming get_invite_link() generates an invite link
        partners_collection = self.mongo_db["partners"]

        if partner_channel:
            await partner_channel.purge()
            await partner_channel.edit(topic="Contro botu sunucunuza ekleyip **/partner** komutunu kullanarak partner sistemine dahil olabilirsiniz. Arada bir **/bump** yaparak sunucunuzu kanalda öne çıkarabilirsiniz.")

        if not partner_channel:
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False),
                ctx.guild.me: discord.PermissionOverwrite(send_messages=True)
            }
            partner_channel = await ctx.guild.create_text_channel("🤝・partnerler", overwrites=overwrites)
            await partner_channel.edit(topic="Contro botu sunucunuza ekleyip **/partner** komutunu kullanarak partner sistemine dahil olabilirsiniz. Arada bir **/bump** yaparak sunucunuzu kanalda öne çıkarabilirsiniz.")


        server_id = str(ctx.guild.id)
        partners = partners_collection.find({})
        partner_data = partners_collection.find_one({"guild_id": server_id})

        for partner in partners:
            if partner["guild_id"] != server_id:
                print(partner["guild_id"])
                partner_message = f"<:blank:1035876485082382426> \n🤝 **{partner['server_name']}**"
                if partner['description']:
                    partner_message += f"\n*{partner['description']}*"
                partner_message += f"\n🔗 {partner['invite']}"
                await partner_channel.send(partner_message)

        if partner_data:
            partners_collection.update_one(
                {"guild_id": server_id},
                {
                    "$set": {
                        "invite": invite_link,
                        "description": description,
                        "channel_id": partner_channel.id,
                        "server_name": ctx.guild.name
                    }
                }
            )
        else:
            new_partner_data = {
                "guild_id": server_id,
                "invite": invite_link,
                "description": description,
                "channel_id": partner_channel.id,
                "server_name": ctx.guild.name
            }
            partners_collection.insert_one(new_partner_data)

        # Sending partner message to all partner channels
        for partner in partners:
            if partner["guild_id"] != server_id:
                partner_channel_id = partner["channel_id"]
                partner_channel = self.bot.get_channel(partner_channel_id)
                if partner_channel:
                    partner_message = f"<:blank:1035876485082382426> \n🤝 **{ctx.guild.name}**"
                    if description is not None:
                        partner_message += f"\n*{description}*"
                    partner_message += f"\n🔗 {invite_link}"
                    await partner_channel.send(partner_message)

        await ctx.send("Partner channel has been set up and existing partner data has been updated.")


    @commands.hybrid_command(name="bump", description="Bump the server's partner channels with the server invite link.")
    @commands.cooldown(1, 604800, commands.BucketType.guild)
    async def bump(self, ctx):
        partner_channel = self.mongo_db["partners"].find_one({"guild_id": str(ctx.guild.id)})["channel_id"]
        if not partner_channel:
            return await ctx.send("Partner channel is not set up.")

        partners_collection = self.mongo_db["partners"]
        partners = partners_collection.find({})

        invite_link = await get_invite_link(ctx.guild)  # Assuming get_invite_link() generates an invite link
        description = partners_collection.find_one({"guild_id": str(ctx.guild.id)})["description"]

        for partner in partners:
            if partner["guild_id"] != str(ctx.guild.id):
                partner_channel_id = partner["channel_id"]
                partner_channel = self.bot.get_channel(partner_channel_id)
                if partner_channel:
                    partner_message = f"<:blank:1035876485082382426> \n 🚀 **{ctx.guild}**"
                    if description is not None:
                        partner_message += f"\n*{description}*"
                    partner_message += f"\n🔗 {invite_link}"
                    await partner_channel.send(partner_message)

        await ctx.send("Server bumped in all partner channels.")

    @commands.hybrid_command(name="partner_settings",
                      description="Update partner settings (description and channel_id) in MongoDB.")
    @commands.has_permissions(manage_guild=True)
    async def partner_settings(self, ctx, description=None, partner_channel: discord.TextChannel = None):
        server_id = str(ctx.guild.id)
        partners_collection = self.mongo_db["partners"]
        partner_data = partners_collection.find_one({"guild_id": server_id})

        if partner_data:
            update_data = {}
            if description is not None:
                update_data["description"] = description
            if partner_channel is not None:
                update_data["channel_id"] = partner_channel.id

            print(update_data)

            partners_collection.update_one({"guild_id": server_id}, {"$set": update_data})

            await ctx.send("Partner settings updated successfully.")
        else:
            await ctx.send(
                "Partner settings not found. Make sure you have set up the partner system using the /partner command first.")


async def setup(bot):
    await bot.add_cog(Partners(bot))
