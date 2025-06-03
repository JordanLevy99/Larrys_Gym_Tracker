def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Run the bot in test mode')
    parser.add_argument('--verbose', action='store_true', help='Run the bot in verbose mode')
    parser.add_argument('--local', action='store_true', help='Run the bot in local mode')
    args, _ = parser.parse_known_args()
    return args
