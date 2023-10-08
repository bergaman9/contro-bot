import datetime
import os
from datetime import datetime

import discord
import dotenv
import pymongo
import requests
from PIL import Image, ImageChops, ImageDraw
from motor.motor_asyncio import AsyncIOMotorClient


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


async def async_initialize_mongodb():
    # Connect to your MongoDB cluster
    client = AsyncIOMotorClient(MONGO_DB)
    db = client[DB]  # Replace "your_db_name" with the actual name of your MongoDB database
    return db


def download_background(url):
    response = requests.get(url)
    if response.status_code == 200:
        background_filename = "../background.png"
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
        followup_send = ctx_or_interaction.followup.send
        channel = ctx_or_interaction.channel
    else:
        raise ValueError("Unknown context received")

    return guild, send, channel, followup_send


def check_video_url(message_content):
    video_platforms = ["youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", "twitch.tv"]
    message_content = message_content.strip().lower()  # Başlangıç ve sonundaki boşlukları kaldır ve küçük harfe çevir
    for platform in video_platforms:
        if platform in message_content:
            return True
    return False


def calculate_how_long_ago_member_joined(member):
    time_difference = datetime.utcnow() - member.joined_at.replace(tzinfo=None)

    years, days_remainder = divmod(time_difference.days, 365)
    days = days_remainder
    hours, remainder = divmod(time_difference.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if years > 0:
        return f"{years} years ago" if years > 1 else "1 year ago"

    if days > 0:
        return f"{days} days ago" if days > 1 else "1 day ago"

    if hours > 0:
        return f"{hours} hours ago" if hours > 1 else "1 hour ago"

    if minutes > 0:
        return f"{minutes} minutes ago" if minutes > 1 else "1 minute ago"

    return f"{seconds} seconds ago" if seconds > 0 else "just now"


def calculate_how_long_ago_member_created(member):
    time_difference = datetime.utcnow() - member.created_at.replace(tzinfo=None)

    years, days_remainder = divmod(time_difference.days, 365)
    days = days_remainder
    hours, remainder = divmod(time_difference.seconds, 3600)

    if years > 0:
        if days > 0:
            return f"{years} year{'s' if years > 1 else ''}, {days} day{'s' if days > 1 else ''} ago"
        return f"{years} year{'s' if years > 1 else ''} ago"

    if days > 0:
        if hours > 0:
            return f"{days} day{'s' if days > 1 else ''}, {hours} hour{'s' if hours > 1 else ''} ago"
        return f"{days} day{'s' if days > 1 else ''} ago"

    if hours > 0:
        minutes, _ = divmod(remainder, 60)
        if minutes > 0:
            return f"{hours} hour{'s' if hours > 1 else ''}, {minutes} minute{'s' if minutes > 1 else ''} ago"
        return f"{hours} hour{'s' if hours > 1 else ''} ago"

    minutes, seconds = divmod(remainder, 60)
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"

    return f"{seconds} second{'s' if seconds != 1 else ''} ago"


def prepare_leaderboard_embeds(mongo_db, guild):
    guild_id = str(guild.id)
    users_data = list(
        mongo_db["users"].find({}, projection=[f"guilds.{guild_id}", "user_id"]).sort(f"guilds.{guild_id}.level", -1))
    embeds = []
    for i in range(0, len(users_data), 10):
        current_users_data = users_data[i:i + 10]
        description = ""
        for user_data in current_users_data:
            user_id = int(user_data["user_id"])
            member = guild.get_member(user_id)
            if member:
                description += f"**{member.name}** - `Level {user_data['guilds'][guild_id]['level']}`\n"
        embed = discord.Embed(title="Leaderboard", description=description, color=discord.Color.green())
        embed.set_footer(text=f"{guild.name}")
        embeds.append(embed)
    return embeds



