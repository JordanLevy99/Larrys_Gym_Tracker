from discord.ext import commands
import asyncio
from .voice_handler import VoiceHandler
from .openai_client import OpenAIRealtimeClient
from .audio_processor import AudioProcessor

class RealtimeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_handlers = {}
        self.audio_processor = AudioProcessor()
        self.openai_client = OpenAIRealtimeClient(bot)
        print("[RealtimeCog] Initialized")

    async def get_voice_handler(self, guild_id: int) -> VoiceHandler:
        """Get or create a VoiceHandler for the guild"""
        if guild_id not in self.voice_handlers:
            print(f"[RealtimeCog] Creating new VoiceHandler for guild {guild_id}")
            self.voice_handlers[guild_id] = VoiceHandler(self.bot, self)
        return self.voice_handlers[guild_id]

    @commands.command(name='join_voice')
    async def join_voice(self, ctx):
        """Join the user's voice channel"""
        print(f"[RealtimeCog] Join voice command received from {ctx.author}")
        if not ctx.author.voice:
            print("[RealtimeCog] User not in voice channel")
            await ctx.send("You must be in a voice channel to use this command!")
            return
            
        try:
            # Get the voice handler for this guild
            voice_handler = await self.get_voice_handler(ctx.guild.id)
            
            print(f"[RealtimeCog] Attempting to connect to channel: {ctx.author.voice.channel.name}")
            success = await voice_handler.connect_to_voice(ctx.author.voice.channel)
            if success:
                print("[RealtimeCog] Voice connection successful")
                print("[RealtimeCog] Initializing OpenAI WebSocket connection")
                await self.openai_client.connect()
                await ctx.send(f"Connected to {ctx.author.voice.channel.name}!")
            else:
                print("[RealtimeCog] Voice connection failed")
                await ctx.send("Failed to connect to voice channel.")
        except Exception as e:
            print(f"[RealtimeCog] Error in join_voice: {str(e)}")
            await ctx.send(f"Error joining voice channel: {str(e)}")

    @commands.command(name='start_listening')
    async def start_listening(self, ctx):
        """Start listening to voice input"""
        print(f"[RealtimeCog] Start listening command received from {ctx.author}")
        try:
            voice_handler = await self.get_voice_handler(ctx.guild.id)
            await voice_handler.start_recording()
            # Start the processing task
            voice_handler.processing_task = asyncio.create_task(voice_handler.process_audio_queue())
            await ctx.send("Started listening to voice input!")
        except Exception as e:
            print(f"[RealtimeCog] Error in start_listening: {str(e)}")
            await ctx.send(f"Error starting voice input: {str(e)}")

    @commands.command(name='stop_listening')
    async def stop_listening(self, ctx):
        """Stop listening to voice input"""
        print(f"[RealtimeCog] Stop listening command received from {ctx.author}")
        try:
            voice_handler = await self.get_voice_handler(ctx.guild.id)
            await voice_handler.stop_recording()
            await ctx.send("Stopped listening to voice input!")
        except Exception as e:
            print(f"[RealtimeCog] Error in stop_listening: {str(e)}")
            await ctx.send(f"Error stopping voice input: {str(e)}")

    async def process_voice_stream(self, audio_data):
        """Process audio data through our pipeline"""
        try:
            user_id = audio_data['user_id']
            audio_bytes = audio_data['audio_data']
            print(f"[RealtimeCog] Received {len(audio_bytes)} bytes of audio from user {user_id}")
            
            # Process audio through our pipeline
            # 1. Remove silence
            print("[RealtimeCog] Removing silence from audio")
            processed_audio = self.audio_processor.remove_silence(audio_bytes)
            
            if processed_audio:
                print(f"[RealtimeCog] Audio after silence removal: {len(processed_audio)} bytes")
                # 2. Get transcription from OpenAI
                user = self.bot.get_user(user_id)
                username = user.name if user else str(user_id)
                print(f"[RealtimeCog] Processing audio for user: {username}")
                
                # Send to OpenAI for transcription
                transcription = await self.openai_client.process_audio(processed_audio)
                if transcription:
                    print(f"[RealtimeCog] Transcription received: {transcription}")
                    # Send transcription to the channel
                    for handler in self.voice_handlers.values():
                        if handler.voice_client and handler.voice_client.channel:
                            await handler.voice_client.channel.send(f"**{username}**: {transcription}")
                            break
            
        except Exception as e:
            print(f"[RealtimeCog] Fatal error in voice stream processing: {e}")
            import traceback
            print(traceback.format_exc())

async def setup(bot):
    print("[RealtimeCog] Setting up RealtimeCog...")
    await bot.add_cog(RealtimeCog(bot))
    print("[RealtimeCog] RealtimeCog setup complete")
