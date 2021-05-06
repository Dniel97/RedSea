import argparse
import re
from urllib.parse import urlparse
from os import path


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
        '-b',
        '--bruteforce',
        action='store_true',
        default=False,
        help='Brute force the download with all available accounts')

    parser.add_argument(
        '-a',
        '--account',
        default='',
        help='Select a session/account to use. Defaults to the "default" session.')

    parser.add_argument(
        '-s',
        '--skip',
        action='store_true',
        default=False,
        help='Pass this flag to skip track and continue when a track does not meet the requested quality')

    parser.add_argument(
        '-o',
        '--overwrite',
        action='store_true',
        default=False,
        help='Overwrite existing files [Default=skip]'
    )

    parser.add_argument(
        '--resumeon',
        type=int,
        help='If ripping a single playlist, resume on the given track number.'
    )

    parser.add_argument(
        'urls',
        nargs='+',
        help='The URLs to download. You may need to wrap the URLs in double quotes if you have issues downloading.'
    )

    parser.add_argument(
        '-f',
        '--file',
        action='store_const',
        const=True,
        default=False,
        help='The URLs to download inside a .txt file with a single track/album/artist each line.'
    )

    args = parser.parse_args()
    if args.resumeon and args.resumeon <= 0:
        parser.error('--resumeon must be a positive integer')

    # Check if only URLs or a file exists
    if len(args.urls) > 1 and args.file:
        parser.error('URLs and -f (--file) cannot be used at the same time')

    return args


def parse_media_option(mo, is_file):
    opts = []
    if is_file:
        file_name = str(mo[0])
        mo = []
        if path.exists(file_name):
            file = open(file_name, 'r')
            lines = file.readlines()
            for line in lines:
                mo.append(line.strip())
        else:
            print("\t File " + file_name + " doesn't exist")
    for m in mo:
        if m.startswith('http'):
            m = re.sub(r'tidal.com\/.{2}\/store\/', 'tidal.com/', m)
            m = re.sub(r'tidal.com\/store\/', 'tidal.com/', m)
            m = re.sub(r'tidal.com\/browse\/', 'tidal.com/', m)
            url = urlparse(m)
            components = url.path.split('/')
            if not components or len(components) <= 2:
                print('Invalid URL: ' + m)
                exit()
            if len(components) == 5:
                type_ = components[3]
                id_ = components[4]
            else:
                type_ = components[1]
                id_ = components[2]
            if type_ == 'album':
                type_ = 'a'
            elif type_ == 'track':
                type_ = 't'
            elif type_ == 'playlist':
                type_ = 'p'
            elif type_ == 'artist':
                type_ = 'r'
            elif type_ == 'video':
                type_ = 'v'
            opts.append({'type': type_, 'id': id_})
            continue
        elif ':' in m and '#' in m:
            ci = m.index(':')
            hi = m.find('#')
            hi = len(m) if hi == -1 else hi
            o = {'type': m[:ci], 'id': m[ci + 1:hi], 'index': m[hi + 1:]}
            opts.append(o)
        else:
            print('Input "{}" does not appear to be a valid url.'.format(m))
    return opts
