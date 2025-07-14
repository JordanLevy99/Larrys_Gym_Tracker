# Development Guidelines for Larry's Gym Tracker

## Setup & Installation

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies 
pip install -r requirements.txt
```

## Running the Bot

```bash
# Normal mode
python larrys_gym_tracker.py

# Test mode (uses test_config.json)
python larrys_gym_tracker.py --test

# Local mode (uses local file storage instead of Dropbox)
python larrys_gym_tracker.py --local

# Verbose mode
python larrys_gym_tracker.py --verbose
```

## Testing

```bash
# Run all tests
python -m unittest discover tests

# Run a specific test file
python -m unittest tests/test_larrys_stock_trader.py

# Run a specific test case
python -m unittest tests.test_larrys_stock_trader.LarrysStockTraderTests
```

## Code Style Guidelines

- **Imports**: Group imports by standard library, third-party libraries, and local modules with a blank line between groups
- **Type Hints**: Use Python type hints for function parameters and return values
- **Naming**: 
  - Classes: PascalCase (`LarrysBot`)
  - Functions/methods: snake_case (`get_user_portfolio`)
  - Constants: UPPER_SNAKE_CASE (`TEXT_CHANNEL_ID`)
- **Error Handling**: Use try/except blocks with specific exceptions and meaningful error messages
- **Organization**: Group related functionality into separate modules and classes
- **Documentation**: Include docstrings for classes and methods explaining purpose and parameters

## Current Branch Status: feature/open-source-prep

### Recent Development Summary
The project has been undergoing significant preparation for open source release. The recent commits show:

1. **Open Source Preparation** (commits: 9968a9c, 1da51fa, a281384):
   - Added configuration system with `config.example.json` and `.env.example`
   - Improved security measures for public release
   - Added comprehensive README.md and setup documentation
   - Updated .gitignore for better file management

2. **Web Configuration Interface** (commit: 5921b0f):
   - Added Flask-based web configuration interface in `web_config/`
   - Created templates for easier setup and Discord integration guide
   - Added static assets (CSS/JS) for web interface

3. **Bot Improvements** (commits: ea49e99, c37279f):
   - Updated exercise.py and HTML templates
   - Enhanced bot initialization with test_config.json support
   - Added command-line argument support (--test, --local, --verbose)

### Current Uncommitted Changes
- **web_config/run.py**: Fixed import path from `web_config.app` to `app` (line 1)
- **Untracked files**: Various audio files, data files, and development artifacts that should likely be gitignored

### Files Modified in Recent Commits
- Configuration files: .env.example, config.example.json, requirements.txt
- Core bot files: src/bot.py, src/config.py, src/exercise.py, src/types.py
- Web interface: web_config/ directory with Flask app, templates, and static files
- Documentation: README.md, CLAUDE.md, setup_server.sh
- Extensions: gambling/sports_betting.py, news/larrys_news_recommender.py

### Next Steps
The branch is 1 commit ahead of origin and ready for the import path fix to be committed.