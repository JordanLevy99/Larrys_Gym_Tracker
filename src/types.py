import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple, List
import datetime
import pytz

ROOT_PATH = Path(os.path.dirname(Path(os.path.abspath(__file__)).parent))


@dataclass
class BotConstants:
    TOKEN: str = ''
    DB_FILE: str = 'larrys_database.db'
    TEXT_CHANNEL: str = 'larrys-gym-logger'
    VOICE_CHANNEL: str = 'Larry\'s Gym'
    TEXT_CHANNEL_ID: int = 0  # Set defaults to 0 instead of real IDs
    VOICE_CHANNEL_ID: int = 0  # Set defaults to 0 instead of real IDs
    GUILD_ID: int = 0  # Add GUILD_ID field
    DB_PATH: Path = ROOT_PATH / 'data' / DB_FILE
    STOCK_DB_FILE: str = 'larrys_stock_exchange.db'


@dataclass
class WalkArgs:
    START_HOUR: int = 7
    WEEKEND_START_HOUR: int = 9
    LENGTH_OF_WALK_IN_MINUTES: int = 45
    MAX_ON_TIME_POINTS: int = 50
    MAX_DURATION_POINTS: int = 50
    WALK_ENDED: bool = False
    WINNER_MINUTE: int = 8
    
    @property
    def WINNER_HOUR(self) -> int:
        now = datetime.datetime.now(pytz.timezone('US/Pacific'))
        return self.WEEKEND_START_HOUR if now.weekday() >= 5 else self.START_HOUR

    @property
    def END_HOUR(self) -> int:
        now = datetime.datetime.now(pytz.timezone('US/Pacific'))
        return self.WEEKEND_START_HOUR+2 if now.weekday() >= 5 else self.START_HOUR+2

    def get_start_hour(self, dt: datetime.datetime) -> int:
        """Return the configured start hour for the provided datetime."""
        return self.WEEKEND_START_HOUR if dt.weekday() >= 5 else self.START_HOUR

@dataclass
class Songs:
    # Birthday songs and winner songs should be loaded from config.json
    # These empty defaults will be overridden by the config system
    BIRTHDAY: Dict[Tuple, Tuple] = field(default_factory=dict)
    WINNER: Dict[str, List] = field(default_factory=dict)