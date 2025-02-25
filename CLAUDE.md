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