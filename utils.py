import discord
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
import os, re
import dotenv
import requests
from PIL import Image, ImageChops, ImageDraw

dotenv.load_dotenv()
MONGO_DB = os.getenv("MONGO_DB")
DB = os.getenv("DB")


async def create_text_channel(guild, channel_name):
    category = get_category_by_name(guild, "Games")
    await guild.create_text_channel(channel_name, category=category)
    channel = get_channel_by_name(guild, channel_name)
    return channel


async def create_voice_channel(guild, channel_name, category_name="Voice Channels", user_limit=None):
    category = get_category_by_name(guild, category_name)
    await guild.create_voice_channel(channel_name, category=category, user_limit=user_limit)
    channel = get_channel_by_name(guild, channel_name)
    return channel


async def get_invite_link(guild):
    invites = await guild.invites()
    if invites:
        return invites[0].url
    else:
        try:
            link = await guild.text_channels[0].create_invite()
            return link.url
        except discord.Forbidden:
            return "No permission to create invite"


def get_channel_by_name(guild, channel_name):
    channel = None
    for c in guild.channels:
        if c.name == channel_name.lower():
            channel = c
            break
    return channel


def get_category_by_name(guild, category_name):
    category = None
    for c in guild.channels:
        if c.name == category_name:
            category = c
            break
    return category


def create_embed(description, color):
    return discord.Embed(description=description, colour=color)


def initialize_mongodb():
    # Connect to your MongoDB cluster
    client = pymongo.MongoClient(MONGO_DB)
    db = client[DB]  # Replace "your_db_name" with the actual name of your MongoDB database
    return db

def async_initialize_mongodb():
    # Connect to your MongoDB cluster
    client = AsyncIOMotorClient(MONGO_DB)
    db = client[DB]  # Replace "your_db_name" with the actual name of your MongoDB database
    return db

def download_background(url):
    response = requests.get(url)
    if response.status_code == 200:
        background_filename = "background.png"
        with open(background_filename, "wb") as f:
            f.write(response.content)
        return background_filename
    else:
        return None


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


def hex_to_int(hex_color):
    hex_color = hex_color.lstrip('#')  # Remove '#' if present
    return int(hex_color, 16)


def find_guild_in_register_collection(guild_id):
    mongo_db = initialize_mongodb()
    record = mongo_db['register'].find_one({"guild_id": guild_id})
    return record


async def check_if_ctx_or_interaction(ctx_or_interaction):
    # Bu fonksiyon ctx veya interaction alabilir.
    # Farklı türleri kontrol etmek için isinstance kullanılabilir.
    if isinstance(ctx_or_interaction, discord.ext.commands.Context):
        # ctx için kod buraya
        guild = ctx_or_interaction.guild
        send = ctx_or_interaction.send
        channel = ctx_or_interaction.channel
    elif isinstance(ctx_or_interaction, discord.Interaction):
        # interaction için kod buraya
        guild = ctx_or_interaction.guild
        send = ctx_or_interaction.response.send_message
        channel = ctx_or_interaction.channel
    else:
        raise ValueError("Unknown context received")

    return guild, send, channel


def check_video_url(message_content):
    video_platforms = ["youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", "twitch.tv"]
    message_content = message_content.strip().lower()  # Başlangıç ve sonundaki boşlukları kaldır ve küçük harfe çevir
    for platform in video_platforms:
        if platform in message_content:
            return True
    return False
