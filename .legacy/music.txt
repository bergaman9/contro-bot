import discord, time
from discord.ext import commands, tasks
import wavelink
from wavelink.ext import spotify

from utils import create_embed

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.inactive_channels = {}  # Inaktif kanalları tutacak bir sözlük
        self.check_inactive_channels.start()  # Görevi başlat

    @tasks.loop(minutes=3)
    async def check_inactive_channels(self):
        await self.bot.wait_until_ready()  # Bot hazır olana kadar bekle
        for vc in self.bot.voice_clients:
            if not vc.is_playing() and not any([not member.bot for member in vc.channel.members]):
                # Eğer ses oynatılmıyorsa ve kanalda bot haricinde kimse yoksa
                if vc.channel.id in self.inactive_channels:
                    if (time.time() - self.inactive_channels[vc.channel.id]) > 60:  # 60 saniye süre
                        await vc.disconnect()
                        del self.inactive_channels[vc.channel.id]
                else:
                    self.inactive_channels[vc.channel.id] = time.time()
            else:
                if vc.channel.id in self.inactive_channels:
                    del self.inactive_channels[vc.channel.id]

    @commands.hybrid_command(name="play", description="Plays the given track or searches for a track and plays the first result.")
    async def play(self, ctx: commands.Context, search: str) -> None:
        """Play command that handles both YouTube and Spotify links."""

        if not hasattr(ctx.author.voice, 'channel') or ctx.author.voice.channel is None:
            await ctx.send(
                embed=create_embed(description='You must be connected to a voice channel to use this command.',
                                   color=discord.Color.red()))
            return

        if not ctx.voice_client:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = ctx.voice_client

        vc.autoplay = False

        # Check if the search matches a valid Spotify URL...
        decoded = spotify.decode_url(search)
        if decoded and decoded['type'] == spotify.SpotifySearchType.track:
            # It's a valid Spotify URL
            tracks: list[spotify.SpotifyTrack] = await spotify.SpotifyTrack.search(search)
            if tracks:
                track: spotify.SpotifyTrack = tracks[0]
                if not vc.is_playing():
                    await vc.play(track, populate=True)
                    await ctx.send(embed=create_embed(description=f"Now playing: **{track.title}**", color=discord.Color.green()))
                else:
                    await vc.queue.put_wait(track)
                    await ctx.send(embed=create_embed(description=f"Queued: **{track.title}**", color=discord.Color.green()))
            else:
                await ctx.send(embed=create_embed(description='This does not appear to be a valid Spotify URL.', color=discord.Color.red()))
        else:
            # It's not a Spotify URL, treat it as a YouTube search
            tracks = await wavelink.YouTubeTrack.search(search)
            if tracks:
                track: wavelink.YouTubeTrack = tracks[0]
                if not vc.is_playing():
                    await vc.play(track, populate=True)
                    await ctx.send(embed=create_embed(description=f"Now playing: **{track.title}**", color=discord.Color.green()))
                else:
                    await vc.queue.put_wait(track)
                    await ctx.send(embed=create_embed(description=f"Queued: **{track.title}**", color=discord.Color.green()))
            else:
                await ctx.send(f'No tracks found with query: `{search}`')

    @commands.hybrid_command(name="skip", description="Skips the current track.")
    async def skip(self, ctx):
        vc: wavelink.Player = ctx.voice_client

        if vc and vc.is_playing():
            await vc.stop()

            if vc.queue and len(vc.queue) > 0:
                next_track = vc.queue[0]
                await ctx.send(
                    embed=create_embed(description=f"Skipped the current track. Now playing: **{next_track.title}**",
                                       color=discord.Color.green()))
            elif vc.autoplay:  # Eğer autoplay aktifse, skip mesajını atlamak yerine bilgilendir
                await ctx.send(embed=create_embed(description="Autoplay is enabled. Waiting for next track.",
                                                  color=discord.Color.yellow()))
            else:
                await ctx.send(
                    embed=create_embed(description="No more tracks in the queue.", color=discord.Color.red()))
        else:
            await ctx.send(embed=create_embed(description="No active playback to skip.", color=discord.Color.red()))


    @commands.hybrid_command(name="disconnect", description="Disconnects the bot from the voice channel.")
    async def disconnect(self, ctx: commands.Context) -> None:
        """Simple disconnect command."""
        vc: wavelink.Player = ctx.voice_client

        channel = discord.utils.get(ctx.guild.channels, id=vc.channel.id)
        await vc.disconnect()
        await ctx.send(embed=create_embed(description=f"Disconnected from **{channel.mention}**", color=discord.Color.green()))


    @commands.hybrid_command(name="pause", description="Pauses the current track.")
    async def pause(self, ctx):
        """Simple pause command."""
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.is_playing():
            await vc.pause()
            await ctx.send(embed=create_embed(description="Paused the playback.", color=discord.Color.green()))
        else:
            await ctx.send(embed=create_embed(description="No active playback to pause.", color=discord.Color.red()))

    @commands.hybrid_command(name="resume", description="Resumes the current track.")
    async def resume(self, ctx):
        """Simple resume command."""
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.is_paused():
            await vc.resume()
            await ctx.send(embed=create_embed(description="Resumed the playback.", color=discord.Color.green()))
        else:
            await ctx.send(embed=create_embed(description="No active playback to resume.", color=discord.Color.red()))

    @commands.hybrid_command(name="now_playing", description="Shows the currently playing track.", aliases=["np"])
    async def now_playing(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.is_playing():
            current_track = vc.current
            await ctx.send(embed=create_embed(description=f"Current Track: **{current_track.title}**", color=discord.Color.green()))
        else:
            await ctx.send(embed=create_embed(description="No active playback.", color=discord.Color.red()))

    @commands.hybrid_command(name="queue", description="Shows the current queue.")
    async def queue(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.is_playing():
            current_track = vc.current
            queue_tracks = [f"{index + 1}. {track.title}" for index, track in enumerate(vc.queue)]
            queue_message = "\n".join(queue_tracks)
            await ctx.send(embed=create_embed(description=f"Current Track: {current_track.title}\nQueue:\n{queue_message}", color=discord.Color.green()))
        else:
            await ctx.send(embed=create_embed(description="No active playback or queue.", color=discord.Color.red()))

    @commands.hybrid_command(name="repeat", description="Repeats the current track.")
    async def repeat(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.is_playing():
            await vc.play(vc.current, populate=True)
            await ctx.send(embed=create_embed(description=f"Repeating: **{vc.current.title}**", color=discord.Color.green()))
        else:
            await ctx.send(embed=create_embed(description="No active playback to repeat.", color=discord.Color.red()))

    @commands.hybrid_command(name="autoplay", description="Toggles autoplay.")
    async def autoplay(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.is_playing():
            vc.autoplay = not vc.autoplay
            await ctx.send(embed=create_embed(description=f"Autoplay: **{vc.autoplay}**", color=discord.Color.green()))
        else:
            await ctx.send(embed=create_embed(description="No active playback to toggle autoplay.", color=discord.Color.red()))


async def setup(bot):
    await bot.add_cog(Music(bot))
