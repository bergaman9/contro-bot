from discord.ext import commands, tasks
import requests
import asyncio

import os
import dotenv
dotenv.load_dotenv()

headers={"authorization": "MzM2NjE1Mjk5Njk0NDYwOTMz.GhRtSR.59IlqXAl6mhljneXSCBYiDDALnrANpe5JtpNnM",}
turkoyto_payload={"type": 2, "application_id":"302050872383242240","guild_id":"505520771603496971", "session_id": "2b5a51b355976a47f479edfeb8a1de13","channel_id": "1030939187496632381", "data": {"version": "1051151064008769576", "id": "947088344167366698", "name": "bump","type": 1}}
teknominator_payload={"type": 2, "application_id":"302050872383242240","guild_id":"1022821492565749771", "session_id": "2b5a51b355976a47f479edfeb8a1de13","channel_id": "1031565331614929037", "data": {"version": "1051151064008769576", "id": "947088344167366698", "name": "bump","type": 1}}


class Bump(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.send_payload.start()  # tasks.loop'u başlat

    @tasks.loop(minutes=150)
    async def send_payload(self):
        await self.bot.wait_until_ready()  # Bot tamamen hazır olmadan döngüyü başlatma
        response = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=turkoyto_payload)
        print(response)
        if response.status_code == 204:
            print("Türk Oyuncu Topluluğu öne çıkarıldı.")
        await asyncio.sleep(1800)  # asyncio.sleep kullanarak bekleme süresi
        response = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=teknominator_payload)
        if response.status_code == 204:
            print("Teknominatör öne çıkarıldı.")
        await asyncio.sleep(7200)

async def setup(bot):
    await bot.add_cog(Bump(bot))