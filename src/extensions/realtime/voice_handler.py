import asyncio
import discord
from discord.ext import voice_recv
import audioop
from typing import Optional, Dict
from queue import Queue
import time

class VoiceHandler:
    def __init__(self, bot, realtime_cog):
        print("[VoiceHandler] Initializing VoiceHandler...")
        self.bot = bot
        self.realtime_cog = realtime_cog
        self.voice_client: Optional[voice_recv.VoiceRecvClient] = None
        self.recording = False
        self.audio_queue = asyncio.Queue()
        self.current_sink = None
        self.processing_task = None
        print("[VoiceHandler] Initialization complete")

    async def connect_to_voice(self, voice_channel):
        """Connect to a voice channel using VoiceRecvClient"""
        print(f"[VoiceHandler] Attempting to connect to voice channel: {voice_channel.name}")
        try:
            if self.voice_client and self.voice_client.is_connected():
                print("[VoiceHandler] Moving existing voice client to new channel")
                await self.voice_client.move_to(voice_channel)
            else:
                print("[VoiceHandler] Creating new voice client connection")
                self.voice_client = await voice_channel.connect(
                    cls=voice_recv.VoiceRecvClient,
                    self_deaf=True  # Reduce server load
                )
            print("[VoiceHandler] Voice connection successful")
            return True
        except Exception as e:
            print(f"[VoiceHandler] Error connecting to voice: {e}")
            return False

    async def process_audio_queue(self):
        """Process audio data from the queue and send to RealtimeCog"""
        print("[VoiceHandler] Starting audio queue processing")
        try:
            while self.recording:
                try:
                    # Get data from queue
                    data_package = await self.audio_queue.get()
                    print(f"[VoiceHandler] Got audio package from queue, sending to RealtimeCog")
                    
                    # Send to RealtimeCog's processing pipeline
                    await self.realtime_cog.process_voice_stream(data_package)
                    
                except Exception as e:
                    print(f"[VoiceHandler] Error processing audio: {e}")
                    import traceback
                    print(traceback.format_exc())
                    
        except Exception as e:
            print(f"[VoiceHandler] Error in audio processing loop: {e}")
            import traceback
            print(traceback.format_exc())
        finally:
            print("[VoiceHandler] Audio processing loop ended")

    class AudioReceiveSink(voice_recv.AudioSink):
        def __init__(self, handler):
            print("[AudioReceiveSink] Initializing AudioReceiveSink")
            super().__init__()
            self.handler = handler
            self.buffer = bytearray()
            self.total_audio_processed = 0
            print("[AudioReceiveSink] Initialization complete")
            
        def write(self, user: discord.User, data: voice_recv.VoiceData):
            """Process incoming audio data"""
            if user and self.handler.recording and data.pcm:
                try:
                    print(f"[AudioReceiveSink] Received audio data from {user.name}, size: {len(data.pcm)} bytes")
                    
                    # Add to buffer
                    self.buffer.extend(data.pcm)
                    print(f"[AudioReceiveSink] Buffer size after extend: {len(self.buffer)} bytes")
                    
                    # Process in chunks of 30ms (48000Hz * 0.03 * 4 bytes)
                    CHUNK_SIZE = 48000 * 2 * 2 * 30 // 1000  # ~5760 bytes
                    
                    while len(self.buffer) >= CHUNK_SIZE:
                        chunk = bytes(self.buffer[:CHUNK_SIZE])
                        self.buffer = self.buffer[CHUNK_SIZE:]
                        
                        # Downsample chunk to 16kHz for OpenAI
                        resampled = audioop.ratecv(
                            chunk,
                            2,  # width
                            2,  # channels 
                            48000,  # source rate
                            16000,  # target rate
                            None  # state
                        )[0]
                        
                        self.total_audio_processed += len(resampled)
                        print(f"[AudioReceiveSink] Resampled chunk: {len(resampled)} bytes. Total processed: {self.total_audio_processed}")
                        
                        # Create the data package
                        data_package = {
                            'user_id': user.id,
                            'audio_data': resampled,
                            'timestamp': time.time()
                        }
                        
                        # Use asyncio.Queue's put_nowait through event loop
                        asyncio.run_coroutine_threadsafe(
                            self.handler.audio_queue.put(data_package),
                            self.handler.bot.discord_client.loop
                        )
                        print(f"[AudioReceiveSink] Queued audio package for processing")
                            
                except Exception as e:
                    print(f"[AudioReceiveSink] Error processing audio data: {e}")
                    import traceback
                    print(traceback.format_exc())

        def cleanup(self):
            """Cleanup resources"""
            print("[AudioReceiveSink] Cleaning up AudioReceiveSink")
            self.buffer.clear()

        @voice_recv.AudioSink.listener()
        def on_voice_member_speaking_start(self, member: discord.Member):
            print(f"[AudioReceiveSink] {member.name} started speaking")
            
        @voice_recv.AudioSink.listener()
        def on_voice_member_speaking_stop(self, member: discord.Member):
            print(f"[AudioReceiveSink] {member.name} stopped speaking")

        def wants_opus(self) -> bool:
            """Required override to indicate if we want opus encoded audio"""
            return False  # We want PCM data for processing

    async def start_recording(self):
        """Start capturing audio using VoiceRecvClient"""
        if not self.voice_client:
            print("[VoiceHandler] Error: Not connected to a voice channel")
            raise ValueError("Not connected to a voice channel")

        try:
            print("[VoiceHandler] Starting recording session")
            self.recording = True
            print("[VoiceHandler] Creating new AudioReceiveSink")
            self.current_sink = self.AudioReceiveSink(self)
            print("[VoiceHandler] Starting voice client listener")
            self.voice_client.listen(self.current_sink)
            
            print("[VoiceHandler] Recording started successfully")
            
            # Keep the recording running
            while self.recording:
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"[VoiceHandler] Error in recording: {e}")
            self.recording = False
            raise

    async def stop_recording(self):
        """Stop capturing audio"""
        print("[VoiceHandler] Stopping recording session")
        self.recording = False
        
        if self.voice_client and self.voice_client.is_listening():
            print("[VoiceHandler] Stopping voice client listener")
            self.voice_client.stop_listening()
            
        if self.current_sink:
            print("[VoiceHandler] Cleaning up current sink")
            self.current_sink.cleanup()
            self.current_sink = None
            
        if self.voice_client:
            print("[VoiceHandler] Disconnecting voice client")
            await self.voice_client.disconnect()
            self.voice_client = None
            
        print("[VoiceHandler] Voice recording stopped and cleaned up")

    def is_speaking(self, member: discord.Member) -> bool:
        """Check if a member is currently speaking"""
        if self.voice_client:
            speaking = bool(self.voice_client.get_speaking(member))
            print(f"[VoiceHandler] Checking speaking status for {member.name}: {speaking}")
            return speaking
        print(f"[VoiceHandler] No voice client to check speaking status for {member.name}")
        return False


