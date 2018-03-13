import argparse
import re
from urllib.parse import urlparse


def get_args():
    #
    # argparse setup
    #
    parser = argparse.ArgumentParser(
        description='A music downloader for Tidal.')

    parser.add_argument(
        '-p',
        '--preset',
        default='default',
        help='Select a download preset. Defaults to Lossless only. See /config/settings.py for presets')

    parser.add_argument(
        '-a',
        '--account',
        default='default',
        help='Select a session/account to use. Defaults to the "default" session.')

    parser.add_argument(
        '-s',
        '--skip',
        action='store_true',
        default='False',
        help='Pass this flag to skip track and continue when a track does not meet the requested quality')

    parser.add_argument(
        'urls',
        nargs='+',
        help=
        'The URLs to download. You may need to wrap the URLs in double quotes if you have issues downloading.'
    )

    return parser.parse_args()


def parse_media_option(mo):
    opts = []
    for m in mo:
        if m.startswith('http'):
            m = re.sub(r'tidal.com\/.{2}\/store\/', 'tidal.com/', m)
            m = re.sub(r'tidal.com\/store\/', 'tidal.com/', m)
            url = urlparse(m)
            components = url.path.split('/')
            if not components or len(components) <= 2:
                print('Invalid URL: ' + m)
                exit()
            type_ = components[1]
            id_ = components[2]
            if type_ == 'album':
                type_ = 'a'
            elif type_ == 'track':
                type_ = 't'
            elif type_ == 'playlist':
                type_ = 'p'
            opts.append({'type': type_, 'id': id_})
            continue

        ci = m.index(':')
        hi = m.find('#')
        hi = len(m) if hi == -1 else hi
        o = {'type': m[:ci], 'id': m[ci + 1:hi], 'index': m[hi + 1:]}
        opts.append(o)
    return opts
