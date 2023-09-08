import discord
from discord.ext import commands
from discord import app_commands

import re


from utils import get_category_by_name, create_voice_channel, create_embed, initialize_mongodb, calculate_how_long_ago_member_joined, calculate_how_long_ago_member_created


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    current_streamers = list()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=create_embed("Please enter all the required arguments.", discord.Color.red()))
            await ctx.message.delete()
        elif isinstance(error, commands.NotOwner):
            await ctx.send(embed=create_embed("You do not own this bot.", discord.Color.red()))
            await ctx.message.delete()
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=create_embed("Member couldn't found.", discord.Color.red()))
            await ctx.message.delete()
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                embed=create_embed(f"Please wait {error.retry_after:.2f} seconds before using this command again.",
                                   discord.Color.red()))
            await ctx.message.delete()
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=create_embed("You can't do that :(", discord.Color.red()))
            await ctx.message.delete()
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(embed=create_embed("Bot don't have required permissions.", discord.Color.red()))
            await ctx.message.delete()
        elif isinstance(error, commands.CommandInvokeError):
            await ctx.send(embed=create_embed("Command raised an exception.", discord.Color.red()))
            await ctx.message.delete()
        else:
            await ctx.send(embed=create_embed(f"Error: {error}", discord.Color.red()))

    @commands.hybrid_command(name="logging_channel_set", description="Set the logging channel for this guild.",
                             usage="logging_channel <channel>")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(channel="The channel to set as logging channel.")
    async def logging_channel_set(self, ctx, channel: discord.TextChannel):
        guild_id = ctx.guild.id

        # Save the welcome configurations to MongoDB
        self.mongo_db['logger'].update_one(
            {"guild_id": guild_id},
            {
                "$set": {
                    "channel_id": channel.id
                }
            },
            upsert=True
        )

        await ctx.send(embed=create_embed(description="Logging configurations have been set for this guild.",
                                          color=discord.Color.green()))

    @commands.hybrid_command(name="logging_channel_remove", description="Removes the logging channel for this guild.")
    @commands.has_permissions(manage_guild=True)
    async def logging_channel_remove(self, ctx):
        guild_id = ctx.guild.id

        # Check if a logging channel exists for the guild
        logging_channel = self.mongo_db['logger'].find_one({"guild_id": guild_id})
        if logging_channel:
            # Delete the logging configurations from MongoDB
            self.mongo_db['logger'].delete_one({"guild_id": guild_id})

            await ctx.send(embed=create_embed(description="Logging configurations have been removed for this guild.",
                                              color=discord.Color.green()))
        else:
            await ctx.send(embed=create_embed(description="No logging configurations found for this guild.",
                                              color=discord.Color.red()))

    # MEMBERS
    @commands.Cog.listener()
    @commands.Cog.listener()
    async def on_member_join(self, member):
        result = self.mongo_db['logger'].find_one({"guild_id": member.guild.id})
        if result is None:
            return

        channel = member.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        created_ago = calculate_how_long_ago_member_created(member)
        embed = discord.Embed(title="Member joined",
                              description=f"{member.mention} joined \n We are now {len(member.guild.members)} members \nThe account is created `{created_ago}`",
                              color=discord.Color.green())
        embed.set_author(name=f"{member.name}#{member.discriminator}", icon_url=member.avatar.url)
        embed.set_thumbnail(url=member.avatar.url)
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        result = self.mongo_db['logger'].find_one({"guild_id": member.guild.id})
        if result is None:
            return

        channel = member.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        time_ago = calculate_how_long_ago_member_joined(member)
        embed = discord.Embed(title="Member left",
                              description=f"{member.mention} joined `{time_ago}` \nWe are now {len(member.guild.members)} members \n**Roles:** {', '.join([role.mention for role in member.roles if role.name != '@everyone'])}",
                              color=discord.Color.red())
        embed.set_author(name=f"{member.name}#{member.discriminator}", icon_url=member.avatar.url)
        embed.set_thumbnail(url=member.avatar.url)
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.display_name != after.display_name:
            result = self.mongo_db['logger'].find_one({"guild_id": before.guild.id})
            if result is None:
                return

            channel = before.guild.get_channel(result['channel_id'])
            if channel is None:
                return

            embed = discord.Embed(title="Name change", color=after.color)
            embed.set_author(name=f"{after.name}#{after.discriminator}", icon_url=after.avatar.url)
            embed.set_thumbnail(url=after.avatar.url)
            embed.add_field(name="Before", value=before.display_name, inline=False)
            embed.add_field(name="After", value=after.display_name, inline=False)
            embed.set_footer(text=f"ID: {after.id}")
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if before.name != after.name:
            result = self.mongo_db['logger'].find_one({"guild_id": before.guild.id})
            if result is None:
                return

            channel = before.guild.get_channel(result['channel_id'])
            if channel is None:
                return

            embed = discord.Embed(title="Name change", color=after.color)
            embed.set_author(name=f"{after.name}#{after.discriminator}", icon_url=after.avatar.url)
            embed.set_thumbnail(url=after.avatar.url)
            embed.add_field(name="Before", value=before.name, inline=False)
            embed.add_field(name="After", value=after.name, inline=False)
            embed.set_footer(text=f"ID: {after.id}")
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not before.bot and before.premium_since is None and after.premium_since is not None:
            result = self.mongo_db['logger'].find_one({"guild_id": before.guild.id})
            if result is None:
                return

            channel = before.guild.get_channel(result['channel_id'])
            if channel is None:
                return

            embed = discord.Embed(title="Server Boosted",
                                  description=f"{after.name}#{after.discriminator} has boosted the server!",
                                  color=discord.Color.gold())
            embed.set_author(name=f"{after.name}#{after.discriminator}", icon_url=after.avatar.url)
            embed.set_footer(text=f"User ID: {after.id}")
            await channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        result = self.mongo_db['logger'].find_one({"guild_id": guild.id})
        if result is None:
            return

        channel = guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Member banned", description=f"{user.name}#{user.discriminator}", color=discord.Color.red())
        embed.set_thumbnail(url=user.avatar.url)
        embed.set_footer(text=f"ID: {user.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        # Get the status_roles collection from the database
        collection = self.mongo_db["status_roles"]
        # Find the document that matches the guild id
        document = collection.find_one({"guild_id": after.guild.id})
        if document is not None:
            # Get the custom status and role name from the document
            custom_status = document["custom_status"]
            role_id = document["role_id"]
            role = discord.utils.get(after.guild.roles, id=role_id)
            if role is not None:
                if after.activity is not None and after.activity.type == discord.ActivityType.custom:
                    message = after.activity.name
                    if message in custom_status:
                        if role not in after.roles:
                            await after.add_roles(role)
                    else:
                        if role in after.roles:
                            await after.remove_roles(role)
                else:
                    if role in after.roles:
                        await after.remove_roles(role)

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if after.activity is not None and after.activity.type == discord.ActivityType.custom:
            message = after.activity.name
            if message.startswith(("https://", "http://", "www.", "discord.gg/")):
                result = self.mongo_db['logger'].find_one({"guild_id": after.guild.id})
                if result is None:
                    return
                channel = after.guild.get_channel(result['channel_id'])
                embed = discord.Embed(title="Custom status advertising", description=f"{after.mention} is advertising in their custom status: {message}", color=discord.Color.red())
                await channel.send(embed=embed)



    # MESSAGES
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.attachments:
            for attachment in message.attachments:
                if attachment.filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    result = self.mongo_db['logger'].find_one({"guild_id": message.guild.id})
                    if result:
                        channel = message.guild.get_channel(result['channel_id'])
                        if channel:
                            embed = discord.Embed(title="Image sent",
                                                  description=f"{message.author.name} sent an image in {message.channel.mention}. \n[Jump to message]({message.jump_url})",
                                                  color=discord.Color.green())
                            embed.set_image(url=attachment.url)
                            await channel.send(embed=embed)
                elif attachment.filename.endswith(('.pdf', '.docx', '.txt', '.zip')):
                    # Farklı dosya türleri için yeni bir log
                    result = self.mongo_db['logger'].find_one({"guild_id": message.guild.id})
                    if result:
                        channel = message.guild.get_channel(result['channel_id'])
                        if channel:
                            embed = discord.Embed(title="File sent",
                                                  description=f"{message.author.name} sent a file in {message.channel.mention}. \n[Jump to message]({message.jump_url})",
                                                  color=discord.Color.blue())
                            embed.add_field(name="File Name", value=attachment.filename)
                            await channel.send(embed=embed)

                elif attachment.filename.endswith(('.mp4', '.avi', '.mkv', '.webm')):
                    # Video dosyaları için yeni bir log
                    result = self.mongo_db['logger'].find_one({"guild_id": message.guild.id})
                    if result:
                        channel = message.guild.get_channel(result['channel_id'])
                        if channel:
                            embed = discord.Embed(title="Video sent",
                                                  description=f"{message.author.name} sent a video in {message.channel.mention}. \n[Jump to message]({message.jump_url})",
                                                  color=discord.Color.purple())
                            embed.add_field(name="Video Name", value=attachment.filename)
                            await channel.send(embed=embed)

        emoji_pattern = re.compile(r"<:\w+:\d+>")
        emojis = emoji_pattern.findall(message.content)
        if emojis:
            result = self.mongo_db['logger'].find_one({"guild_id": message.guild.id})
            if result:
                channel = message.guild.get_channel(result['channel_id'])
                if channel:
                    embed = discord.Embed(title="Emojis used",
                                          description=f"{message.author.name} used emojis in their message. \n[Jump to message]({message.jump_url})",
                                          color=discord.Color.gold())
                    embed.add_field(name="Emojis", value=" ".join(emojis))
                    await channel.send(embed=embed)

        # Bağlantıları algılamak için bir regex paterni oluşturuyoruz.
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        urls = url_pattern.findall(message.content)

        if urls:
            result = self.mongo_db['logger'].find_one({"guild_id": message.guild.id})
            if result:
                channel = message.guild.get_channel(result['channel_id'])
                if channel:
                    embed = discord.Embed(title="URLs used",
                                          description=f"{message.author.name} shared a URL in {message.channel.mention}. \n[Jump to message]({message.jump_url})",
                                          color=discord.Color.orange())
                    embed.add_field(name="URLs", value="\n".join(urls))
                    await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not after.author.bot:
            if before.content != after.content:
                result = self.mongo_db['logger'].find_one({"guild_id": before.guild.id})
                if result is None:
                    return

                channel = before.guild.get_channel(result['channel_id'])
                if channel is None:
                    return

                embed = discord.Embed(description=f"### [Message edited in {after.channel.name}]({after.jump_url}) \n**Before:** {before.content} \n**After:** {after.content}", color=discord.Color.blue())
                embed.set_author(name=f"{after.author.name}#{after.author.discriminator}",
                                 icon_url=after.author.avatar.url)
                embed.set_footer(text=f"ID: {after.author.id}")
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.author.bot:
            result = self.mongo_db['logger'].find_one({"guild_id": message.guild.id})
            if result is None:
                return

            channel = message.guild.get_channel(result['channel_id'])
            if channel is None:
                return
            embed = discord.Embed(title=f"Message deleted in #{message.channel}", description=message.content, color=discord.Color.red())
            embed.set_author(name=f"{message.author.name}#{message.author.discriminator}",
                             icon_url=message.author.avatar.url)
            embed.set_footer(text=f"ID: {message.author.id}")
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if not messages[0].author.bot:
            result = self.mongo_db['logger'].find_one({"guild_id": messages[0].guild.id})
            if result is None:
                return

            channel = messages[0].guild.get_channel(result['channel_id'])
            if channel is None:
                return

            embed = discord.Embed(title=f"{len(messages)} messages deleted in #{messages[0].channel}", color=discord.Color.red())

            embed.set_author(name=f"{messages[0].author.name}#{messages[0].author.discriminator}",
                             icon_url=messages[0].author.avatar.url)
            embed.set_footer(text=f"ID: {messages[0].author.id}")
            await channel.send(embed=embed)

    # GUILDS
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        embed = discord.Embed(title="Joined a guild", description=f"Joined {guild.name} with {guild.member_count} members.", color=discord.Color.green())
        embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"ID: {guild.id}")
        await self.bot.get_channel(830792272958193684).send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        embed = discord.Embed(title="Left a guild", description=f"Left {guild.name} with {guild.member_count} members.", color=discord.Color.red())
        embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"ID: {guild.id}")
        await self.bot.get_channel(830792272958193684).send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.name != after.name:
            embed = discord.Embed(title="Guild name changed", description=f"{before.name} -> {after.name}", color=discord.Color.blue())
            embed.set_thumbnail(url=after.icon.url)
            embed.set_footer(text=f"ID: {after.id}")
            await self.bot.get_channel(830792272958193684).send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        result = self.mongo_db['logger'].find_one({"guild_id": channel.guild.id})
        if result is None:
            return

        channel = channel.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Channel created", description=f"{channel.mention}", color=discord.Color.green())
        embed.set_footer(text=f"ID: {channel.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        result = self.mongo_db['logger'].find_one({"guild_id": channel.guild.id})
        if result is None:
            return

        channel = channel.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Channel deleted", description=f"{channel.mention}", color=discord.Color.red())
        embed.set_footer(text=f"ID: {channel.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        result = self.mongo_db['logger'].find_one({"guild_id": before.guild.id})
        if result is None:
            return

        channel = before.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Channel updated", description=f"**Before:** {before.name} \n**After:** {after.name}", color=discord.Color.blue())
        embed.set_footer(text=f"ID: {before.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        result = self.mongo_db['logger'].find_one({"guild_id": role.guild.id})
        if result is None:
            return

        channel = role.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Role created", description=f"{role.mention}", color=discord.Color.green())
        embed.set_footer(text=f"ID: {role.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        result = self.mongo_db['logger'].find_one({"guild_id": role.guild.id})
        if result is None:
            return

        channel = role.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Role deleted", description=f"{role.mention}", color=discord.Color.red())
        embed.set_footer(text=f"ID: {role.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        result = self.mongo_db['logger'].find_one({"guild_id": before.guild.id})
        if result is None:
            return

        channel = before.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Role updated", description=f"{before.mention}", color=discord.Color.blue())
        embed.set_footer(text=f"ID: {before.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        result = self.mongo_db['logger'].find_one({"guild_id": before.guild.id})
        if result is None:
            return

        channel = before.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Guild updated", description=f"{before.name}", color=discord.Color.blue())
        embed.set_footer(text=f"ID: {before.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        result = self.mongo_db['logger'].find_one({"guild_id": guild.id})
        if result is None:
            return

        channel = guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Emojis updated", description=f"{guild.name}", color=discord.Color.blue())
        embed.set_footer(text=f"ID: {guild.id}")
        await channel.send(embed=embed)

    # @commands.Cog.listener()
    # async def on_audit_log_entry_create(self, entry):
    #     result = self.mongo_db['logger'].find_one({"guild_id": entry.guild.id})
    #     if result is None:
    #         return
    #
    #     channel = entry.guild.get_channel(result['channel_id'])
    #     if channel is None:
    #         return
    #
    #     embed = discord.Embed(title="Audit log entry created", description=f"{entry.user.mention}", color=discord.Color.green())
    #     embed.set_footer(text=f"ID: {entry.user.id}")
    #     await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        result = self.mongo_db['logger'].find_one({"guild_id": invite.guild.id})
        if result is None:
            return

        channel = invite.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Invite created", description=f"{invite.url}", color=discord.Color.green())
        embed.add_field(name="Channel", value=invite.channel.mention, inline=True)
        embed.add_field(name="Creator", value=invite.inviter.mention, inline=True)
        embed.set_footer(text=f"ID: {invite.inviter.id}")
        await channel.send(embed=embed)

    # REACTIONS
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if not user.bot:
            result = self.mongo_db['logger'].find_one({"guild_id": reaction.message.guild.id})
            if result is None:
                return

            channel = reaction.message.guild.get_channel(result['channel_id'])
            if channel is None:
                return

            embed = discord.Embed(title="Reaction added", description=f"{reaction.emoji} | {reaction.message.jump_url}", color=discord.Color.green())
            embed.set_author(name=f"{user.name}#{user.discriminator}", icon_url=user.avatar.url)
            embed.set_footer(text=f"ID: {user.id}")
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if not user.bot:
            result = self.mongo_db['logger'].find_one({"guild_id": reaction.message.guild.id})
            if result is None:
                return

            channel = reaction.message.guild.get_channel(result['channel_id'])
            if channel is None:
                return

            embed = discord.Embed(title="Reaction removed", description=f"{reaction.emoji} | {reaction.message.jump_url}", color=discord.Color.red())
            embed.set_author(name=f"{user.name}#{user.discriminator}", icon_url=user.avatar.url)
            embed.set_footer(text=f"ID: {user.id}")
            await channel.send(embed=embed)

    # ROLES
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        result = self.mongo_db['logger'].find_one({"guild_id": role.guild.id})
        if result is None:
            return

        channel = role.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Role created", description=f"{role.mention}", color=discord.Color.green())
        embed.set_footer(text=f"ID: {role.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        result = self.mongo_db['logger'].find_one({"guild_id": role.guild.id})
        if result is None:
            return

        channel = role.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Role deleted", description=f"{role.name}", color=discord.Color.red())
        embed.set_footer(text=f"ID: {role.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        result = self.mongo_db['logger'].find_one({"guild_id": before.guild.id})
        if result is None:
            return

        channel = before.guild.get_channel(result['channel_id'])
        if channel is None:
            return

        embed = discord.Embed(title="Role updated", description=f"{before.mention}", color=discord.Color.blue())
        embed.set_footer(text=f"ID: {before.id}")
        await channel.send(embed=embed)

    # VOICES
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        result = self.mongo_db['logger'].find_one({"guild_id": member.guild.id})
        if result is None:
            return

        logging_channel = member.guild.get_channel(result['channel_id'])

        if member.bot:
            return
        if not before.channel:
            embed = discord.Embed(title="Member joined voice channel",
                                  description=f"{member.name} joined {after.channel.mention}",
                                  color=discord.Color.green())
            # Üyenin katıldığı kanaldaki diğer üyeleri al
            other_members = [m.mention for m in after.channel.members]
            # Üyelerin isimlerini birleştir
            other_members_str = ", ".join(other_members)
            if other_members:
                embed.add_field(name="Members in the channel", value=other_members_str, inline=False)
            await logging_channel.send(embed=embed)

        if before.channel and not after.channel:
            embed = discord.Embed(title="Member left voice channel",
                                  description=f"{member.name} left {before.channel.mention}", color=discord.Color.red())
            # Üyenin ayrıldığı kanaldaki diğer üyeleri al
            other_members = [m.mention for m in before.channel.members]
            # Üyelerin isimlerini birleştir
            other_members_str = ", ".join(other_members)
            if other_members:
                embed.add_field(name="Members in the channel", value=other_members_str, inline=False)
            await logging_channel.send(embed=embed)

        if before.channel and after.channel:
            if before.channel.id != after.channel.id:
                embed = discord.Embed(title="Member switched voice channel",
                                      description=f"{member.name} switched from {before.channel.mention} to {after.channel.mention}",
                                      color=discord.Color.blue())
                # Üyenin ayrıldığı kanaldaki diğer üyeleri al
                before_members = [m.mention for m in before.channel.members]
                before_members_str = ", ".join(before_members)
                # Üyenin katıldığı kanaldaki diğer üyeleri al
                after_members = [m.mention for m in after.channel.members]
                after_members_str = ", ".join(after_members)
                embed.add_field(name="Members in the channel before", value=before_members_str, inline=True)
                embed.add_field(name="Members in the channel after", value=after_members_str, inline=True)
                await logging_channel.send(embed=embed)
            else:
                if member.voice.self_stream:
                    invite = await after.channel.create_invite(reason=f"For joining {member.name}'s stream")
                    embed = discord.Embed(title="Member started streaming",
                                          description=f"{member.name} started streaming in {after.channel.mention}",
                                          color=discord.Color.blue())
                    if invite:
                        embed.add_field(name="Stream URL", value=invite.url, inline=True)
                    await logging_channel.send(embed=embed)
                    self.current_streamers.append(member.id)
                elif member.voice.self_mute:
                    embed = discord.Embed(title="User muted",
                                          description=f"{member.name} muted themselves in {after.channel.mention}",
                                          color=discord.Color.blue())
                    await logging_channel.send(embed=embed)
                elif member.voice.self_deaf:
                    embed = discord.Embed(title="User deafened",
                                          description=f"{member.name} deafened themselves in {after.channel.mention}",
                                          color=discord.Color.blue())
                    await logging_channel.send(embed=embed)
                else:
                    for streamer in self.current_streamers:
                        if member.id == streamer:
                            if not member.voice.self_stream:
                                embed = discord.Embed(title="Member stopped streaming",
                                                      description=f"{member.name} stopped streaming in {after.channel.mention}",
                                                      color=discord.Color.blue())
                                await logging_channel.send(embed=embed)
                                self.current_streamers.remove(member.id)
                            break


async def setup(bot):
    await bot.add_cog(Events(bot))