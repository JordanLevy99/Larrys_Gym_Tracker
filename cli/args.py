def parse_args():
    import argparse
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Run the bot in test mode')
    parser.add_argument('--verbose', action='store_true', help='Run the bot in verbose mode')
    parser.add_argument('--local', action='store_true', help='Run the bot in local mode')

    args, _ = parser.parse_known_args()
    if 'PYTEST_CURRENT_TEST' in os.environ:
        args.local = True
    return args
