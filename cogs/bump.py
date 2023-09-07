from discord.ext import commands, tasks
import requests
import asyncio

import os
import dotenv
dotenv.load_dotenv()

headers={"authorization": os.getenv("AUTHORIZATION")}
turkoyto_payload={"type": 2, "application_id":"302050872383242240","guild_id":os.getenv("TURKOYTO_GID"), "session_id": os.getenv("SESSION_ID"),"channel_id": os.getenv("TURKOYTO_CID"), "data": {"version": "1051151064008769576", "id": "947088344167366698", "name": "bump","type": 1}}
teknominator_payload={"type": 2, "application_id":"302050872383242240","guild_id":os.getenv("TEKNOMINATOR_GID"), "session_id": os.getenv("SESSION_ID"),"channel_id": os.getenv("TEKNOMINATOR_CID"), "data": {"version": "1051151064008769576", "id": "947088344167366698", "name": "bump","type": 1}}


class Bump(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.send_payload.start()  # tasks.loop'u başlat

    @tasks.loop(minutes=150)
    async def send_payload(self):
        await self.bot.wait_until_ready()  # Bot tamamen hazır olmadan döngüyü başlatma
        response = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=turkoyto_payload)
        if response.status_code == 204:
            print("Türk Oyuncu Topluluğu öne çıkarıldı.")
        await asyncio.sleep(1800)  # asyncio.sleep kullanarak bekleme süresi
        response = requests.post("https://discord.com/api/v9/interactions", headers=headers, json=teknominator_payload)
        if response.status_code == 204:
            print("Teknominatör öne çıkarıldı.")
        await asyncio.sleep(7200)

async def setup(bot):
    await bot.add_cog(Bump(bot))