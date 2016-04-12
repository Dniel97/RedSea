import argparse

def get_args():
    #
    # argparse setup
    #
    parser = argparse.ArgumentParser(description='A music downloader for Tidal.')

    parser.add_argument('-o', 
        default='rs_config.json',
        metavar='filename', 
        help='The path to a config file. If not supplied, uses `rs_config.json\' in the current directory.')
        
    parser.add_argument('-q',
        metavar='quality',
        help='Override the quality specified in the config file. See readme for valid values.')

    parser.add_argument('media', nargs='+', help='The media to download. See readme for media download format.')

    return parser.parse_args()

def parse_media_option(mo):
    opts = []
    for m in mo:
        ci = m.index(':')
        hi = m.find('#')
        hi = len(m) if hi == -1 else hi
        o = {
            'type': m[:ci],
            'id': m[ci + 1:hi],
            'index': m[hi + 1:]
        }
        opts.append(o)
    return opts