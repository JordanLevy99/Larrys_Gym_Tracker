import asyncio
import base64
import json
import logging
import time
import discord
from discord.ext import commands, voice_recv
import wave

from discord.ext.voice_recv import AudioSink, BasicSink
import io
import json
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
class VoiceCaptureCog(commands.Cog):
    def __init__(self, bot, websocket):
        self.bot = bot
        self.websocket = websocket
        self.audio_buffer = []
        self.sink = None

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            vc = await channel.connect(cls=voice_recv.VoiceRecvClient)
            self.sink = StreamingSink(self.callback, self.websocket, self.bot)
            vc.listen(self.sink)
        else:
            await ctx.send("You are not connected to a voice channel.")

    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        else:
            await ctx.send("I am not connected to a voice channel.")

    @commands.command()
    async def save_audio(self, ctx, filename: str):
        self._save_audio()
        await ctx.send(f"Audio saved to {filename}")

    def _save_audio(self):
        with wave.open('audio.wav', 'wb') as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(48000)
            f.writeframes(b''.join(self.audio_buffer))
            print("Audio saved to audio.wav")


    def callback(self, user, data: voice_recv.VoiceData):
        self.audio_buffer.append(data.pcm)
        self.sink.audio_buffer.append(data.pcm)


class StreamingSink(BasicSink):
    def __init__(self, callback, websocket, bot):
        super().__init__(callback)
        self.websocket = websocket
        self.audio_buffer = []
        self.bot = bot

    @AudioSink.listener()
    def on_voice_member_speaking_start(self, member: discord.Member):
        print(f"{member} has started speaking")
        self.timer = time.time()

    @AudioSink.listener()
    def on_voice_member_speaking_stop(self, member: discord.Member):
        print(f"{member} has stopped speaking")
        total_time = time.time() - self.timer
        print(f"Total speaking time: {total_time} seconds")
        self.handle_speaking_stop(total_time)

    def handle_speaking_stop(self, total_time):
        if total_time > 2:
            self.save_audio()
            print("Sending audio to websocket")
            self.bot.discord_client.loop.create_task(self.send_audio_to_websocket())

    def save_audio(self):
        with wave.open('audio.wav', 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(24000)
            f.writeframes(b''.join(self.audio_buffer))
            print("Audio saved to audio.wav")

    async def send_audio_to_websocket(self):
        print("Sending audio to websocket 22")
        logging.info("send_audio_to_websocket started")

        # with wave.open('audio.wav', 'rb') as audio_file:
        #     frames = audio_file.readframes(audio_file.getnframes())
        #     print(frames)
        #     float32_array = [frame / 32768.0 for frame in frames]
        #
        # base64_audio_data = self.base64_encode_audio(float32_array)
        # base64_audio_data = self.base64_encode_audio(self.audio_buffer)

        # base64_audio_data = base64.b64encode(b''.join(self.audio_buffer)).decode()
        #
        # event = {
        #     "type": "conversation.item.create",
        #     "item": {
        #         "type": "message",
        #         "role": "user",
        #         "content": [
        #             {
        #                 "type": "input_audio",
        #                 "audio": base64_audio_data
        #             }
        #         ]
        #     }
        # }

        event = self.audio_to_item_create_event()
        await self.websocket.send(event)
        await self.websocket.send(json.dumps({"type": "response.create"}))
        self.audio_buffer = []

    def audio_to_item_create_event(self) -> str:
        # Load the audio file from the byte stream

        audio_data = b''.join(self.audio_buffer)
        pcm_audio = AudioSegment(
            audio_data,
            frame_rate=24000,
            sample_width=2,
            channels=1
        ).raw_data
        # audio = AudioSegment.from_file(io.BytesIO(b''.join(self.audio_buffer)))
        #
        # # Resample to 24kHz mono pcm16
        # pcm_audio = audio.set_frame_rate(24000).set_channels(1).set_sample_width(2).raw_data

        # Encode to base64 string
        pcm_base64 = base64.b64encode(pcm_audio).decode()

        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{
                    "type": "input_audio",
                    "audio": pcm_base64
                }]
            }
        }
        return json.dumps(event)


    def base64_encode_audio(self, float32_array):
        pcm16_array = self.float_to_16bit_pcm(float32_array)
        return base64.b64encode(pcm16_array).decode('utf-8')

    def float_to_16bit_pcm(self, float32_array):
        pcm16_array = bytearray()
        for sample in float32_array:
            s = max(-1, min(1, sample))
            pcm16_array.extend(int((s * 32767.0) if s >= 0 else (s * 32768.0)).to_bytes(2, byteorder='little', signed=True))
        return pcm16_array

    # @AudioSink.listener()
    # def on_voice_member_disconnect(self, member: discord.Member, ssrc: int | None):
    #     print(f"{member} has disconnected")
    #     self.do_something_like_handle_disconnect(ssrc)
