import discord
from discord.ext import commands

from utils import initialize_mongodb, create_embed


class Invites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        self.invites = {}

    @commands.Cog.listener()
    async def on_ready(self):
        # Bot başladığında tüm sunuculardaki davetleri al

        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
                self.mongo_db["invites"].update_one(
                    {"guild_id": guild.id},
                    {
                        "$set": {
                            "old_invites": {invite.code: invite.uses for invite in self.invites[guild.id]}
                        }
                    },
                    upsert=True
                )
            except:
                print("Error: ", guild.id, guild.name, guild.owner_id)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f"{member.name} has joined the server.")

        new_invites = await member.guild.invites()
        old_invites = self.mongo_db["invites"].find_one({"guild_id": member.guild.id})["old_invites"]

        print(f"Number of old invites: {len(old_invites)}")
        print(f"Old invites: {old_invites}")
        print(f"Number of new invites: {len(new_invites)}")

        try:
            for invite in new_invites:
                print(f"Checking invite: {invite.code} | Uses: {invite.uses} | Inviter: {invite.inviter}")

                # Eğer bu davet kodu eski davetlerde yoksa, bu daveti atlayalım.
                # if invite.code not in old_invites:
                #     continue

                print(f"Comparing with old invite: {old_invites[invite.code]}")

                guild_entry = self.mongo_db["invites"].find_one({"guild_id": member.guild.id})

                if not guild_entry:
                    self.mongo_db["invites"].insert_one({
                        "guild_id": member.guild.id,
                        "invited_members": {}
                    })

                if invite.uses > old_invites[invite.code]:
                    print("Inviter: ", invite.inviter)
                    logs = self.mongo_db["logger"].find_one({"guild_id": member.guild.id})
                    if logs:
                        log_channel_id = logs["channel_id"]
                        if log_channel_id:
                            log_channel = discord.utils.get(member.guild.channels, id=log_channel_id)

                    await log_channel.send(embed=create_embed(
                        description=f"{member.mention} sunucuya katıldı. {invite.inviter.mention} tarafından davet edildi.",
                        color=discord.Color.green()))

                    # Bu davet linki kullanıldı, davet eden kişiyi veritabanına kaydet

                    self.mongo_db["invites"].update_one(
                        {"guild_id": member.guild.id},
                        {
                            "$set": {
                                f"invited_members.{member.id}": invite.inviter.id
                            }
                        },
                        upsert=True
                    )

                    # Update the old_invites in the database
                    updated_invites = {inv.code: inv.uses for inv in new_invites}
                    self.mongo_db["invites"].update_one(
                        {"guild_id": member.guild.id},
                        {
                            "$set": {
                                "old_invites": updated_invites
                            }
                        }
                    )
                    return
        except:
            print("Error: ", invite.code, dict(old_invites)[invite.code].uses)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Üye sunucudan ayrıldığında davetleri güncelle
        logs = self.mongo_db["logger"].find_one({"guild_id": member.guild.id})
        if logs:
            log_channel_id = logs["channel_id"]
            if log_channel_id:
                log_channel = discord.utils.get(member.guild.channels, id=log_channel_id)
                print(log_channel)

        invites = self.mongo_db["invites"].find_one({"guild_id": member.guild.id})
        if invites:
            invited_members = invites["invited_members"]
            print(invited_members)
            inviter_id = invited_members.get(str(member.id))
            print(inviter_id)
            if inviter_id:
                inviter = member.guild.get_member(int(inviter_id))
                print(inviter)
                await log_channel.send(embed=create_embed(
                    description=f"{member.mention} sunucudan ayrıldı. {inviter.mention} tarafından davet edilmişti.",
                    color=discord.Color.red()))
                return

        self.mongo_db["invites"].update_one(
            {"guild_id": member.guild.id},
            {
                "$set": {
                    "old_invites": {invite.code: invite.uses for invite in await member.guild.invites()}
                }
            })

    @commands.hybrid_command(name="invites_leaderboard", description="Shows the invite leaderboard of the server.")
    async def leaderboard(self, ctx):
        # Fetch the invites document for the guild
        invites = self.mongo_db["invites"].find_one({"guild_id": ctx.guild.id})
        if not invites:
            await ctx.send(
                embed=create_embed(description="No invite data found for this server.", color=discord.Color.red()))
            return

        invited_members = invites.get("invited_members", {})

        if not invited_members:
            await ctx.send(embed=create_embed(description="No invite leaderboard data available for this server.",
                                              color=discord.Color.red()))
            return

        # Count the number of times each user invited someone
        inviter_counts = {}
        for inviter_id in invited_members.values():
            inviter_counts[inviter_id] = inviter_counts.get(inviter_id, 0) + 1

        # Sort the users by their invite counts in descending order
        sorted_inviters = sorted(inviter_counts.items(), key=lambda x: x[1], reverse=True)

        # Prepare the leaderboard message
        leaderboard_msg = ""
        for idx, (inviter_id, count) in enumerate(sorted_inviters, 1):
            member = ctx.guild.get_member(int(inviter_id))
            if member:
                leaderboard_msg += f"{idx}. {member.mention} - {count} invites\n"

        # Create the embed and send
        embed = discord.Embed(title="Invite Leaderboard", description=leaderboard_msg, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.command(name="invites", description="Shows leaderboard of invites.")
    async def invites(self, ctx, member: discord.Member = None):
        """
        Display the number of people a user has invited.
        If no user is provided, it shows the invites of the command invoker.
        """
        if not member:
            member = ctx.author

        # Fetch the invites document for the guild
        invites_data = self.mongo_db["invites"].find_one({"guild_id": ctx.guild.id})

        if not invites_data:
            await ctx.send("No invite data found for this server.")
            return

        invited_members = invites_data.get("invited_members", {})

        # Count how many people the member has invited
        invite_count = list(invited_members.values()).count(member.id)

        embed = discord.Embed(title="Invite Count",
                              description=f"{member.mention} has invited {invite_count} member(s).",
                              color=discord.Color.blue())
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Invites(bot))
