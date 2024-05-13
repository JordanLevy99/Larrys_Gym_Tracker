import discord
from discord.ext import commands
import yt_dlp


class YoutubeMusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def play(self, ctx, url: str):
        # Find the voice channel with the most members
        voice_channel = await self.__connect_to_voice_channel(ctx)

        # Download and play song
        ydl_opts = {'format': 'bestaudio'}

        with yt_dlp.YoutubeDL({'extract_audio': True, 'format': 'bestaudio', 'outtmpl': '%(title)s.mp3'}) as video:
            info_dict = video.extract_info(url, download=True)
            video_title = info_dict['title']
            print(video_title)
            video.download(url)
            print("Successfully Downloaded - see local folder on Google Colab")
            voice_channel.play(discord.FFmpegPCMAudio(f'{video_title}.mp3'))
        # with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        #     info = ydl.extract_info(url, download=False)
        #     print(info['formats'][0])
        #     url2 = info['formats'][0]['url']
        #     voice_channel.play(discord.FFmpegPCMAudio(url2))
        #     await ctx.send('Now playing...')

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
