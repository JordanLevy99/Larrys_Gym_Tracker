import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class DiscordConfig:
    token: str
    guild_id: int
    text_channel_name: str
    text_channel_id: int
    voice_channel_name: str
    voice_channel_id: int

    @classmethod
    def from_dict(cls, data: Dict) -> 'DiscordConfig':
        return cls(
            token=data['token'],
            guild_id=int(data['guild_id']),
            text_channel_name=data['channels']['text']['name'],
            text_channel_id=int(data['channels']['text']['id']),
            voice_channel_name=data['channels']['voice']['name'],
            voice_channel_id=int(data['channels']['voice']['id'])
        )

@dataclass
class DatabaseConfig:
    main_db: str
    stock_db: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'DatabaseConfig':
        return cls(**data)

@dataclass
class APIConfig:
    openai: str
    perplexity: str
    finnhub: str
    news: str = ""
    odds: str = ""
    dropbox_key: str = ""
    dropbox_secret: str = ""
    dropbox_refresh_token: str = ""
    gemini: str = ""

    @classmethod
    def from_dict(cls, data: Dict) -> 'APIConfig':
        # Initialize with required keys
        config = cls(
            openai=data.get('openai', ''),
            perplexity=data.get('perplexity', ''),
            finnhub=data.get('finnhub', '')
        )
        
        # Add optional keys if they exist
        if 'news' in data:
            config.news = data['news']
        if 'odds' in data:
            config.odds = data['odds']
        if 'dropbox_key' in data:
            config.dropbox_key = data['dropbox_key']
        if 'dropbox_secret' in data:
            config.dropbox_secret = data['dropbox_secret']
        if 'dropbox_refresh_token' in data:
            config.dropbox_refresh_token = data['dropbox_refresh_token']
        if 'gemini' in data:
            config.gemini = data['gemini']
            
        return config

@dataclass
class BirthdaySong:
    month: int
    day: int
    song_link: str
    song_file: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'BirthdaySong':
        return cls(**data)

@dataclass
class WinnerSong:
    file: str
    duration: int
    start_second: int

    @classmethod
    def from_dict(cls, data: Dict) -> 'WinnerSong':
        return cls(**data)

class Config:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path('config.json')
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found at {self.config_path}. Please copy config.example.json to config.json and fill in your values."
            )
        
        with open(self.config_path) as f:
            config_data = json.load(f)
        
        self.discord = DiscordConfig.from_dict(config_data['discord'])
        self.database = DatabaseConfig.from_dict(config_data['database'])
        self.api_keys = APIConfig.from_dict(config_data['api_keys'])
        
        self.birthday_songs: Dict[str, BirthdaySong] = {
            username: BirthdaySong.from_dict(data)
            for username, data in config_data.get('birthday_songs', {}).items()
        }
        
        self.winner_songs: Dict[str, List[WinnerSong]] = {
            username: [WinnerSong.from_dict(song_data) for song_data in songs]
            for username, songs in config_data.get('winner_songs', {}).items()
        }
        
        # Store enabled extensions
        self.enabled_extensions = config_data.get('enabled_extensions', [])

    @property
    def birthday_tuples(self) -> Dict[tuple, tuple]:
        """Convert birthday_songs to the format expected by the existing code"""
        return {
            (song.month, song.day): (username.lower(), song.song_link)
            for username, song in self.birthday_songs.items()
        }

    @property
    def winner_song_tuples(self) -> Dict[str, List[tuple]]:
        """Convert winner_songs to the format expected by the existing code"""
        return {
            username: [(song.file, song.duration, song.start_second) for song in songs]
            for username, songs in self.winner_songs.items()
        } 