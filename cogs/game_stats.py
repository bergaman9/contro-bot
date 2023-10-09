from typing import List

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils import async_initialize_mongodb, create_embed
from utility.class_utils import Paginator


class GameStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongodb = async_initialize_mongodb()
        self.update_game_activities.start()
        self.update_game_logs.start()
        self.clean_up_database_for_guild.start()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Bir üye sunucudan ayrıldığında çağrılır."""
        try:
            await self.remove_game_logs_in_db(member.guild, member)
        except Exception as e:
            print(f"Error in on_member_remove: {e}")

    @tasks.loop(seconds=60, reconnect=True)
    async def update_game_activities(self):
        try:
            for guild in self.bot.guilds:
                count = 0
                for member in guild.members:
                    count += 1
                    if not member.bot and member.activity and member.activity.type == discord.ActivityType.playing:
                        game_name = member.activity.name if member.activity else None
                        if game_name:
                            await self.update_game_in_db(guild.id, game_name, member.id)
                # print(f"Updated {count} members' game activity in {guild.name}")
        except Exception as e:
            print(f"Error in update_game_activities: {e}")

    @tasks.loop(seconds=60, reconnect=True)
    async def update_game_logs(self):
        for guild in self.bot.guilds:
            try:
                print(f"Checking {guild.name} for game logs")
                added_count = 0
                removed_count = 0
                for member in guild.members:
                    if not member.bot and member.activity and member.activity.type == discord.ActivityType.playing:
                        game_name = member.activity.name if member.activity else None
                        if game_name:
                            added_count += 1
                            await self.update_game_logs_in_db(guild.id, game_name, member.id)
                    else:
                        removed_count += 1
                        await self.remove_game_logs_in_db(guild, member)
                        if guild.name == "Türk Oyuncu Topluluğu":
                            print(f"Removed {member.name}'s game logs")
                # print(f"Added {added_count} and removed {removed_count} members' game logs in {guild.name}")
            except Exception as e:
                print(f"Error in update_game_logs for guild {guild.name}: {e}")

    @tasks.loop(seconds=60, reconnect=True)
    async def clean_up_database_for_guild(self):
        for guild in self.bot.guilds:
            try:
                # print(f"Cleaning up logs for guild {guild.id}")
                game_logs = self.mongodb["game_logs"]
                guild_log = await game_logs.find_one({"guild_id": guild.id})

                if not guild_log:
                    print(f"No logs found for guild {guild.id}.")
                    continue  # 'return' yerine 'continue' kullanarak diğer sunucular için döngüyü devam ettiriyoruz.

                current_member_ids = [member.id for member in guild.members]
                for game in guild_log["game_names"]:
                    # Sunucuda olmayan üyeleri active_players listesinden kaldır
                    players_to_remove = [player for player in game["active_players"] if
                                         player["member_id"] not in current_member_ids]
                    for player in players_to_remove:
                        game["active_players"].remove(player)

                # Veritabanını güncelle
                await game_logs.update_one({"guild_id": guild.id}, {"$set": {"game_names": guild_log["game_names"]}})
                # print(f"Cleaned up logs for guild {guild.id}.")
                if guild.name == "Türk Oyuncu Topluluğu":
                    print(f"Cleaned up logs for guild {guild.id}.")
            except Exception as e:
                print(f"Error in clean_up_database_for_guild for guild {guild.id}: {e}")

    async def remove_game_logs_in_db(self, guild, member):
        try:
            game_logs = self.mongodb["game_logs"]
            log = await game_logs.find_one({"guild_id": guild.id})
            if log:
                for game in log["game_names"]:
                    game["active_players"] = [player for player in game["active_players"] if
                                              player["member_id"] != member.id]
                    if len(game["active_players"]) == 0:
                        log["game_names"].remove(game)

                await game_logs.update_one({"guild_id": guild.id}, {"$set": {"game_names": log["game_names"]}})
        except Exception as e:
            print(f"Error in remove_game_logs_in_db: {e}")

    async def update_game_in_db(self, guild_id, game_name, member_id):
        game_stats = self.mongodb["game_stats"]

        # Find the guild's document or create it if it doesn't exist
        guild_data = await game_stats.find_one({"guild_id": guild_id})
        if not guild_data:
            game_stats.insert_one({"guild_id": guild_id, "played_games": []})
            guild_data = game_stats.find_one({"guild_id": guild_id})
            # print(f"Created a new document for guild {guild_id}.")

        # Update the played_games list for the game
        played_games = guild_data.get("played_games", [])
        for game in played_games:
            if game["game_name"] == game_name:
                game["total_time_played"] += 1
                # Member update or insert
                for player in game["players"]:
                    if player["member_id"] == member_id:
                        player["time_played"] += 1
                        break
                else:
                    game["players"].append({"member_id": member_id, "time_played": 1})
                # print(f"Updated game: {game_name} for user: {member_id}")
                break
        else:
            played_games.append({
                "game_name": game_name,
                "total_time_played": 1,
                "players": [{"member_id": member_id, "time_played": 1}]
            })
            # print(f"Added new game: {game_name} for user: {member_id}")

        # Update the document in the database
        game_stats.update_one({"guild_id": guild_id}, {"$set": {"played_games": played_games}})

    @commands.hybrid_command(name="topgames", description="En çok oynanan oyunları gösterir.")
    @app_commands.describe(member="Üyenin oynadığı oyunları gösterir.")
    async def topgames(self, ctx, member: discord.Member = None):
        if member:
            # Üyenin oynadığı oyunları al
            member_games = await self.get_member_top_games(ctx.guild.id, member.id)

            def chunk_list(l, n):
                """Yield successive n-sized chunks from l."""
                for i in range(0, len(l), n):
                    yield l[i:i + n]

            embeds = []  # Embed listesi oluşturuldu
            for chunk in chunk_list(member_games, 15):  # Oyunları 15'lik gruplara ayırdık
                description = ""
                for idx, game in enumerate(chunk, 1 + (15 * embeds.__len__())):  # index ile birlikte enumerate
                    description += f"{idx}. {game['game_name']}: `{game['time_played']} minutes`\n"
                embed = discord.Embed(title=f"{member.name}'s Top Played Games", description=description,
                                      color=discord.Color.pink())
                embeds.append(embed)  # Oluşturulan embed'i listeye ekledik

            view = Paginator(embeds)
            await view.send_initial_message(ctx)
        else:
            game_stats = self.mongodb["game_stats"]
            guild_data = await game_stats.find_one({"guild_id": ctx.guild.id})

            if guild_data and "played_games" in guild_data:
                played_games = guild_data["played_games"]
                top_games = sorted(played_games, key=lambda game: game["total_time_played"], reverse=True)

                def chunk_list(l, n):
                    """Yield successive n-sized chunks from l."""
                    for i in range(0, len(l), n):
                        yield l[i:i + n]

                embeds = []  # Embed listesi oluşturuldu
                for chunk in chunk_list(top_games, 15):  # Oyunları 15'lik gruplara ayırdık
                    description = ""
                    for idx, game in enumerate(chunk, 1 + (15 * embeds.__len__())):  # index ile birlikte enumerate
                        description += f"{idx}. {game['game_name']}: `{game['total_time_played']} minutes`\n"
                    embed = discord.Embed(title="Top Played Games", description=description,
                                          color=discord.Color.pink())
                    embeds.append(embed)  # Oluşturulan embed'i listeye ekledik

                view = Paginator(embeds)
                await view.send_initial_message(ctx)
            else:
                await ctx.send(
                    embed=create_embed(description="No game statistics available.", color=discord.Color.red()))

    async def get_member_top_games(self, guild_id, member_id):
        game_stats = self.mongodb["game_stats"]
        guild_data = await game_stats.find_one({"guild_id": guild_id})

        member_games = []

        if guild_data and "played_games" in guild_data:
            for game in guild_data["played_games"]:
                for player in game["players"]:
                    if player["member_id"] == member_id:
                        member_games.append({
                            "game_name": game["game_name"],
                            "time_played": player["time_played"]
                        })

        # Oyunları en çok oynanandan en az oynanana doğru sırala
        member_games = sorted(member_games, key=lambda game: game["time_played"], reverse=True)
        return member_games

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
            "Visual Studio Code",
        ]

        matching_games = [
            game for game in games if current.lower() in game.lower()
        ]

        return [app_commands.Choice(name=game, value=game) for game in matching_games]

    @commands.hybrid_command(name="playing", description="Aktif olarak oyun oynayanları gösterir.")
    @app_commands.describe(game_name="Oyun adı")
    @app_commands.autocomplete(game_name=game_name_autocomplete)
    async def playing(self, ctx, game_name: str):
        async with ctx.typing():
            game_logs = self.mongodb["game_logs"]
            guild_log = await game_logs.find_one({"guild_id": ctx.guild.id})

            if not guild_log:
                await ctx.send(
                    embed=create_embed(description=f"No one is playing {game_name}", color=discord.Color.red()))
                return

            game_entry = next((game for game in guild_log.get("game_names", []) if game["game_name"] == game_name),
                              None)

            if not game_entry:
                await ctx.send(
                    embed=create_embed(description=f"No one is playing {game_name}", color=discord.Color.red()))
                return

            description = ""
            for idx, player in enumerate(game_entry["active_players"], 1):
                member = ctx.guild.get_member(player["member_id"])
                if member:
                    description += f"{idx}. {member.mention} - playing for {player['time_played']} minutes\n"

            embed = discord.Embed(title=f"Players currently playing {game_name}", description=description,
                                  color=discord.Color.pink())
            await ctx.send(embed=embed)

    async def update_game_logs_in_db(self, guild_id, game_name, member_id):
        game_logs = self.mongodb["game_logs"]

        # Sunucu için olan dökümanı bul ya da oluştur
        log = await game_logs.find_one({"guild_id": guild_id})
        if not log:
            await game_logs.insert_one({"guild_id": guild_id, "game_names": []})
            log = await game_logs.find_one({"guild_id": guild_id})
            print(f"-Created a new document for guild {guild_id}.")

        # Oyunun aktif oyuncular listesinde olup olmadığını kontrol et
        for game in log["game_names"]:
            if game["game_name"] == game_name:
                for player in game["active_players"]:
                    if player["member_id"] == member_id:
                        player["time_played"] += 1
                        # print(f"-Updated game: {game_name} for user: {member_id}")
                        break
                else:
                    game["active_players"].append({"member_id": member_id, "time_played": 1})
                    # print(f"-Added new game: {game_name} for user: {member_id}")
                break
        else:
            log["game_names"].append({
                "game_name": game_name,
                "active_players": [{"member_id": member_id, "time_played": 1}]
            })
            # print(f"-Added new game: {game_name} for user: {member_id}")

        # Dökümanı güncelle
        await game_logs.update_one({"guild_id": guild_id}, {"$set": {"game_names": log["game_names"]}})


async def setup(bot):
    await bot.add_cog(GameStats(bot))
