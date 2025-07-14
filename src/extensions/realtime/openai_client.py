import asyncio
from openai import AsyncOpenAI
from typing import AsyncGenerator, Optional

class OpenAIRealtimeClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-realtime-preview-2024-10-01"):
        print("[OpenAIClient] Initializing with realtime API")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.connection = None
        print("[OpenAIClient] Initialized with model:", model)
        
    async def connect(self):
        """Establish WebSocket connection with OpenAI's realtime API"""
        print("[OpenAIClient] Connecting to realtime API")
        try:
            async with self.client.beta.realtime.connect(model="gpt-4o-realtime-preview-2024-10-01") as connection:
                self.connection = connection
                # Configure session for audio input/output
                await self.connection.session.update(session={
                    'modalities': ['audio', 'text']
                })
                print("[OpenAIClient] Connected successfully")
                return True
        except Exception as e:
            print(f"[OpenAIClient] Connection error: {e}")
            return False
        
    async def process_audio(self, audio_data: bytes) -> AsyncGenerator[str, None]:
        """Process audio using OpenAI's realtime API"""
        if not self.connection:
            print("[OpenAIClient] No active connection")
            raise RuntimeError("No active connection to OpenAI")
            
        try:
            print(f"[OpenAIClient] Processing {len(audio_data)} bytes of audio")
            
            # Send audio data
            await self.connection.conversation.item.create(
                item={
                    "type": "message",
                    "role": "user",
                    "content": [{
                        "type": "audio",
                        "data": audio_data,
                        "encoding": "pcm",
                        "sample_rate": 16000,
                        "channels": 1
                    }]
                }
            )
            
            # Request response
            await self.connection.response.create()
            
            # Process events
            async for event in self.connection:
                if event.type == 'error':
                    print(f"[OpenAIClient] Error event: {event.error.message}")
                    raise RuntimeError(f"OpenAI error: {event.error.message}")
                    
                elif event.type == 'response.text.delta':
                    print(f"[OpenAIClient] Received text delta: {event.delta}")
                    yield event.delta
                    
                elif event.type == 'response.text.done':
                    print("[OpenAIClient] Text response complete")
                    break
                    
                elif event.type == "response.done":
                    print("[OpenAIClient] Response complete")
                    break
                    
        except Exception as e:
            print(f"[OpenAIClient] Error processing audio: {e}")
            raise
                
    async def close(self):
        """Close the WebSocket connection"""
        print("[OpenAIClient] Closing connection")
        if self.connection:
            await self.connection.close()
            self.connection = None
            print("[OpenAIClient] Connection closed") 