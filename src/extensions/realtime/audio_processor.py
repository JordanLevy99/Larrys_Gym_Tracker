import numpy as np
import webrtcvad
from typing import List

class AudioProcessor:
    def __init__(self, sample_rate=16000, frame_duration=30):
        self.vad = webrtcvad.Vad(3)  # Aggressiveness level 3
        self.sample_rate = sample_rate
        self.frame_duration = frame_duration
        self.frame_size = int(sample_rate * frame_duration / 1000)
        
    def frame_generator(self, audio_data: bytes) -> List[bytes]:
        """Generate frames from audio data"""
        n = len(audio_data)
        offset = 0
        while offset + self.frame_size < n:
            yield audio_data[offset:offset + self.frame_size]
            offset += self.frame_size
            
    def is_speech(self, frame: bytes) -> bool:
        """Detect if a frame contains speech"""
        return self.vad.is_speech(frame, self.sample_rate)
        
    def remove_silence(self, audio_data: bytes) -> bytes:
        """Remove silence from audio data"""
        frames = list(self.frame_generator(audio_data))
        voiced_frames = [f for f in frames if self.is_speech(f)]
        return b''.join(voiced_frames) 