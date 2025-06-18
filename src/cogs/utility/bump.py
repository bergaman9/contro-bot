from discord.ext import commands, tasks
import requests
import asyncio
import os
import dotenv

dotenv.load_dotenv()

USER_TOKEN = os.getenv("USER_TOKEN")
USER_ID = os.getenv("USER_ID")
TURKOYTO_CID = os.getenv("TURKOYTO_CID")
TEKNOMINATOR_CID = os.getenv("TEKNOMINATOR_CID")
TURKOYTO_GID = os.getenv("TURKOYTO_GID")
TEKNOMINATOR_GID = os.getenv("TEKNOMINATOR_GID")
SESSION_ID = os.getenv("SESSION_ID")
# Bu iki değer her zaman güncel tutulmalı! Discord istemcisinin networkünden alınır.
BUMP_COMMAND_ID = "947088344167366698"
BUMP_COMMAND_VERSION = "1051151064008769576"
APPLICATION_ID = "302050872383242240"  # Disboard botu

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
HEADERS = {
    "Authorization": USER_TOKEN,
    "User-Agent": USER_AGENT,
    "Content-Type": "application/json",
    "Origin": "https://discord.com",
    "Referer": "https://discord.com/channels/@me",
}

def build_bump_payload(guild_id, channel_id, session_id):
    return {
        "type": 2,
        "application_id": APPLICATION_ID,
        "guild_id": str(guild_id),
        "channel_id": str(channel_id),
        "session_id": str(session_id),
        "data": {
            "version": BUMP_COMMAND_VERSION,
            "id": BUMP_COMMAND_ID,
            "name": "bump",
            "type": 1
        }
    }

def send_bump_interaction(guild_id, channel_id, session_id):
    url = "https://discord.com/api/v9/interactions"
    payload = build_bump_payload(guild_id, channel_id, session_id)
    response = requests.post(url, headers=HEADERS, json=payload)
    return response

class Bump(commands.Cog):
    """Discord sunucularını otomatik olarak bump'layan cog"""
    
    # Zaman sabitleri
    BUMP_INTERVAL = 120  # dakika
    INTER_SERVER_WAIT = 1800  # 30 dakika (saniye cinsinden)
    
    def __init__(self, bot):
        self.bot = bot
        self.bump_scheduler.start()

    @tasks.loop(minutes=BUMP_INTERVAL)
    async def bump_scheduler(self):
        """Belirli aralıklarla bump işlemlerini planlayan döngü"""
        await self.bot.wait_until_ready()
        await self.process_server_bumps()

    async def process_server_bumps(self):
        """Tüm yapılandırılmış sunucular için bump işlemlerini yürütür"""
        # İlk sunucu: Türk Oyuncu Topluluğu
        await self._bump_server(
            guild_id=TURKOYTO_GID,
            channel_id=TURKOYTO_CID,
            server_name="Türk Oyuncu Topluluğu"
        )

        # Sunucular arası bekleme süresi
        await asyncio.sleep(self.INTER_SERVER_WAIT)

        # İkinci sunucu: Teknominatör
        await self._bump_server(
            guild_id=TEKNOMINATOR_GID,
            channel_id=TEKNOMINATOR_CID,
            server_name="Teknominatör"
        )

    async def _bump_server(self, guild_id, channel_id, server_name):
        """Belirli bir sunucu için bump komutunu gönderir
        
        Args:
            guild_id: Discord sunucu ID'si
            channel_id: Discord kanal ID'si
            server_name: Log için okunabilir sunucu adı
        """
        response = send_bump_interaction(guild_id, channel_id, SESSION_ID)
        
        if response.status_code in (200, 204):
            print(f"{server_name} için /bump komutu başarıyla gönderildi.")
        else:
            print(f"{server_name} bump hatası: {response.status_code} - {response.text}")

async def setup(bot):
    await bot.add_cog(Bump(bot))