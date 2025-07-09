import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import asyncio

from src.utils.database.connection import initialize_mongodb
from src.utils.core.formatting import create_embed

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        print(f"[Starboard] on_raw_reaction_add tetiklendi: payload.guild_id={payload.guild_id}, emoji={payload.emoji}")
        if not payload.guild_id:
            print("[Starboard] payload.guild_id yok, çıkılıyor")
            return

        starboard_data = self.mongo_db.starboard.find_one({"guild_id": str(payload.guild_id)})
        if not starboard_data or not starboard_data.get("enabled", False):
            print("[Starboard] starboard_data yok veya devre dışı, çıkılıyor")
            return

        emoji = starboard_data.get("emoji", "⭐")
        if str(payload.emoji) != emoji:
            print(f"[Starboard] Emoji uyuşmazlığı: {payload.emoji} != {emoji}, çıkılıyor")
            return

        threshold = starboard_data.get("threshold")
        if threshold is None:
            threshold = starboard_data.get("count", 5)
        self_star = starboard_data.get("self_star", False)
        if "bots_can_star" in starboard_data:
            bots_can_star = starboard_data["bots_can_star"]
        elif "ignore_bots" in starboard_data:
            bots_can_star = not starboard_data["ignore_bots"]
        else:
            bots_can_star = True
        auto_delete = starboard_data.get("auto_delete", False)
        auto_delete_threshold = starboard_data.get("auto_delete_threshold", 0)
        ignored_channels = starboard_data.get("ignored_channels", [])
        ignored_roles = starboard_data.get("ignored_roles", [])
        embed_color = starboard_data.get("embed_color", "#FFD700")
        include_author = starboard_data.get("include_author", True)
        include_timestamp = starboard_data.get("include_timestamp", True)
        include_reactions = starboard_data.get("include_reactions", True)

        if payload.channel_id in ignored_channels:
            print(f"[Starboard] Kanal ignore listesinde: {payload.channel_id}, çıkılıyor")
            return

        try:
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                print(f"[Starboard] Kanal bulunamadı: {payload.channel_id}, çıkılıyor")
                return
            message = await channel.fetch_message(payload.message_id)
            if not message:
                print(f"[Starboard] Mesaj bulunamadı: {payload.message_id}, çıkılıyor")
                return

            if not bots_can_star and message.author.bot:
                print("[Starboard] Bot star engellendi (bots_can_star kapalı), çıkılıyor")
                return

            print(f"[Starboard] self_star: {self_star}, payload.user_id: {payload.user_id}, message.author.id: {message.author.id}")
            if not self_star and str(payload.user_id) == str(message.author.id):
                print("[Starboard] Self star engellendi (ayar kapalı), çıkılıyor")
                return
            else:
                print("[Starboard] Self star izinli veya farklı kullanıcı")

            member = await message.guild.fetch_member(payload.user_id)
            if any(role.id in ignored_roles for role in member.roles):
                print(f"[Starboard] Kullanıcı ignore rolde, çıkılıyor")
                return

            starboard_channel = self.bot.get_channel(int(starboard_data["channel_id"]))
            if not starboard_channel:
                print(f"[Starboard] Starboard kanalı bulunamadı: {starboard_data['channel_id']}, çıkılıyor")
                return

            for reaction in message.reactions:
                if str(reaction.emoji) == emoji and reaction.count >= threshold:
                    print(f"[Starboard] Reaction eşleşti ve threshold aşıldı, starboard'a ekleniyor/güncelleniyor")
                    await self.handle_starboard_message(message, starboard_data, reaction.count)
                    break
                else:
                    print(f"[Starboard] Reaction eşleşmedi veya threshold yetersiz: {reaction.emoji}, {reaction.count}")

        except Exception as e:
            print(f"[Starboard] HATA: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not payload.guild_id:
            return

        starboard_data = self.mongo_db.starboard.find_one({"guild_id": str(payload.guild_id)})
        if not starboard_data:
            return

        emoji = starboard_data.get("emoji", "⭐")
        threshold = starboard_data.get("threshold", 5)
        auto_delete = starboard_data.get("auto_delete", False)
        auto_delete_threshold = starboard_data.get("auto_delete_threshold", 0)

        if str(payload.emoji) != emoji:
            return

        try:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            for reaction in message.reactions:
                if str(reaction.emoji) == emoji:
                    if auto_delete and reaction.count < auto_delete_threshold:
                        await self.remove_starboard_message(message, starboard_data)
                    elif reaction.count < threshold:
                        await self.remove_starboard_message(message, starboard_data)
                    else:
                        await self.update_starboard_message(message, starboard_data, reaction.count)
                    break
            else:
                await self.remove_starboard_message(message, starboard_data)

        except Exception as e:
            print(f"Error in starboard reaction remove: {e}")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild:
            return

        starboard_data = self.mongo_db.starboard.find_one({"guild_id": str(message.guild.id)})
        if not starboard_data:
            return

        await self.remove_starboard_message(message, starboard_data)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not before.guild:
            return

        starboard_data = self.mongo_db.starboard.find_one({"guild_id": str(before.guild.id)})
        if not starboard_data:
            return

        # Update starboard message if content changed
        starboard_msg_id = starboard_data.get("messages", {}).get(str(before.id))
        if starboard_msg_id:
            try:
                starboard_channel = self.bot.get_channel(int(starboard_data["channel_id"]))
                starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                
                embed = await self.create_starboard_embed(after, starboard_data)
                await starboard_msg.edit(embed=embed)
                
                # Update database
                await self.update_starboard_message_in_db(after, starboard_data)
                
            except Exception as e:
                print(f"Error updating starboard message: {e}")

    async def handle_starboard_message(self, message, starboard_data, star_count):
        """Handle adding or updating a starboard message"""
        starboard_msg_id = starboard_data.get("messages", {}).get(str(message.id))
        
        if starboard_msg_id:
            # Update existing message
            await self.update_starboard_message(message, starboard_data, star_count)
        else:
            # Create new message
            await self.create_starboard_message(message, starboard_data, star_count)

    async def create_starboard_message(self, message, starboard_data, star_count):
        """Create a new starboard message"""
        try:
            starboard_channel = self.bot.get_channel(int(starboard_data["channel_id"]))
            embed = await self.create_starboard_embed(message, starboard_data)
            
            sent_msg = await starboard_channel.send(embed=embed)
            
            # Update database
            if "messages" not in starboard_data:
                starboard_data["messages"] = {}
            starboard_data["messages"][str(message.id)] = sent_msg.id
            
            self.mongo_db.starboard.update_one(
                {"guild_id": str(message.guild.id)},
                {"$set": starboard_data}
            )
            
            # Add to starboard_messages collection
            await self.add_starboard_message_to_db(message, sent_msg, star_count)
            
        except Exception as e:
            print(f"Error creating starboard message: {e}")

    async def update_starboard_message(self, message, starboard_data, star_count):
        """Update an existing starboard message"""
        try:
            starboard_msg_id = starboard_data.get("messages", {}).get(str(message.id))
            if not starboard_msg_id:
                return
                
            starboard_channel = self.bot.get_channel(int(starboard_data["channel_id"]))
            starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
            
            embed = await self.create_starboard_embed(message, starboard_data)
            await starboard_msg.edit(embed=embed)
            
            # Update database
            await self.update_starboard_message_in_db(message, starboard_data, star_count)
            
        except Exception as e:
            print(f"Error updating starboard message: {e}")

    async def remove_starboard_message(self, message, starboard_data):
        """Remove a starboard message"""
        try:
            starboard_msg_id = starboard_data.get("messages", {}).get(str(message.id))
            if not starboard_msg_id:
                return
                
            starboard_channel = self.bot.get_channel(int(starboard_data["channel_id"]))
            starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
            await starboard_msg.delete()
            
            # Remove from database
            del starboard_data["messages"][str(message.id)]
            self.mongo_db.starboard.update_one(
                {"guild_id": str(message.guild.id)},
                {"$set": starboard_data}
            )
            
            # Remove from starboard_messages collection
            self.mongo_db.starboard_messages.delete_one({
                "guild_id": str(message.guild.id),
                "original_message_id": str(message.id)
            })
            
        except Exception as e:
            print(f"Error removing starboard message: {e}")

    async def create_starboard_embed(self, message, starboard_data):
        """Create embed for starboard message"""
        embed = discord.Embed(
            description=message.content,
            color=int(starboard_data.get("embed_color", "#FFD700").replace("#", ""), 16)
        )
        
        if starboard_data.get("include_author", True):
            embed.set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url
            )
        
        if starboard_data.get("include_timestamp", True):
            embed.timestamp = message.created_at
        
        # Add attachments
        if message.attachments:
            embed.set_image(url=message.attachments[0].url)
        
        # Add jump link
        embed.add_field(
            name="Original Message",
            value=f"[Jump to Message](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})",
            inline=False
        )
        
        return embed

    async def add_starboard_message_to_db(self, original_msg, starboard_msg, star_count):
        """Add starboard message to database"""
        try:
            self.mongo_db.starboard_messages.insert_one({
                "guild_id": str(original_msg.guild.id),
                "original_message_id": str(original_msg.id),
                "starboard_message_id": str(starboard_msg.id),
                "author_id": str(original_msg.author.id),
                "channel_id": str(original_msg.channel.id),
                "content": original_msg.content,
                "attachments": [att.url for att in original_msg.attachments],
                "embed": original_msg.embeds[0].to_dict() if original_msg.embeds else None,
                "star_count": star_count,
                "starred_at": datetime.utcnow(),
                "last_updated": datetime.utcnow()
            })
        except Exception as e:
            print(f"Error adding starboard message to DB: {e}")

    async def update_starboard_message_in_db(self, message, starboard_data, star_count=None):
        """Update starboard message in database"""
        try:
            update_data = {
                "content": message.content,
                "attachments": [att.url for att in message.attachments],
                "embed": message.embeds[0].to_dict() if message.embeds else None,
                "last_updated": datetime.utcnow()
            }
            
            if star_count is not None:
                update_data["star_count"] = star_count
            
            self.mongo_db.starboard_messages.update_one(
                {
                    "guild_id": str(message.guild.id),
                    "original_message_id": str(message.id)
                },
                {"$set": update_data}
            )
        except Exception as e:
            print(f"Error updating starboard message in DB: {e}")

    # New Commands
    @app_commands.command(name="starboard", description="Starboard management commands")
    @app_commands.describe(
        action="Action to perform (info, stats, top, remove, purge)",
        message_id="Message ID for remove action"
    )
    async def starboard_command(self, interaction: discord.Interaction, action: str, message_id: str = None):
        """Main starboard command"""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        # Check permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer()

        if action == "info":
            await self.starboard_info(interaction)
        elif action == "stats":
            await self.starboard_stats(interaction)
        elif action == "top":
            await self.starboard_top(interaction)
        elif action == "remove" and message_id:
            await self.starboard_remove(interaction, message_id)
        elif action == "purge":
            await self.starboard_purge(interaction)
        else:
            await interaction.followup.send("Invalid action. Use: info, stats, top, remove, purge", ephemeral=True)

    async def starboard_info(self, interaction: discord.Interaction):
        """Show starboard information"""
        starboard_data = self.mongo_db.starboard.find_one({"guild_id": str(interaction.guild.id)})
        
        if not starboard_data or not starboard_data.get("enabled", False):
            embed = create_embed("Starboard Info", "Starboard is not enabled in this server.", "info")
            await interaction.followup.send(embed=embed)
            return

        channel = self.bot.get_channel(int(starboard_data["channel_id"]))
        embed = create_embed(
            "Starboard Information",
            f"**Channel:** {channel.mention if channel else 'Unknown'}\n"
            f"**Threshold:** {starboard_data['threshold']} {starboard_data['emoji']}\n"
            f"**Emoji:** {starboard_data['emoji']}\n"
            f"**Ignore Bots:** {'Yes' if starboard_data.get('bots_can_star', False) else 'No'}\n"
            f"**Self Star:** {'Yes' if starboard_data.get('self_star', False) else 'No'}\n"
            f"**Ignored Channels:** {len(starboard_data.get('ignored_channels', []))}\n"
            f"**Ignored Roles:** {len(starboard_data.get('ignored_roles', []))}",
            "info"
        )
        
        await interaction.followup.send(embed=embed)

    async def starboard_stats(self, interaction: discord.Interaction):
        """Show starboard statistics"""
        # Get stats from database
        total_messages = self.mongo_db.starboard_messages.count_documents({"guild_id": str(interaction.guild.id)})
        total_stars = self.mongo_db.starboard_messages.aggregate([
            {"$match": {"guild_id": str(interaction.guild.id)}},
            {"$group": {"_id": None, "total": {"$sum": "$star_count"}}}
        ]).next().get("total", 0) if total_messages > 0 else 0

        # Get top user
        top_user_pipeline = [
            {"$match": {"guild_id": str(interaction.guild.id)}},
            {"$group": {"_id": "$author_id", "total_stars": {"$sum": "$star_count"}}},
            {"$sort": {"total_stars": -1}},
            {"$limit": 1}
        ]
        top_user_result = list(self.mongo_db.starboard_messages.aggregate(top_user_pipeline))
        top_user_id = top_user_result[0]["_id"] if top_user_result else None

        embed = create_embed(
            "Starboard Statistics",
            f"**Total Starred Messages:** {total_messages}\n"
            f"**Total Stars Given:** {total_stars}\n"
            f"**Average Stars/Message:** {total_stars/total_messages:.1f}" if total_messages > 0 else "0",
            "info"
        )

        if top_user_id:
            try:
                top_user = await interaction.guild.fetch_member(int(top_user_id))
                embed.add_field(name="Most Starred User", value=top_user.mention, inline=True)
            except:
                embed.add_field(name="Most Starred User", value=f"<@{top_user_id}>", inline=True)

        await interaction.followup.send(embed=embed)

    async def starboard_top(self, interaction: discord.Interaction):
        """Show top starred messages"""
        top_messages = list(self.mongo_db.starboard_messages.find(
            {"guild_id": str(interaction.guild.id)}
        ).sort("star_count", -1).limit(5))

        if not top_messages:
            embed = create_embed("Top Starred Messages", "No starred messages found.", "info")
            await interaction.followup.send(embed=embed)
            return

        embed = create_embed("Top Starred Messages", "", "info")
        
        for i, msg in enumerate(top_messages, 1):
            content = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
            embed.add_field(
                name=f"#{i} - {msg['star_count']} ⭐",
                value=f"{content}\n[Jump to Message](https://discord.com/channels/{interaction.guild.id}/{msg['channel_id']}/{msg['original_message_id']})",
                inline=False
            )

        await interaction.followup.send(embed=embed)

    async def starboard_remove(self, interaction: discord.Interaction, message_id: str):
        """Remove a message from starboard"""
        starboard_data = self.mongo_db.starboard.find_one({"guild_id": str(interaction.guild.id)})
        if not starboard_data:
            await interaction.followup.send("Starboard is not enabled in this server.", ephemeral=True)
            return

        # Remove from starboard
        await self.remove_starboard_message_by_id(interaction.guild, message_id, starboard_data)
        await interaction.followup.send(f"Message {message_id} has been removed from starboard.", ephemeral=True)

    async def starboard_purge(self, interaction: discord.Interaction):
        """Purge old starboard messages"""
        # Remove messages older than 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        old_messages = list(self.mongo_db.starboard_messages.find({
            "guild_id": str(interaction.guild.id),
            "starred_at": {"$lt": cutoff_date}
        }))

        if not old_messages:
            await interaction.followup.send("No old messages to purge.", ephemeral=True)
            return

        # Remove from starboard channel
        starboard_data = self.mongo_db.starboard.find_one({"guild_id": str(interaction.guild.id)})
        if starboard_data:
            starboard_channel = self.bot.get_channel(int(starboard_data["channel_id"]))
            if starboard_channel:
                for msg in old_messages:
                    try:
                        starboard_msg = await starboard_channel.fetch_message(msg["starboard_message_id"])
                        await starboard_msg.delete()
                    except:
                        pass

        # Remove from database
        self.mongo_db.starboard_messages.delete_many({
            "guild_id": str(interaction.guild.id),
            "starred_at": {"$lt": cutoff_date}
        })

        await interaction.followup.send(f"Purged {len(old_messages)} old starboard messages.", ephemeral=True)

    async def remove_starboard_message_by_id(self, guild, message_id: str, starboard_data):
        """Remove starboard message by ID"""
        try:
            starboard_msg_id = starboard_data.get("messages", {}).get(message_id)
            if starboard_msg_id:
                starboard_channel = self.bot.get_channel(int(starboard_data["channel_id"]))
                starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                await starboard_msg.delete()
                
                del starboard_data["messages"][message_id]
                self.mongo_db.starboard.update_one(
                    {"guild_id": str(guild.id)},
                    {"$set": starboard_data}
                )

            # Remove from starboard_messages collection
            self.mongo_db.starboard_messages.delete_one({
                "guild_id": str(guild.id),
                "original_message_id": message_id
            })
        except Exception as e:
            print(f"Error removing starboard message by ID: {e}")

async def setup(bot):
    await bot.add_cog(Starboard(bot))