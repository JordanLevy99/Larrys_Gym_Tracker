from pathlib import Path

import discord
from discord.ext import commands
import yt_dlp

from src.types import ROOT_PATH
from src.util import play_audio, get_mp3_duration


class YoutubeMusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.queues = {}

    @commands.command()
    async def play(self, ctx, url: str):
        guild_id = ctx.guild.id
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        self.queues[guild_id].append(url)
        print(f"Added {url} to the queue")
        print(self.queues[guild_id])

        # If the bot is not currently playing anything, start playing
        voice_channel = discord.utils.get(self.bot.discord_client.voice_clients, guild=ctx.guild)
        if not voice_channel or not voice_channel.is_playing():
            await self.start_playing(ctx)
        else:
            await ctx.send(f"Added {url} to the queue")

    @commands.command()
    async def queue(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in self.queues and self.queues[guild_id]:
            await ctx.send(f"Current queue: {self.queues[guild_id]}")
        else:
            await ctx.send("No songs in queue")

    @commands.command()
    async def pause(self, ctx):
        voice_channel = discord.utils.get(self.bot.discord_client.voice_clients, guild=ctx.guild)
        if voice_channel:
            voice_channel.pause()
            print("Paused playback")

    @commands.command()
    async def resume(self, ctx):
        voice_channel = discord.utils.get(self.bot.discord_client.voice_clients, guild=ctx.guild)
        if voice_channel:
            voice_channel.resume()
            print("Resumed playback")

    # @commands.command()
    # async def rewind(self, ctx, seconds: int):
    #     """Rewind audio playback."""
    #     voice_client = ctx.message.guild.voice_client
    #     if voice_client.is_playing():
    #         voice_client.stop()
    #         self.current_playback_position = max(0, self.current_playback_position - seconds)
    #         await play_audio(voice_client, self.current_file_path, self.bot.backend_client,
    #                          start_second=self.current_playback_position)

    async def start_playing(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in self.queues and self.queues[guild_id]:
            url = self.queues[guild_id].pop(0)

            ydl_opts = {
                'extract_audio': True,
                'format': 'bestaudio',
                'outtmpl': 'data/%(title)s.%(ext)s',
                'proxy': 'http://159.89.227.166:3128'
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_title = info['title']
                file_path = ydl.prepare_filename(info)
                duration = info['duration']
                print(f"Duration: {duration}")
                print(f'Now playing {file_path}...')
                await ctx.send(f'Now playing {video_title}...')
                voice_channel = await self.__connect_to_voice_channel(ctx)
                await play_audio(voice_channel, file_path, self.bot.backend_client,
                                 duration=duration, start_second=0, download=False)
            if self.queues[guild_id]:
                await self.start_playing(ctx)

    @commands.command()
    async def skip(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in self.queues:
            if self.queues[guild_id]:
                self.queues[guild_id].pop(0)
                print("Skipped current song")
                if self.queues[guild_id]:
                    await self.start_playing(ctx)
            else:
                print("No songs in queue")

    @commands.command()
    async def stop(self, ctx):
        voice_channel = discord.utils.get(self.bot.discord_client.voice_clients, guild=ctx.guild)
        if voice_channel:
            voice_channel.stop()
            await voice_channel.disconnect()
            print("Stopped playback and disconnected from voice channel")

    async def __connect_to_voice_channel(self, ctx):
        max_members = 0
        target_channel = None
        for channel in ctx.guild.voice_channels:
            if len(channel.members) > max_members:
                max_members = len(channel.members)
                target_channel = channel
                print(target_channel.name, max_members)

        if not target_channel:
            await ctx.send("No active voice channels found")
            return

        voice_channel = discord.utils.get(self.bot.discord_client.voice_clients, guild=ctx.guild)
        if not voice_channel or voice_channel.channel != target_channel:
            if voice_channel:
                await voice_channel.disconnect()
            voice_channel = await target_channel.connect()
        return voice_channel
