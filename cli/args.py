def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Run the bot in test mode')
    return parser.parse_args()
