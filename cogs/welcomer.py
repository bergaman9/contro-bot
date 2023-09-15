import discord, asyncio, os, json
from ordinal import ordinal
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import requests
import pymongo

from utils import create_embed, initialize_mongodb, hex_to_int, download_background

class Welcomer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.name = "hidden"
        self.mongo_db = initialize_mongodb()

    # Round profile picture
    def circle(pfp, size=(215, 215)):
        pfp = pfp.resize(size, Image.LANCZOS).convert("RGBA")

        bigsize = (pfp.size[0] * 3, pfp.size[1] * 3)
        mask = Image.new('L', bigsize, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + bigsize, fill=255)
        mask = mask.resize(pfp.size, Image.LANCZOS)
        mask = ImageChops.darker(mask, pfp.split()[-1])
        pfp.putalpha(mask)
        return pfp


    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = str(member.guild.id)

        # Fetch the welcome configuration from MongoDB based on the guild ID
        guild_config = self.mongo_db['welcomer'].find_one({"guild_id": guild_id})
        channel_id = int(guild_config["welcome_channel_id"])
        channel = self.bot.get_channel(channel_id)
        if guild_config is None:
            # Ignore the member join event if the guild is not in the configuration.
            return

        description = guild_config["description"].format(mention=member.mention, name=member.name,
                                                         member_count=member.guild.member_count,
                                                         server=member.guild.name)
        color = guild_config["color"]
        fill_color = guild_config["fill"]
        background_url = guild_config["background_url"]
        welcome_text = guild_config["welcome_text"]

        print(welcome_text)

        if not welcome_text:
            welcome_text = "HOŞ GELDİN!"

        print(welcome_text)

        # Download the background image and get its filename
        background_filename = download_background(background_url)

        if background_filename is None:
            # If the background image couldn't be downloaded, use a default one or skip the process
            # You can add a default background image in your bot's folder named "default_background.png"
            background_filename = "welcome.png"

        # await member.add_roles(guild.get_role(ID_OF_ROLE)) # You can add a default role to new joiners if you'd like here

        filename = f"results_{member.id}.png"  # <- The name of the file that will be saved and deleted after (Should be PNG)

        with Image.open(background_filename) as background:
            background = background.resize((1024, 500))  # <- Resizes the background to fit the canvas (Can be changed

        # asset = member.avatar.with_size(1024) if member.avatar else "../genshinWizard/attributes/Avatars/default.png" # This loads the Member Avatar
        if member.avatar:
            asset = member.avatar.with_size(1024)
        else:
            asset = self.bot.user.avatar.with_size(1024)

        data = BytesIO(await asset.read())

        pfp = Image.open(data).convert("RGBA")
        pfp = Welcomer.circle(pfp)
        pfp = pfp.resize((226, 226))  # Resizes the Profilepicture so it fits perfectly in the circle
        draw = ImageDraw.Draw(background)
        welcomeFont = ImageFont.truetype("attributes/Fonts/GothamNarrow-Bold.otf", 100)
        memberFont = ImageFont.truetype("attributes/Fonts/GothamNarrow-Bold.otf", 42)
        member_text = f"{member.name}#{member.discriminator}"  # <- Text under the Profilepicture with the Membercount

        W, H = (1024, 500)  # Canvas Dimensions

        bbox = draw.textbbox((0, 295), welcome_text, font=welcomeFont)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((W - w) / 2, 295), welcome_text, font=welcomeFont, fill=fill_color)

        bbox = draw.textbbox((0, 390), member_text, font=memberFont)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((W - w) / 2, 390), member_text, font=memberFont, fill=fill_color)

        background.paste(pfp, (int((W - 226) / 2), 50), pfp)  # Pastes the Profilepicture on the Background Image
        background.save(filename)  # Saves the finished Image in the folder with the filename

        file = discord.File(filename)

        embed = discord.Embed(title=welcome_text, description=description, color=color)
        embed.set_image(url=f"attachment://{filename}")

        await channel.send(file=file, embed=embed)
        try:
            os.remove(filename)  # <- Change your path to where the Bot is located. Tries to delete the file again so your folder won't be full of Images. If it's already deleted nothing will happen
        except Exception as e:
            print(e)

    @commands.hybrid_command(name="welcomer_set", description="Set the welcome configurations for the guild.")
    @app_commands.describe(welcome_channel="The channel where the welcome message will be sent.", description="The description of the welcome message.", color="The color of the embed.", fill_color="The color of the text.", background_url="The URL of the background image.")
    @commands.has_permissions(manage_guild=True)
    async def welcomer_set(self, ctx, welcome_channel: discord.TextChannel, description: str, color: str,
                           fill_color: str, background_url: str, welcome_text = "HOŞ GELDİN!"):
        guild_id = str(ctx.guild.id)

        # Save the welcome configurations to MongoDB
        self.mongo_db['welcomer'].update_one(
            {"guild_id": guild_id},
            {
                "$set": {
                    "welcome_channel_id": str(welcome_channel.id),
                    "description": description,
                    "color": hex_to_int(color),
                    "fill": str(f"#{fill_color}"),
                    "background_url": background_url,
                    "welcome_text": welcome_text
                }
            },
            upsert=True
        )

        await ctx.send(embed=create_embed(description="Welcome configurations have been set for this guild.", color=discord.Color.green()))


    @commands.hybrid_command(name="welcomer_remove", description="Remove the welcome configurations for the guild.")
    @commands.has_permissions(manage_guild=True)
    async def welcomer_remove(self, ctx):
        guild_id = str(ctx.guild.id)

        # Delete the welcome configurations from MongoDB for the specified guild
        self.mongo_db['welcomer'].delete_one({"guild_id": guild_id})

        await ctx.send(embed=create_embed(description="Welcome configurations have been removed for this guild.", color=discord.Color.green()))


class ByeBye(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()


    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild_id = str(member.guild.id)

        # Fetch the welcome configuration from MongoDB based on the guild ID
        guild_config = self.mongo_db['byebye'].find_one({"guild_id": guild_id})
        channel_id = int(guild_config["byebye_channel_id"])
        channel = self.bot.get_channel(channel_id)
        if guild_config is None:
            # Ignore the member join event if the guild is not in the configuration.
            return

        description = guild_config["description"].format(mention=member.mention, name=member.name,
                                                         member_count=member.guild.member_count,
                                                         server=member.guild.name)
        color = guild_config["color"]
        fill_color = guild_config["fill"]
        background_url = guild_config["background_url"]

        # Download the background image and get its filename
        background_filename = download_background(background_url)

        if background_filename is None:
            # If the background image couldn't be downloaded, use a default one or skip the process
            # You can add a default background image in your bot's folder named "default_background.png"
            background_filename = "welcome.png"

        # await member.add_roles(guild.get_role(ID_OF_ROLE)) # You can add a default role to new joiners if you'd like here

        filename = f"results_{member.id}.png"  # <- The name of the file that will be saved and deleted after (Should be PNG)

        with Image.open(background_filename) as background:
            background = background.resize((1024, 500))  # <- Resizes the background to fit the canvas (Can be changed

        # asset = member.avatar.with_size(1024) if member.avatar else "../genshinWizard/attributes/Avatars/default.png" # This loads the Member Avatar
        if member.avatar:
            asset = member.avatar.with_size(1024)
        else:
            asset = self.bot.user.avatar.with_size(1024)

        data = BytesIO(await asset.read())

        pfp = Image.open(data).convert("RGBA")
        pfp = Welcomer.circle(pfp)
        pfp = pfp.resize((226, 226))  # Resizes the Profilepicture so it fits perfectly in the circle
        draw = ImageDraw.Draw(background)
        welcomeFont = ImageFont.truetype("attributes/Fonts/GothamNarrow-Bold.otf", 100)
        memberFont = ImageFont.truetype("attributes/Fonts/GothamNarrow-Bold.otf", 42)
        welcome_text = "GÜLE GÜLE!"
        member_text = f"{member.name}#{member.discriminator}"  # <- Text under the Profilepicture with the Membercount

        W, H = (1024, 500)  # Canvas Dimensions

        bbox = draw.textbbox((0, 295), welcome_text, font=welcomeFont)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((W - w) / 2, 295), welcome_text, font=welcomeFont, fill=fill_color)

        bbox = draw.textbbox((0, 390), member_text, font=memberFont)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((W - w) / 2, 390), member_text, font=memberFont, fill=fill_color)

        background.paste(pfp, (int((W - 226) / 2), 50), pfp)  # Pastes the Profilepicture on the Background Image
        background.save(filename)  # Saves the finished Image in the folder with the filename

        file = discord.File(filename)

        embed = discord.Embed(title="GÜLE GÜLE!", description=description, color=color)
        embed.set_image(url=f"attachment://{filename}")

        await channel.send(file=file, embed=embed)
        try:
            os.remove(filename)
        except Exception as e:
            print(e)

    @commands.hybrid_command(name="byebye_set", description="Set the byebye configurations for the guild.")
    @commands.has_permissions(manage_guild=True)
    async def byebye_set(self, ctx, byebye_channel: discord.TextChannel, description: str, color: str,
                           fill_color: str, background_url: str):

        guild_id = str(ctx.guild.id)

        # Save the welcome configurations to MongoDB
        self.mongo_db['byebye'].update_one(
            {"guild_id": guild_id},
            {
                "$set": {
                    "byebye_channel_id": str(byebye_channel.id),
                    "description": description,
                    "color": hex_to_int(color),
                    "fill": str(f"#{fill_color}"),
                    "background_url": background_url
                }
            },
            upsert=True
        )

        await ctx.send(embed=create_embed(description="Bye bye configurations have been set for this guild.",
                                          color=discord.Color.green()))

    @commands.hybrid_command(name="byebye_remove", description="Remove the welcome configurations for the guild.")
    @commands.has_permissions(manage_guild=True)
    async def byebye_remove(self, ctx):
        guild_id = str(ctx.guild.id)

        # Delete the welcome configurations from MongoDB for the specified guild
        self.mongo_db['byebye'].delete_one({"guild_id": guild_id})

        await ctx.send(embed=create_embed(description="Bye bye configurations have been removed for this guild.",
                                          color=discord.Color.green()))


async def setup(bot):
    await bot.add_cog(Welcomer(bot))
    await bot.add_cog(ByeBye(bot))