from pathlib import Path

import discord
from discord.ext import commands
from src.types import ROOT_PATH
from src.util import play_audio
from src.util import get_mp3_duration


class OpenAICog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.exercise_map = {}

    @commands.command()
    async def ask_larry(self, ctx, *args):
        query = ' '.join(args)
        response = self.create_chat(self.bot.perplexity_client, query,
                                    system_message='Keep your answers concise '
                                                   'and to the point.',
                                    temperature=0.5,
                                    model='llama-3.1-sonar-large-128k-online')

        remote_speech_file_path = Path('data') / "response.mp3"
        local_speech_file_path = ROOT_PATH / remote_speech_file_path
        self.produce_tts_audio(self.bot.openai_client, response, local_speech_file_path)
        voice_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.VOICE_CHANNEL_ID)

        if voice_channel and len(voice_channel.members) >= 1:
            try:
                voice_client = await voice_channel.connect()
            except discord.errors.ClientException as e:
                print(str(e))
                print(
                    f'Already connected to a voice channel.')

            voice_client = self.bot.discord_client.voice_clients[0]
            text_channel = self.bot.discord_client.get_channel(self.bot.bot_constants.TEXT_CHANNEL_ID)
            await text_channel.send(response)
            await play_audio(voice_client, str(remote_speech_file_path), self.bot.backend_client,
                             duration=get_mp3_duration(local_speech_file_path),
                             start_second=0, download=False)
        else:
            await ctx.send(response)

    @staticmethod
    def produce_tts_audio(client, response, speech_file_path):
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=response
        )
        response.write_to_file(speech_file_path)

    @staticmethod
    def create_chat(client, user_message, system_message='', temperature=0.65, model='gpt-4o'):
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            model=model,
            temperature=temperature
        )
        return response.choices[0].message.content
