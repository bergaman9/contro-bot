import io
import os
import shutil
from io import BytesIO

import aiohttp
import discord
import requests
from PIL import Image
from discord import app_commands
from discord.ext import commands

from utility.class_utils import Paginator
from utility.utils import create_embed, initialize_mongodb, generate_members_of_role_embeds


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
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

    @commands.hybrid_command(name="advertisements", description="Prints all custom activities that are discord invites")
    @commands.has_permissions(manage_guild=True)
    async def advertisements(self, ctx):
        guild = ctx.guild
        found_advertisements = False
        for member in guild.members:
            for activity in member.activities:
                if activity.type == discord.ActivityType.custom:
                    message = activity.name
                    if message and message.startswith(("https://", "http://", "www.", "discord.gg/")):
                        await ctx.send(embed=create_embed(
                            description=f"{member.mention} is advertising with the custom status '{message}'.",
                            color=discord.Color.red()))
                        found_advertisements = True  # Reklam bulundu, bayrağı True yap

        if not found_advertisements:  # Eğer hiç reklam bulunamadıysa
            await ctx.send(
                embed=create_embed(description="No advertisements found in the server.", color=discord.Color.green()))

    @commands.hybrid_command(name="set_status_role",
                             description="Sets the custom status and role for the status_role command.")
    @commands.has_permissions(manage_guild=True)
    async def set_status_role(self, ctx, custom_status: str, role: discord.Role):
        # Get the status_roles collection from the database

        cleaned_custom_status = [item.strip() for item in custom_status.split(",")]

        collection = self.mongo_db["status_roles"]
        # Update or insert the document that matches the guild id
        collection.update_one({"guild_id": ctx.guild.id},
                              {"$set": {"custom_status": cleaned_custom_status, "role_id": role.id}}, upsert=True)
        await ctx.send(f"Status role set to {role.mention} for custom status '{custom_status}'.")

    @commands.hybrid_command(name="reset_nicknames", description="Resets everyone's nickname.")
    @commands.has_permissions(manage_guild=True)
    async def reset_nicknames(self, ctx):
        async for member in ctx.guild.fetch_members(limit=5000):
            if member.nick:
                await member.edit(nick=None)
                await ctx.send(f"{member.mention}'s nickname has been reset.")
        await ctx.send("All nicknames have been reset.")

    @app_commands.command(name="mass_unban", description="Mass unban people banned from the server.")
    @commands.has_permissions(manage_guild=True)
    async def mass_unban(self, interaction):
        async for entry in interaction.guild.bans(limit=None):
            await interaction.guild.unban(entry.user)

        await interaction.response.send_message("All banned members from the server unbanned.", ephemeral=True)

    @commands.hybrid_command(name="give_everyone", description="gives everyone a role.")
    @commands.has_permissions(manage_guild=True)
    async def give_everyone(self, ctx, role: discord.Role):
        await ctx.defer()
        for member in ctx.guild.members:
            if not member.bot:
                await member.add_roles(role)
        await ctx.send(f"{role.mention} role has been given to everyone.")

    @commands.hybrid_command(name="membersofrole")
    async def members_of_role(self, ctx, role: discord.Role):
        members_with_role = [member for member in ctx.guild.members if role in member.roles]

        if not members_with_role:
            await ctx.send(f"Hiçbir kullanıcının {role.name} rolü yok.")
            return

        embeds = generate_members_of_role_embeds(members_with_role, role)
        paginator = Paginator(embed_list=embeds)
        await paginator.send_initial_message(ctx)

    @commands.command(name="download_emojis", description="Fetch emojis of the server.")
    @commands.has_permissions(manage_messages=True)
    async def download_emojis(self, interaction):

        # defer response
        await interaction.response.defer()

        # mkdir images
        if not os.path.exists("images"):
            os.mkdir("images")

        # download emojis
        emojis = await interaction.guild.fetch_emojis()
        for emoji in emojis:
            response = requests.get(emoji.url)
            img = Image.open(BytesIO(response.content))
            img.save(f"images/{emoji.name}.png")

        # zip folder
        shutil.make_archive(f"{interaction.guild.name} emojis", "zip", "images")
        shutil.rmtree("images")

        # send file
        await interaction.followup.send(file=discord.File(f"{interaction.guild.name} emojis.zip"))
        os.remove(f"{interaction.guild.name} emojis.zip")

        # remove images folder
        if os.path.exists("images"):
            shutil.rmtree("images")

    @commands.hybrid_command(name="emoji_list", description="Fetch emojis of the server.")
    async def emoji_list(self, ctx):
        emojis = await ctx.guild.fetch_emojis()
        static_emojis = [f"<:{emoji.name}:{emoji.id}>" for emoji in emojis if not emoji.animated]
        animated_emojis = [f"<a:{emoji.name}:{emoji.id}>" for emoji in emojis if emoji.animated]

        # Sayfa başına kaç emoji gösterilecek
        emojis_per_page = 50

        # Embed'leri oluşturma
        def create_embed_pages(emojis_list, title):
            pages = []
            for i in range(0, len(emojis_list), emojis_per_page):
                chunk = emojis_list[i:i + emojis_per_page]
                embed = discord.Embed(title=title, description=" ".join(chunk), color=discord.Color.blurple())
                embed.set_thumbnail(url=ctx.guild.icon.url)
                pages.append(embed)
            return pages

        static_embeds = create_embed_pages(static_emojis, "Server Static Emojis")
        animated_embeds = create_embed_pages(animated_emojis, "Server Animated Emojis")

        # İlk olarak statik emoji listesini gönderelim
        if len(static_embeds) > 0:
            static_paginator = Paginator(static_embeds)
            await static_paginator.send_initial_message(ctx)
        else:
            await ctx.send(embed=create_embed(description="No static emojis found.", color=discord.Color.red()))

        # Sonrasında animasyonlu emoji listesini gönderelim
        if len(animated_embeds) > 0:
            animated_paginator = Paginator(animated_embeds)
            await animated_paginator.send_initial_message(ctx)
        else:
            await ctx.send(embed=create_embed(description="No animated emojis found.", color=discord.Color.red()))

    @commands.hybrid_command(name="poll", description="Creates a poll.")
    async def poll(self, ctx, question: str, option1: str, option2: str, option3: str = None, option4: str = None,
                   option5: str = None, option6: str = None, option7: str = None, option8: str = None,
                   option9: str = None, option10: str = None):

        emoji_list = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        # Gather all the options into a list and filter out None values
        options = [opt for opt in
                   [option1, option2, option3, option4, option5, option6, option7, option8, option9, option10] if
                   opt is not None]

        # Create the embed
        embed_description = "\n".join(f"{emoji_list[idx]} {option}" for idx, option in enumerate(options))
        embed = discord.Embed(title=question, description=embed_description, color=ctx.author.color)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)

        # Send the embed
        message = await ctx.send(embed=embed)

        # Add the reactions
        for emoji in emoji_list[:len(options)]:
            await message.add_reaction(emoji)

    @commands.hybrid_command(name="whois", description="Shows member info.")
    async def whois(self, ctx, member: discord.Member = None):
        if not member:
            member = ctx.author

        embed = discord.Embed(title=member.name, description=member.mention, color=discord.Colour.blue())
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Joined at", value=member.joined_at.strftime("%a, %d %B %Y, %I:%M  UTC"))
        embed.add_field(name="Joined Server On:", value=(member.joined_at.strftime("%a, %d %B %Y, %I:%M %p UTC")))
        embed.add_field(name="Highest Role:", value=member.top_role.mention)
        embed.add_field(name="Voice:", value=member.voice)
        embed.set_thumbnail(url=member.display_avatar)
        embed.set_footer(icon_url=ctx.author.display_avatar, text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", description="Shows member avatar.")
    async def avatar(self, ctx, *, member: discord.Member = None):
        if not member:
            member = ctx.author
        userAvatar = member.display_avatar
        embed = discord.Embed(title=f"{member.name}'s Avatar", description="", color=0xffff00)
        embed.set_image(url=userAvatar.url)
        embed.set_footer(icon_url=ctx.author.display_avatar, text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="server_info", description="Shows server info.")
    async def server_info(self, ctx):
        embed = discord.Embed(
            title=ctx.guild.name + " Server Information",
            description=ctx.guild.description,
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.add_field(name="Server ID", value=ctx.guild.id, inline=True)
        embed.add_field(name="Owner", value=ctx.guild.owner, inline=True)
        embed.add_field(name="Created at", value=ctx.guild.created_at.strftime("%a, %d %B %Y, %I:%M %p UTC"),
                        inline=True)
        embed.add_field(name="Members", value=ctx.guild.member_count, inline=True)
        embed.add_field(name="Roles", value=len(ctx.guild.roles), inline=True)
        embed.add_field(name="Emojis", value=len(ctx.guild.emojis), inline=True)
        embed.add_field(name="Text Channels", value=len(ctx.guild.text_channels), inline=True)
        embed.add_field(name="Voice Channels", value=len(ctx.guild.voice_channels), inline=True)
        embed.add_field(name="Boosts", value=ctx.guild.premium_subscription_count, inline=True)
        await ctx.send(embed=embed)



    @app_commands.command(name="embed", description="Creates embed message.")
    @app_commands.describe(color="Color of embed message.")
    @commands.has_permissions(manage_messages=True)
    async def embed(self, interaction, *, color: str = "ff0000", image_url: str = None, title: str, description: str):
        embed = discord.Embed(title=title, description=description, colour=int(color, base=16))
        if image_url:
            embed.set_image(url=image_url)
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("Embed is created!", ephemeral=True)

    @app_commands.command(name="link_button", description="Creates link button.")
    async def link_button(self, interaction, title: str, description: str, button_label: str, button_url: str,
                          emoji: str = None, button_label2: str = None, button_url2: str = None, emoji2: str = None,
                          button_label3: str = None, button_url3: str = None, emoji3: str = None,
                          button_label4: str = None, button_url4: str = None, emoji4: str = None,
                          button_label5: str = None, button_url5: str = None, emoji5: str = None,
                          color: str = "ff0000"):
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(label=button_label, url=button_url, style=discord.ButtonStyle.link, emoji=emoji))
        if button_label2 and button_url2:
            view.add_item(
                discord.ui.Button(label=button_label2, url=button_url2, style=discord.ButtonStyle.link, emoji=emoji2))
        if button_label3 and button_url3:
            view.add_item(
                discord.ui.Button(label=button_label3, url=button_url3, style=discord.ButtonStyle.link, emoji=emoji3))
        if button_label4 and button_url4:
            view.add_item(
                discord.ui.Button(label=button_label4, url=button_url4, style=discord.ButtonStyle.link, emoji=emoji4))
        if button_label5 and button_url5:
            view.add_item(
                discord.ui.Button(label=button_label5, url=button_url5, style=discord.ButtonStyle.link, emoji=emoji5))

        await interaction.channel.send(
            embed=discord.Embed(title=title, description=description, color=int(color, base=16)), view=view)
        await interaction.response.send_message(
            embed=create_embed(description="Embed with links is created!", color=discord.Color.green()), ephemeral=True)

    @commands.hybrid_command(name="emote", description="Shows emote info.")
    @commands.has_permissions(manage_messages=True)
    async def emote(self, ctx, emoji: discord.Emoji):

        if not emoji:
            return ctx.invoke(self.bot.get_command("help"), entity="emote")

        try:
            emoji = await emoji.guild.fetch_emoji(emoji.id)
        except discord.NotFound:
            return await ctx.send("I could not find this emoji in the given guild.")

        is_managed = "Yes" if emoji.managed else "No"
        is_animated = "Yes" if emoji.animated else "No"
        require_colons = "Yes" if emoji.require_colons else "No"
        creation_time = emoji.created_at.strftime("%I:%M %p, %d %B %Y")
        can_use_emoji = "Everyone" if not emoji.roles else "".join(role.name for role in emoji.roles)

        description = f"""
        **General:**
        **- Name: **{emoji.name}
        **- ID: **{emoji.id}
        **- URL: **[Link to Emoji]({emoji.url})
        **- Author: ** {emoji.user.mention}    
        **- Time Created: ** {creation_time}    
        **- Usable by: ** {can_use_emoji}    

        **Other:**
        **- Animated: ** {is_animated}
        **- Managed: ** {is_managed}
        **- Requires Colons: ** {require_colons}
        **- Guild Colons: ** {emoji.guild.name}
        **- Guild ID: ** {emoji.guild.id}
        """

        embed = discord.Embed(
            title=f"**Emoji Information for: ** `{emoji.name}`",
            description=description,
            colour=0xadd8e6)

        embed.set_thumbnail(url=emoji.url)
        await ctx.send(embed=embed)

    @commands.command(name="upload", description="Uploads a file.")
    @commands.has_permissions(manage_messages=True)
    async def upload(self, ctx):
        await ctx.send("Lütfen resmi yükleyin.")

        def check(m):
            return m.attachments and m.author == ctx.author

        message = await self.bot.wait_for("message", check=check)
        await message.attachments[0].save("resim.gif")
        with open("resim.gif", "rb") as f:
            picture = discord.File(f)
            await ctx.send(file=picture)

    @commands.hybrid_command(name="edit_nicknames", description="Edits everyone's nickname.")
    @commands.has_permissions(manage_guild=True)
    async def edit_nicknames(self, ctx, role_name: str, new_name):

        guild = ctx.guild
        role = discord.utils.get(guild.roles, name=role_name)

        if not role:
            await ctx.send(f"Rol bulunamadı: {role}")
            return

        count = 0
        for member in guild.members:
            if role in member.roles:
                try:
                    await member.edit(nick=new_name)
                    await ctx.send(f"{member.name} kullanıcısının {new_name} olarak düzenlendi.")
                    count += 1
                except discord.Forbidden:
                    await ctx.send(f"Bot, {member.mention} kullanıcısının ismini değiştiremiyor.")
                except discord.HTTPException as e:
                    await ctx.send(f"Bir hata oluştu: {e}")

        await ctx.send(f"{count} kullanıcının ismi düzenlendi.")

    @commands.hybrid_command(name="copy_emoji",
                             description="Copy an emoji from another server if the bot is a member of that server.")
    @commands.has_permissions(manage_emojis=True)
    async def copy_emoji(self, ctx, emoji: discord.Emoji):
        guild = ctx.guild
        emoji_url = emoji.url
        emoji_name = emoji.name
        async with aiohttp.ClientSession() as session:
            async with session.get(emoji_url) as resp:
                if resp.status != 200:
                    return await ctx.send(
                        embed=create_embed(description="Could not download file...", color=discord.Color.red()))
                data = io.BytesIO(await resp.read())
                await guild.create_custom_emoji(name=emoji_name, image=data.read())
                await ctx.send(embed=create_embed(description=f"Emoji {emoji} is added to the server.",
                                                  color=discord.Color.green()))


async def setup(bot):
    await bot.add_cog(Utility(bot))
