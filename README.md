# Larry's Gym Tracker Discord Bot

A feature-rich Discord bot designed to help track and gamify your fitness journey with your friends. This bot includes features for tracking workouts, sleep, stock trading simulation, news recommendations, and more!

## Features

- 🏋️‍♂️ Daily exercise challenges and tracking
- 😴 Sleep tracking with points system
- 📈 Stock trading simulation
- 📰 AI-powered news recommendations
- 🎵 YouTube music player
- 🎂 Birthday celebrations
- 📊 Year-in-review statistics
- 🏆 Daily and monthly winner announcements

## Prerequisites

- Python 3.9+
- Discord Bot Token
- OpenAI API Key (for AI features)
- Perplexity API Key (for enhanced AI capabilities)
- Finnhub API Key (for stock trading features)
- FFmpeg (for audio playback)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Larrys_Gym_Tracker.git
cd Larrys_Gym_Tracker
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up configuration:
```bash
cp config.example.json config.json
cp .env.example .env
```
Edit `config.json` and `.env` with your own values.

## Configuration

The bot requires several configuration values to be set up. Copy `config.example.json` to `config.json` and fill in the following:

- Discord Configuration:
  - Bot Token
  - Guild ID
  - Channel IDs (text and voice)
- API Keys:
  - OpenAI
  - Perplexity
  - Finnhub
  - News API (optional)
  - Odds API (optional)
  - Dropbox (optional, for database backup)
- Custom Songs:
  - Birthday songs
  - Winner celebration songs
- User Information:
  - Display names
  - Birthdates

You can also use environment variables by copying `.env.example` to `.env` and setting your API keys there.

## Security Notes

- **Never commit your config.json or .env files** to version control
- Keep your API keys secure and rotate them periodically
- The .gitignore file is set up to exclude sensitive files, but be cautious when making changes
- Ensure your database files are adequately backed up and secured
- Consider implementing rate limiting to protect your API usage

## Usage

1. Start the bot:
```bash
python larrys_gym_tracker.py
```

2. Available Commands:
- `!log_exercise <exercise> <sets> <reps>` - Log your exercises
- `!log_sleep [yesterday] <hours>` - Track your sleep
- `!play <youtube_url>` - Play music in voice channel
- `!stocks` - View your stock portfolio
- `!leaderboard [week|month|year]` - View fitness leaderboard
- Many more! Use `!help` to see all commands

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Discord.py team for the amazing Discord API wrapper
- OpenAI and Perplexity for AI capabilities
- All contributors and users of the bot

## Support

If you encounter any issues or have questions, please open an issue on GitHub. 