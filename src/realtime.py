import logging
from discord.ext import commands
import asyncio
import websockets
import os
import json
from websockets.exceptions import InvalidStatusCode

from src.voice_capture import VoiceCaptureCog


class WebSocketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.websocket = None

    async def connect_to_websocket(self):
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        headers = {
            "Authorization": "Bearer " + os.getenv("OPENAI_API_KEY"),
            "OpenAI-Beta": "realtime=v1",
        }

        while True:
            try:
                async with websockets.connect(url, extra_headers=headers) as ws:
                    self.websocket = ws
                    if 'VoiceCaptureCog' not in self.bot.discord_client.cogs:
                        await self.bot.discord_client.add_cog(VoiceCaptureCog(self.bot, self.websocket))
                        print("VoiceCaptureCog added to bot.")
                    print("Connected to server.")

                    # Send initial message
                    initial_message = {
                        "type": "response.create",
                        "response": {
                            "modalities": ["audio", "text"],
                            "instructions": "Only respond to messages if the user says 'Hey ChatGPT' make sure to "
                                            "respond in english and be a helpful assistant",
                        }
                    }
                    await ws.send(json.dumps(initial_message))

                    await self.receive_messages(ws)
            except InvalidStatusCode as e:
                if e.status_code == 403:
                    logging.error("Failed to connect to WebSocket server: HTTP 403 Forbidden. Check your API key and permissions.")
                    break
                else:
                    logging.error(f"Failed to connect to WebSocket server: {e}")
                    await asyncio.sleep(5)
            except websockets.ConnectionClosed:
                print("Connection closed, retrying in 5 seconds...")
                await asyncio.sleep(5)

    async def receive_messages(self, ws):
        print('receiving messages')
        async for message in ws:
            with open('responses.json', 'a') as f:
                json.dump(json.loads(message), f)
                f.write('\n')
                print(f"Received message: {message}")
                if 'response.audio.done' in message['type']:
                    print("Audio response received.")
                    # Save audio to file
                    audio_data = message['response']['audio']['data']
                    audio = base64.b64decode(audio_data)
                    with open('response.wav', 'wb') as f:
                        f.write(audio)
                    print("Audio saved to response.wav")

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.discord_client.loop.create_task(self.connect_to_websocket())

    def cog_unload(self):
        if self.websocket:
            self.websocket.close()

    @commands.command(name='check_connection')
    async def check_connection(self, ctx):
        if self.websocket and self.websocket.open:
            await ctx.send("WebSocket is connected.")
        else:
            await ctx.send("WebSocket is not connected.")
