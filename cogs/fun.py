import asyncio
import csv
from enum import Enum
import random
from typing import List
import json


import discord
from discord import app_commands
from discord.ext import commands, tasks

import html_text
import openai
import aiohttp
from aiohttp import request, ClientSession
import requests
import spotipy
import rawg
import asyncpraw
import tmdbsimple as tmdb
from spotipy.oauth2 import SpotifyClientCredentials
from translate import Translator
from datetime import datetime, timedelta, time

from utils import create_embed, initialize_mongodb

import os
import dotenv
dotenv.load_dotenv()


tmdb.API_KEY = os.getenv("TMDB_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=os.getenv("SP_CLIENT_ID"), client_secret=os.getenv("SP_CLIENT_SECRET")))

reddit = asyncpraw.Reddit(client_id = os.getenv("REDDIT_CLIENT_ID"),
                     client_secret = os.getenv("REDDIT_CLIENT_SECRET"),
                     username = os.getenv("REDDIT_USERNAME"),
                     password = os.getenv("REDDIT_PASSWORD"),
                     user_agent = os.getenv("REDDIT_USER_AGENT"))

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        self.check_birthdays.start()

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        current_day = datetime.now().day
        current_month = datetime.now().month

        # Sunucuları al
        guilds_data = self.mongo_db['birthday'].find()

        for guild_data in guilds_data:
            guild_id = guild_data['guild_id']
            birthday_channel_id = guild_data.get('channel_id')
            members_data = guild_data.get('members', [])

            # Bugün doğum günü olan kullanıcıları filtrele
            birthday_members = [m for m in members_data if m["day"] == current_day and m["month"] == current_month]

            if birthday_channel_id:
                birthday_channel = self.bot.get_channel(birthday_channel_id)

                for member_data in birthday_members:
                    member = self.bot.get_guild(guild_id).get_member(member_data["member_id"])
                    if member:
                        await birthday_channel.send(f"🎉 Mutlu yıllar {member.mention}! 🎂")

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        now = datetime.now()
        midnight = datetime.combine(now + timedelta(days=1), time(0))
        delta = midnight - now
        await asyncio.sleep(delta.total_seconds())

    def get_zodiac_sign(self, day, month):
        # Burada doğum gününe ve ayına göre burcun hesaplanacağı bir fonksiyon oluşturabilirsiniz.
        # Örnek olarak burç hesaplama kodu:
        zodiac_signs = [
            ("Akrep", (10, 23), (11, 21)),
            ("Yay", (11, 22), (12, 21)),
            ("Oğlak", (12, 22), (1, 19)),
            ("Kova", (1, 20), (2, 18)),
            ("Balık", (2, 19), (3, 20)),
            ("Koç", (3, 21), (4, 19)),
            ("Boğa", (4, 20), (5, 20)),
            ("İkizler", (5, 21), (6, 20)),
            ("Yengeç", (6, 21), (7, 22)),
            ("Aslan", (7, 23), (8, 22)),
            ("Başak", (8, 23), (9, 22)),
            ("Terazi", (9, 23), (10, 22))
        ]

        zodiac_sign = ""
        for sign, (start_month, start_day), (end_month, end_day) in zodiac_signs:
            if (month == start_month and day >= start_day) or (month == end_month and day <= end_day):
                zodiac_sign = sign
                break

        return zodiac_sign

    async def remove_zodiac_role(self, ctx, member):
        # Remove any existing zodiac sign roles from the member
        zodiac_roles = ["Akrep", "Yay", "Oğlak", "Kova", "Balık", "Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak", "Terazi"]
        removed_roles = []

        for role in member.roles:
            if role.name in zodiac_roles:
                removed_roles.append(role.mention)
                await member.remove_roles(role)

        if removed_roles:
            removed_roles_string = ", ".join(removed_roles)
            await ctx.send(embed=create_embed(f"{member.mention}, {removed_roles_string} burç rolün kaldırıldı.",
                                                   0xff0076))

    @commands.hybrid_command(name="birthday", description="Doğum günü belirterek burcunuzu alın.")
    @app_commands.describe(day="Doğum gününüzün günü.", month="Doğum gününüzün ayı.", year="Doğum gününüzün yılı.")
    async def birthday(self, ctx, day: int, month: int, year: int = None):
        # Kullanıcıya göre burç belirleme
        zodiac_sign = self.get_zodiac_sign(day, month)

        if zodiac_sign:
            role = discord.utils.get(ctx.guild.roles, name=zodiac_sign)
            if role:
                member = ctx.author

                await self.remove_zodiac_role(ctx, member)

                await member.add_roles(role)

                # Kullanıcının doğum gününü veritabanına kaydedin
                self.mongo_db['birthday'].update_one({"guild_id": ctx.guild.id}, {
                    "$push": {
                        "members": {
                            "day": day,
                            "month": month,
                            "year": year,
                            "member_id": member.id
                        }
                    }
                }, upsert=True)

                await ctx.send(
                    embed=create_embed(f"{member.mention}, burcun {role.mention} olarak belirlendi.",
                                       discord.Colour.green()))
            else:
                await ctx.send(embed=create_embed(
                    f"{zodiac_sign} adında bir rol bulunamadı. Lütfen sunucu yöneticisine bu rolü oluşturmasını söyleyin.",
                    discord.Colour.red()))
        else:
            await ctx.send(embed=create_embed("Geçersiz doğum günü veya ay.", discord.Colour.red()))

    @commands.hybrid_command(name="birthday_setup", description="Burç rollerini ve doğum günü kanalını ayarlayın.")
    @app_commands.describe(channel="Doğum günü mesajlarının paylaşılacağı kanal.")
    @commands.has_permissions(manage_roles=True)
    async def birthday_setup(self, ctx, channel: discord.TextChannel = None):
        # Burç rollerini ayarlayın
        await ctx.defer()
        zodiac_roles = ["Akrep", "Yay", "Oğlak", "Kova", "Balık", "Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak",
                        "Terazi"]
        for role in zodiac_roles:
            if not discord.utils.get(ctx.guild.roles, name=role):
                await ctx.guild.create_role(name=role)

        await ctx.send(embed=create_embed("Burç rolleri oluşturuldu.", discord.Colour.green()))

        if channel:
            self.mongo_db['birthday'].update_one({"guild_id": ctx.guild.id}, {"$set": {"channel_id": channel.id}},
                                                 upsert=True)
            await ctx.send(embed=create_embed(f"{channel.mention} kanalında doğum günü mesajları paylaşılacak.",
                                              discord.Colour.green()))

    @app_commands.command(name="ask", description="Get an answer to a question.")
    @app_commands.describe(question="Write your question.")
    async def ask(self, interaction, question: str):

        await interaction.response.defer(ephemeral=False, thinking=True)

        completion = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=[
                {'role': 'user', 'content': 'Hello!'}
            ],
            temperature=0
        )

        print(completion)

        response = completion.choices[0].message["content"]

        print(response)

        await interaction.followup.send(response)

    @commands.hybrid_command(name="crypto", description="Gets usd price of the asset.")
    @app_commands.describe(asset="The asset to get the price of.")
    async def crypto(self, ctx, asset):
        response = requests.get(f"https://api.coincap.io/v2/assets/{asset}")
        price = float(response.json()["data"]["priceUsd"])
        embed = discord.Embed(title=f"{asset.capitalize()}", description=f"**Price:** ${round(price, 2)}", colour=discord.Color.green())
        embed.add_field(name="Symbol", value=response.json()["data"]["symbol"], inline=True)
        embed.add_field(name="Rank", value=response.json()["data"]["rank"], inline=True)
        change_num = float(response.json()["data"]["changePercent24Hr"])
        embed.add_field(name="Change (24h)", value=round(change_num, 2), inline=True)
        supply_num = float(response.json()["data"]["supply"])
        embed.add_field(name="Supply", value=int(supply_num), inline=True)
        maxSupply_num = float(response.json()["data"]["maxSupply"])
        embed.add_field(name="Max Supply", value=int(maxSupply_num), inline=True)
        await ctx.send(embed=embed)


    @commands.hybrid_command(name="shorten", description="Shorts the url.")
    @app_commands.describe(link="The link to shorten.")
    async def shorten(self, ctx, link):
        await ctx.defer()
        response = requests.get(f"https://api.shrtco.de/v2/shorten?url={link}/very/long/link.html")

        try:
            response_json = response.json()
            short_link = response_json["result"]["full_short_link"]
            await ctx.send(f"**Short Link:** {short_link}")
        except:
            await ctx.send("The link you entered is a disallowed link, for more infos see shrtco.de/disallowed")


    @commands.hybrid_command(name="suggest_game", description="Suggests a game.")
    async def suggest_game(self, ctx):

        game_list = []
        game_url = []

        with open("datas/bergaman9.csv", 'r') as file:
            csvreader = csv.reader(file)
            for row in csvreader:
                game_list.append(row[0])
                game_url.append(row[10])

        file.close()

        random_number = random.randint(1, len(game_list))

        random_game = game_list[random_number]
        game_url = game_url[random_number]

        await ctx.send(f"You can play **{random_game}**. \n{game_url}")

    @commands.hybrid_command(name="sentence", description="Fetches an example sentence.")
    @app_commands.describe(word="The word to fetch the example sentence of.")
    async def sentence(self, ctx, word):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.wordnik.com/v4/word.json/{word}/examples?includeDuplicates=false&useCanonical=false&limit=5&api_key=f92xh8ket8ue6gz0idhb2w8khifl29fudmopu83pnpoafdmmd") as response:
                if response.status == 200:
                    json_data = await response.json()
                    examples = json_data.get("examples", [])

                    if examples:
                        random_example = random.choice(examples)["text"]
                        await ctx.send(embed=create_embed(description=random_example.replace(word, f"**{word}**"),
                                                          color=discord.Color.green()))
                    else:
                        await ctx.send(embed=create_embed(description=f"No examples found for the word **{word}**.",
                                                          color=discord.Color.red()))
                else:
                    await ctx.send(embed=create_embed(description=f"Could not find the word **{word}**.",
                                                      color=discord.Color.red()))

    async def fetch_example(self, word):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"https://api.wordnik.com/v4/word.json/{word}/examples?includeDuplicates=false&useCanonical=false&limit=5&api_key=f92xh8ket8ue6gz0idhb2w8khifl29fudmopu83pnpoafdmmd") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    examples = data["examples"]
                    if examples:
                        return examples[random.randint(0, len(examples) - 1)]["text"]
                    else:
                        return "Example sentence not found."
                else:
                    return "Example sentence not found."

    @commands.hybrid_command(name="word", description="Fetches info about the word.")
    @app_commands.describe(word="The word to fetch the info of.")
    async def word(self, ctx, word):
        await ctx.defer()

        async with aiohttp.ClientSession() as session:
            # Fetch word meanings
            async with session.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    meanings = data[0]["meanings"]
                else:
                    await ctx.send(embed=create_embed(description=f"Could not find the word **{word}**.", color=discord.Color.red()))
                    return

            # Prepare meanings
            meaning_list = []
            for meaning in meanings:
                meaning_list.append(f"**{meaning['partOfSpeech']}**: {meaning['definitions'][0]['definition']}")

            # Translation
            translator = Translator(to_lang="tr")
            translation_tr = translator.translate(word)

            translator = Translator(to_lang="de")
            translation_de = translator.translate(word)

            # Fetch example sentences
            random_example = await self.fetch_example(word)

        embed = discord.Embed(
            title=f"{word.capitalize()} || 🇹🇷 {translation_tr.lower()}  🇩🇪 {translation_de.lower()}||",
            description="\n".join(meaning_list), color=ctx.author.color)
        embed.add_field(name="Example", value=random_example.replace(word, f"**{word}**"), inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="reddit", description="Sends content from reddit about sub you choosed.")
    @app_commands.describe(sub="The sub to fetch the meme of.")
    async def reddit(self, ctx, sub):
        await ctx.defer()
        try:
            subreddit = await reddit.subreddit(sub, fetch=True)
        except:
            await ctx.send(embed=create_embed(description=f"Could not find the subreddit **{sub}**.", color=discord.Color.red()))
            return

        all_subs = []

        async for submission in subreddit.top(limit=30, time_filter="week"):
            all_subs.append(submission)

        if not all_subs:
            await ctx.send(embed=create_embed(description=f"Could not find any memes in the subreddit **{sub}**.", color=discord.Color.red()))
            return

        random_sub = random.choice(all_subs)

        name = random_sub.title
        url = random_sub.url
        link = random_sub.shortlink
        description = random_sub.selftext

        embed = discord.Embed(title=name, description=f"{description} \n**Reddit:** {link}", color=0xff4500)

        if url.endswith(('png', 'jpg', 'jpeg', 'gif')):  # Make sure URL exists
            embed.set_image(url=url)
        else:
            embed.add_field(name="Content", value=url)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="spotify", description="Shows top 5 songs according to your query.")
    @app_commands.describe(query="The query to search for.")
    async def spotify(self, ctx, query):
        await ctx.defer()
        spotifyList = []
        results = sp.search(q=query, limit=5)
        for idx, track in enumerate(results['tracks']['items']):
            spotifyList.append(f"🎵 **{track['name']}** {track['external_urls']['spotify']}")

        try:
            await ctx.send("\n".join(spotifyList))
        except:
            await ctx.send(embed=create_embed(description=f"Could not find the song **{query}**.", color=discord.Color.red()))

    async def game_name_autocomplete(self, interaction: discord.Interaction, current: str) -> List[
        app_commands.Choice[str]]:
        games = [
            "Grand Theft Auto V",
            "Roblox",
            "Minecraft",
            "League of Legends",
            "Fortnite",
            "Apex Legends",
            "Counter-Strike: Global Offensive",
            "VALORANT",
            "Rocket League",
            "Call of Duty: Warzone",
            "Overwatch",
        ]

        matching_games = [
            game for game in games if current.lower() in game.lower()
        ]

        return [app_commands.Choice(name=game, value=game) for game in matching_games]

    @commands.hybrid_command(name="game", description="Finds the game you want to see.")
    @app_commands.describe(name="The name of the game to search for.")
    @app_commands.autocomplete(name=game_name_autocomplete)
    async def game(self, ctx, name):
        await ctx.defer()
        try:
            async with rawg.ApiClient(
                    rawg.Configuration(api_key={'key': '31594c329244494eb5fd3f6cc379d044'})) as api_client:
                # Create an instance of the API class
                api = rawg.GamesApi(api_client)

                # Search for the game using games_list
                search_result = await api.games_list(search=name, page_size=1)

                if not search_result.results:
                    await ctx.send(
                        embed=create_embed(description="Could not find the game.", color=discord.Color.red()))
                    return

                # Take the first result from the search
                first_result = search_result.results[0]
                game_id = first_result.id

                # Fetch detailed game info using the id
                game = await api.games_read(id=game_id)

                embed = discord.Embed(title=game.name, url=game.website,
                                      description=html_text.extract_text(game.description, guess_layout=False),
                                      colour=ctx.author.color)
                embed.add_field(name="Release Date", value=game.released, inline=True)
                embed.add_field(name="Rating", value=game.rating, inline=True)
                embed.add_field(name="Metacritic", value=game.metacritic, inline=True)
                embed.set_image(url=game.background_image)
                await ctx.send(embed=embed)

        except Exception as e:
            print(e)
            await ctx.send(embed=create_embed(description="An error occurred or the game could not be found.",
                                              color=discord.Color.red()))

    async def movie_name_autocomplete(self, interaction: discord.Interaction, current: str) -> List[
        app_commands.Choice[str]]:
        games = [
            "Drive",
            "Adaption.",
            "The Departed",
            "Thunderbolt and Lightfoot",
            "Jaws",
            "Die Hard",
            "Rocky Balboa",
            "Cop Land",
            "All Good Things",
            "Raising Arizona",
            "Escape From Alcatraz",
            "American Psycho",
            "Con Air",
            "Lord of War",
            "Rain Man",
            "The Godfather",
            "The Dark Knight",
            "Interstellar",
        ]

        matching_games = [
            game for game in games if current.lower() in game.lower()
        ]

        return [app_commands.Choice(name=game, value=game) for game in matching_games]

    @commands.hybrid_command(name="movie", description="Finds the movie you want to see.")
    @app_commands.describe(name="The name of the movie to search for.")
    @app_commands.autocomplete(name=movie_name_autocomplete)
    async def movie(self, ctx, name: str):
        await ctx.defer()

        search = tmdb.Search()
        search.movie(query=name)

        # Eğer film bulunamazsa bir mesaj gönder
        if not search.results:
            await ctx.send(embed=create_embed(description="Sorry, no movies found.", color=discord.Color.red()))
            return

        content = search.results[0]

        genres = content.get("genre_ids", [])
        genre_names = []
        for genre in genres:
            genre_mapping = {
                18: "Drama",
                28: "Action",
                12: "Adventure",
                16: "Animation",
                35: "Comedy",
                80: "Crime",
                99: "Documentary",
                10751: "Family",
                14: "Fantasy",
                36: "History",
                27: "Horror",
                10749: "Romance",
                53: "Thriller",
                10752: "War",
                37: "Western",
                878: "Science Fiction"
            }
            genre_names.append(genre_mapping.get(genre, "Unknown"))

        embed = discord.Embed(title=content["title"],
                              description=content["overview"],
                              color=ctx.author.color)
        embed.add_field(name="User Score", value=content["vote_average"], inline=True)
        embed.add_field(name="Release Date", value=content["release_date"], inline=True)
        embed.add_field(name="Genres", value=(", ").join(str(e) for e in genre_names), inline=True)
        embed.set_image(url=f"https://image.tmdb.org/t/p/original/{content['backdrop_path']}")

        await ctx.send(embed=embed)

    async def tv_name_autocomplete(self, interaction: discord.Interaction, current: str) -> List[
        app_commands.Choice[str]]:
        tv_shows = [
            "Breaking Bad",
            "Game of Thrones",
            "Friends",
            "The Office",
            "Stranger Things",
            "Black Mirror",
            "The Crown",
            "Westworld",
            "Fargo",
            "Narcos",
            "The Mandalorian",
            "The Witcher",
            "Better Call Saul",
            "The Sopranos",
            "Sherlock"
        ]

        matching_tv_shows = [
            tv_show for tv_show in tv_shows if current.lower() in tv_show.lower()
        ]

        return [app_commands.Choice(name=tv_show, value=tv_show) for tv_show in matching_tv_shows]


    @commands.hybrid_command(name="tv", description="Finds the TV show you want to see.")
    @app_commands.describe(name="The name of the TV show to search for.")
    @app_commands.autocomplete(name=tv_name_autocomplete)  # Burada isimleri düzenlemeyi unutmayın
    async def tv(self, ctx, name: str):
        await ctx.defer()

        search = tmdb.Search()
        search.tv(query=name)

        # Eğer TV dizi bulunamazsa
        if not search.results:
            await ctx.send(embed=create_embed(description="Sorry, no TV shows found.", color=discord.Color.red()))
            return

        content = search.results[0]

        genres = content.get("genre_ids", [])
        genre_names = []
        for genre in genres:
            genre_mapping = {
                18: "Drama",
                10759: "Action & Adventure",
                16: "Animation",
                35: "Comedy",
                80: "Crime",
                99: "Documentary",
                10751: "Family",
                14: "Fantasy",
                36: "History",
                27: "Horror",
                10749: "Romance",
                53: "Thriller",
                10768: "War & Politics",
                37: "Western",
                878: "Science Fiction",
                10762: "Kids",
                10767: "Talk",
                10763: "News",
                10766: "Soap",
                10765: "Sci-Fi & Fantasy",
                10764: "Reality",
                9648: "Mystery",
            }
            genre_names.append(genre_mapping.get(genre, "Unknown"))

        embed = discord.Embed(title=content["name"],
                              description=content["overview"],
                              color=ctx.author.color)
        embed.add_field(name="User Score", value=content["vote_average"], inline=True)
        embed.add_field(name="First Air Date", value=content.get("first_air_date"), inline=True)
        embed.add_field(name="Genres", value=(", ").join(str(e) for e in genre_names), inline=True)
        embed.set_image(url=f"https://image.tmdb.org/t/p/original/{content['backdrop_path']}")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="love", description="Sends a channel message that you love mentioned member.")
    @app_commands.describe(member="The member to love.")
    async def love(self, ctx, member: discord.Member):
        embed = discord.Embed(description=f"{ctx.author.mention}, {member.mention} seni çok seviyor! ❤", color=0xffcbdb)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="love_calculator", description="Calculate love percentage between two members.")
    @app_commands.describe(member="The member to calculate love percentage.")
    async def love_calculator(self, ctx, member: discord.Member):
        lovePercentage = random.randint(0,100)
        await ctx.send(f"{member.mention} loves you {lovePercentage}%")

    @commands.hybrid_command(name="echo", description="Says what you say.", aliases=["say"])
    @app_commands.describe(message="The message to say.")
    async def echo(self, ctx, *, message):
        await ctx.send(message)
        await ctx.message.delete()

    @commands.hybrid_command(name="_8ball", description="Ask a question, bot will be answer!", aliases=['8ball'])
    @app_commands.describe(question="Write your question.")
    async def _8ball(self, ctx, *, question):
        responses = [
                "Kesin.",
                "Sanırım öyle.",
                "Şüphe yok.",
                "Evet - kesinlikle.",
                "Buna güvenmelisin.",
                "Göründüğü üzere evet.",
                "Eh işte.",
                "Göründüğü kadarıyla iyi.",
                "Sonra tekrar sor.",
                "Şimdi sormasan iyi.",
                "Şu anda tahmin edemiyorum.",
                "Odaklan ve tekrar sor.",
                "Pek bel bağlama.",
                "Cevabım hayır.",
                "Kaynaklarım hayır diyor.",
                "Çok iyi görünmüyor.",
                "Çok şüpheli."]

        await ctx.send(f'Soru: {question}\nCevap: {random.choice(responses)}')


    @commands.hybrid_command(name="reverse", description="Reverses the text you writed.")
    @app_commands.describe(text="The text to reverse.")
    async def reverse(self, ctx, *, text: str):
        t_rev = text[::-1].replace("@", "@\u200B").replace("&", "&\u200B")
        await ctx.send(f"🔁 {t_rev}")


async def setup(bot):
    await bot.add_cog(Fun(bot))