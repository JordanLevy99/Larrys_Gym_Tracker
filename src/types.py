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
    TEXT_CHANNEL_ID: int = 1193971930794045544
    VOICE_CHANNEL_ID: int = 1234680075962683482
    DB_PATH: Path = ROOT_PATH / 'data' / DB_FILE
    STOCK_DB_FILE: str = 'larrys_stock_exchange.db'


@dataclass
class WalkArgs:
    START_HOUR: int = 7
    WEEKEND_START_HOUR: int = 9
    #END_HOUR: int = 9
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

@dataclass
class Songs:
    BIRTHDAY: Dict[Tuple, Tuple] = field(default_factory=lambda: {
        # (month, day): (name, link)
        (1, 19): ('james', 'https://www.youtube.com/watch?v=jcZRsApNZwk'),
        (9, 27): ('jordan', 'https://www.youtube.com/watch?v=E8Jx5jOXM9Y'),
        (4, 5): ('kyle', 'https://www.youtube.com/watch?v=bujfHuKO-Vc'),
        (1, 22): ('ben', 'https://www.youtube.com/watch?v=t5r1qIY0g2g'),
        (4, 12): ('peter', 'https://www.youtube.com/watch?v=SsoIMucoHa4'),
        (1, 27): ('mikal', 'https://www.youtube.com/watch?v=Hz8-5D2dmus'),
    })

    WINNER: Dict[str, List] = field(default_factory=lambda: {
        # Provides the song name, duration, and start second
        'jam4bears': [('rocky_balboa.mp3', 15, 0),
                      ('walk_it_talk_it.mp3', 45, 40)],
        'bemno': [('wanna_be_free.mp3', 40, 0),
                  ('war_fanfare.mp3', 15, 95),
                  ('gimmick_good_weather.mp3', 15, 0),
                  ('gimmick_good_morning.mp3', 15, 0)],
        'dinkstar': [('chug_jug_with_you.mp3', 32, 1),
                     ('jesus_forgive_me_i_am_a_thot.mp3', 23, 122),
                     ('thot_tactics.mp3', 22, 109),
                     ('jump_out_the_house.mp3', 12, 7)],
        'Larry\'s Gym Bot': [('larrys_song.mp3', 26, 0)],
        'kyboydigital': [('shenanigans.mp3', 15, 13)],
        'shmeg.': [('chum_drum_bedrum.mp3', 67, 26),
                   ('whats_new_scooby_doo.mp3', 64, 0),
                   ('tnt_dynamite.mp3', 64, 18),
                   ('HEYYEYAAEYAAAEYAEYAA.mp3', 84, 0),
                   ('hyrule_field.mp3', 50, 175),
                   ('tunak_tunak.mp3', 76, 26),
                   ('vinland_saga.mp3', 75, 14),
                   ('german_soldiers_song.mp3', 37, 0),
                   ('BED_INTRUDER_SONG.mp3', 76, 0),
                   ('Medal_Of_Honor_European_Assault.mp3', 75, 77),
                   ('Klendathu_Drop.mp3', 80, 0),
                   ('The_Black_Pearl.mp3', 64, 30),
                   ('Rohan_and_Gondor_Themes.mp3', 62, 222),
                   ('The_Ecstasy_of_Gold.mp3', 107, 0),
                   ('Fergie_sings_the_national_anthem.mp3', 62, 77)],
        'shamupete': [('Bloopin.mp3', 81, 0),
                      ('chocolate_rain.mp3', 60, 0)]
    })
