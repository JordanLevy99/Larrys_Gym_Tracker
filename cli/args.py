def parse_args(args=None):
    """Parse command line arguments.

    Using ``parse_known_args`` ensures unrecognised arguments from other tools
    (e.g. ``pytest -q``) don't cause a ``SystemExit`` during import.
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Run the bot in test mode')
    parser.add_argument('--verbose', action='store_true', help='Run the bot in verbose mode')
    parser.add_argument('--local', action='store_true', help='Run the bot in local mode')

    if args is None:
        args = sys.argv[1:]

    return parser.parse_known_args(args)[0]
