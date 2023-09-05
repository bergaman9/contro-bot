import random

import discord
from discord import app_commands
from discord.ext import commands


from utils import initialize_mongodb, create_embed, check_if_ctx_or_interaction

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Katıl", style=discord.ButtonStyle.gray, custom_id="participate_button"))
        self.add_item(discord.ui.Button(label="Katılımcılar", style=discord.ButtonStyle.gray, custom_id="participants_button"))
        self.add_item(discord.ui.Button(label="Çekilişi Bitir", style=discord.ButtonStyle.danger, custom_id="reroll_button"))

class GiveawayEditView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Katılımcılar", style=discord.ButtonStyle.gray, custom_id="participants_button"))
        self.add_item(discord.ui.Button(label="Aktif Çekilişler", style=discord.ButtonStyle.gray, custom_id="active_giveaways_button"))
        self.add_item(discord.ui.Button(label="Çekilişi Tekrarla", style=discord.ButtonStyle.danger, custom_id="reroll_button"))

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    @commands.hybrid_command(name="giveaway_create", description="Starts a giveaway.")
    @app_commands.describe(limit="When how many members join the giveaway will end.", prize="What is the prize of the giveaway?", roles="Which roles can join the giveaway? @role1 @role2 ...")
    @commands.has_permissions(ban_members=True)
    async def giveaway_create(self, ctx, limit, prize, roles: commands.Greedy[discord.Role] = None):

        embed = discord.Embed(title=prize,description=f"Katılmak için katıl butonuna tıkla! \nToplamda **{limit}** kişi katıldığında çekiliş tamamlanacak.", colour=0xff0076)
        embed.add_field(name="Başlatan", value=ctx.author.mention, inline=True)
        if roles:
            embed.add_field(name="Katılabilir Roller", value=' '.join([role.mention for role in roles]), inline=True)
        else:
            embed.add_field(name="Katılabilir Roller", value="@everyone", inline=True)
        embed.add_field(name="Kazanan Sayısı", value="1", inline=True)
        embed.set_image(url="https://i.ibb.co/8Kn0L6t/giveaway-banner.png")
        message = await ctx.channel.send(embed=embed, view=GiveawayView())
        embed.set_footer(text=f"Çekiliş ID: {message.id}")
        await ctx.send(embed=create_embed(description="Çekiliş oluşturuldu.", color=discord.Color.green()), ephemeral=True)

        giveaway_data = {
            "guild_id": ctx.guild.id,
            "message_id": message.id,
            "channel_id": message.channel.id,
            "prize": prize,
            "limit": limit,
            "status": True,
            "winner": None,
            "participants": [],
            "allowed_roles": [role.id for role in roles] if roles else []
        }
        self.mongo_db['giveaways'].insert_one(giveaway_data)


    @commands.hybrid_command(name="giveaway_shuffle", description="Shuffles giveaway participants")
    @app_commands.describe(message_id="The ID of the giveaway message.")
    @commands.has_permissions(ban_members=True)
    async def giveaway_shuffle(self, ctx, message_id):

        try:
            message_id = int(message_id)  # Bu satırı ekledim.
        except ValueError:
            await ctx.send("Geçersiz mesaj ID'si.")
            return

        # Retrieve the giveaway data from the MongoDB collection
        giveaway_data = self.mongo_db['giveaways'].find_one({"message_id": message_id})

        if giveaway_data:
            participantsList = giveaway_data["participants"]

            if participantsList:
                selected_user_id = random.choice(participantsList)
                selected_user = await self.bot.fetch_user(selected_user_id)

                # Update the winnerShuffle field in the MongoDB collection
                # id -> message_id olarak değiştirildi. Kontrol edin.
                self.mongo_db['giveaways'].update_one(
                    {"message_id": message_id},
                    {"$set": {"winnerShuffle": selected_user_id}}
                )

                await ctx.send(f"🎉 {selected_user.mention} çekilişin yeni talihlisidir!")
            else:
                await ctx.send(embed=create_embed(description="Çekilişte hiç katılımcı yok.", color=discord.Color.red()))
        else:
            await ctx.send("Geçersiz çekiliş ID.")

    @commands.hybrid_command(name="giveaway_show", description="Shows active giveaways on the guild.")
    @commands.has_permissions(ban_members=True)
    async def giveaway_show(self, ctx: commands.Context):
        await self.active_giveaways_handler(ctx)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.data["custom_id"] == "participate_button":
                guild = self.bot.get_guild(interaction.guild.id)
                member = guild.get_member(interaction.user.id)
                giveaway_data = self.mongo_db['giveaways'].find_one({"message_id": interaction.message.id})

                if not giveaway_data:
                    return  # Exit if no giveaway data found

                allowed_roles = giveaway_data.get("allowed_roles", [])
                user = self.bot.get_user(interaction.user.id)

                if not allowed_roles or (member and any(role.id in allowed_roles for role in member.roles)):
                    limit = giveaway_data["limit"]
                    prize = giveaway_data["prize"]
                    status = giveaway_data["status"]
                    participants_list = giveaway_data["participants"]
                    message_id = giveaway_data["message_id"]
                    guild_id = giveaway_data["guild_id"]

                    # Check if the user is already in the list
                    if member.id not in participants_list and status:
                        participants_list.append(interaction.user.id)  # Add only the current user

                        self.mongo_db['giveaways'].update_one({"message_id": interaction.message.id},
                                                              {"$set": {"participants": participants_list}})
                        await interaction.response.send_message(
                            embed=create_embed(description=f"Çekilişe katıldınız.", color=discord.Color.green()),
                            ephemeral=True)

                        if len(participants_list) >= int(limit):
                            selected_user = self.bot.get_user(random.choice(participants_list))
                            channel = self.bot.get_channel(interaction.channel.id)
                            self.mongo_db['giveaways'].update_one({"message_id": interaction.message.id},
                                                                  {"$set": {"status": False, "winner": selected_user.id,
                                                                            "participants": participants_list}})

                            await channel.send(embed=create_embed(
                                description=f"🎉 {selected_user.mention} tebrikler! **{prize}** kazandınız!",
                                color=0xff0076))
                            await selected_user.send(embed=create_embed(
                                description=f"🎉 {selected_user.mention} tebrikler! **{prize}** kazandınız!",
                                color=0xff0076))
                            message = await channel.fetch_message(message_id)
                            embed = discord.Embed(title=prize, description=f"Çekiliş tamamlandı, katılan herkese teşekkürler!", colour=0xff0076)
                            embed.add_field(name="Başlatan", value=message.embeds[0].fields[0].value, inline=True)
                            embed.add_field(name="Katılabilir Roller", value=message.embeds[0].fields[1].value,
                                            inline=True)
                            embed.add_field(name="Kazanan", value=selected_user.mention, inline=True)
                            embed.set_image(url="https://i.ibb.co/8Kn0L6t/giveaway-banner.png")
                            await message.edit(embed=embed, view=GiveawayEditView())
                    elif status == False:
                        try:
                            user = self.bot.get_user(interaction.user.id)
                            await user.send(
                                embed=create_embed(description="Bu çekiliş aktif değil!", color=discord.Color.red()))
                        except:
                            guild = self.bot.get_guild(guild_id)
                            owner = self.bot.get_user(guild.owner.id)
                            await owner.send(
                                embed=create_embed(description=f"{user.mention} kişisine mesaj gönderilemedi.",
                                                   color=discord.Color.red()))
                    else:
                        await interaction.response.send_message(embed=create_embed(description="Bu çekilişe zaten katıldınız.", color=discord.Color.red()), ephemeral=True)
                else:
                    await interaction.response.send_message(embed=create_embed(description="Bu çekilişe katılamazsınız.", color=discord.Color.red()), ephemeral=True)


            elif interaction.data["custom_id"] == "participants_button":
                giveaway_data = self.mongo_db['giveaways'].find_one({"message_id": interaction.message.id})
                if giveaway_data:
                    participants_list = giveaway_data["participants"]
                    participants = [self.bot.get_user(user_id) for user_id in participants_list]
                    participants = [f"{user.mention}" for user in participants]
                    if len(participants) == 0:
                        participants = ["Çekilişe henüz katılan yok."]
                    embed = discord.Embed(title="Çekiliş Katılımcıları", description="\n".join(participants), color=discord.Color.green())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=create_embed(description="Çekiliş bulunamadı.", color=discord.Color.red()), ephemeral=True)
            elif interaction.data["custom_id"] == "reroll_button":
                guild = self.bot.get_guild(interaction.guild_id)
                member = guild.get_member(interaction.user.id)
                if member.guild_permissions.ban_members:
                    giveaway_data = self.mongo_db['giveaways'].find_one({"message_id": interaction.message.id})
                    if giveaway_data:
                        participants_list = giveaway_data["participants"]
                        if participants_list:
                            selected_user = self.bot.get_user(random.choice(participants_list))
                            channel = self.bot.get_channel(interaction.channel_id)
                            await channel.send(embed=create_embed(description=f"🎉 {selected_user.mention} çekilişin yeni talihlisidir!", color=0xff0076))
                            await selected_user.send(embed=create_embed(description=f"🎉 {selected_user.mention} tebrikler! **{giveaway_data['prize']}** kazandınız!", color=0xff0076))
                            message = await channel.fetch_message(interaction.message.id)
                            embed = discord.Embed(title=giveaway_data['prize'], description=f"Çekiliş tamamlandı, katılan herkese teşekkürler!", colour=0xff0076)
                            embed.add_field(name="Başlatan", value=message.embeds[0].fields[0].value, inline=True)
                            embed.add_field(name="Katılabilir Roller", value=message.embeds[0].fields[1].value, inline=True)
                            embed.add_field(name="Kazanan", value=selected_user.mention, inline=True)
                            embed.set_image(url="https://i.ibb.co/8Kn0L6t/giveaway-banner.png")
                            await message.edit(embed=embed, view=GiveawayEditView())
                            await interaction.response.send_message(embed=create_embed(description="Çekiliş tekrarlandı.", color=discord.Color.green()), ephemeral=True)
                        else:
                            await interaction.response.send_message(embed=create_embed(description="Çekilişte hiç katılımcı yok.", color=discord.Color.red()), ephemeral=True)
                else:
                    await interaction.response.send_message(embed=create_embed(description="Bu çekilişi tekrarlamak için yetkiniz yok.", color=discord.Color.red()), ephemeral=True)
            elif interaction.data["custom_id"] == "active_giveaways_button":
                await self.active_giveaways_handler(interaction)

    @commands.hybrid_command(name="giveaway_remove", description="Removes a giveaway.")
    @app_commands.describe(message_id="The ID of the giveaway message.")
    @commands.has_permissions(ban_members=True)
    async def giveaway_remove(self, ctx, message_id):
        giveaway_data = self.mongo_db['giveaways'].find_one({"message_id": int(message_id)})
        if giveaway_data:
            self.mongo_db['giveaways'].delete_one({"message_id": int(message_id)})
            await ctx.send(embed=create_embed(description="Çekiliş silindi.", color=discord.Color.green()), ephemeral=True)

    async def active_giveaways_handler(self, interaction: discord.Interaction):

        guild, send, channel = await check_if_ctx_or_interaction(interaction)

        active_giveaways = self.mongo_db['giveaways'].find(
            {"guild_id": guild.id, "status": True})
        active_giveaways_list = [
            f"[{giveaway['prize'].title()} Çekilişi]"
            f"(https://discord.com/channels/{guild.id}/{giveaway['channel_id']}/{giveaway['message_id']})"
            for giveaway in active_giveaways
        ]

        if len(active_giveaways_list) == 0:
            embed = discord.Embed(title=f"Aktif Çekilişler", description="Aktif çekiliş yok.",
                                  color=discord.Color.green())
            await send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title=f"Aktif Çekilişler", description='\n'.join(active_giveaways_list),
                                  color=discord.Color.green())
            await send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Giveaway(bot))