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
- FFmpeg (for audio playback)
- Optional API Keys (for specific extensions):
  - Finnhub API Key (for stock trading features)
  - News API Key (for news recommendations)
  - Odds API Key (for sports betting features)

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

4. Run the configuration web app:
```bash
python web_config/run.py
```

5. Open your browser and navigate to http://localhost:5000 to configure the bot.

## Configuration

### Web Configuration Interface

The easiest way to configure the bot is through the web interface:

1. Run the web configuration app: `python web_config/run.py`
2. Navigate to http://localhost:5000 in your browser
3. Fill in all required fields:
   - Discord Bot Token (follow the Discord Bot Creation Guide)
   - Server and Channel IDs
   - API Keys for enabled extensions
4. Choose which extensions to enable
5. Add users, birthday songs, and winner songs
6. Click "Save Configuration"

### Creating a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Add a bot user under the "Bot" section
4. Enable necessary intents (MESSAGE CONTENT and SERVER MEMBERS)
5. Generate and copy your bot token
6. Create an invite URL with bot and application.commands scopes
7. Invite the bot to your server

Detailed instructions with screenshots are available in the web configuration app.

### Manual Configuration

If you prefer to configure manually, copy `config.example.json` to `config.json` and edit it:

```bash
cp config.example.json config.json
```

The configuration file includes:

- Discord Configuration (token, guild_id, channel IDs)
- Database settings
- API Keys for various services
- Enabled Extensions list
- Custom Songs for birthdays and winners
- User Information (display names, birthdates)

## Extensions

The bot has a modular design with optional extensions:

- **Stock Trading** - Simulated stock market trading (requires Finnhub API)
- **YouTube Music Player** - Play music in voice channels (requires FFmpeg)
- **News Recommender** - AI-powered news article recommendations (requires News API)
- **Exercise of the Day** - Daily exercise challenge announcements (requires OpenAI API)
- **Sleep Tracker** - Track user sleep patterns and award points
- **Year in Review** - Generate year-end activity summaries
- **Voice Transcription** - Real-time voice chat transcription (requires OpenAI)
- **Sports Betting** - Sports odds information (requires Odds API)

Enable or disable extensions through the web configuration interface.

## Security Notes

- **Never commit your config.json file** to version control
- Keep your API keys secure and rotate them periodically
- Ensure your database files are adequately backed up and secured
- Consider implementing rate limiting to protect your API usage

## Usage

1. Start the bot:
```bash
python larrys_gym_tracker.py
```

Optional flags:
- `--test` - Use test_config.json instead of config.json
- `--local` - Use local file storage instead of Dropbox
- `--verbose` - Enable verbose logging

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