from pathlib import Path

import discord
from discord.ext import commands
import yt_dlp

from src.types import ROOT_PATH
from src.util import play_audio, get_mp3_duration


class YoutubeMusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def play(self, ctx, url: str):
        # Find the voice channel with the most members

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

        if not target_channel:
            await ctx.send("No active voice channels found")
            return

        voice_channel = discord.utils.get(self.bot.discord_client.voice_clients, guild=ctx.guild)
        if not voice_channel or voice_channel.channel != target_channel:
            if voice_channel:
                await voice_channel.disconnect()
            voice_channel = await target_channel.connect()
        return voice_channel
