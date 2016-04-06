#!/usr/bin/env python

import argparse
import json
import getpass
from os import path

from tagger import Tagger
from tidal_api import TidalApi, TidalError
from mediadownloader import MediaDownloader

logo = "" +\
"                           `.:;::`            \n" +\
"                       `;;;;;;;;;;;;;,        \n" +\
"                     ,;;:           .;;;      \n" +\
"                   ,;;;                ;;.    \n" +\
"                  ;;++:                 `;:   \n" +\
"                ,;;++++++                 ;`  \n" +\
"               :;++++++.                  ,;  \n" +\
"              :;+++++++                    ;  \n" +\
"             :;++++++++++              ,;` ;  \n" +\
"            .;++++++++++`               ;;;,  \n" +\
"            ;++++++++++             ;,  ;     \n" +\
"           ;;++;++++++++'           ;;:;;     \n" +\
"          ;;++;;+++++++++:      ,   ;.;:      \n" +\
"          ;++;;++';+++++;       ;;  ;`        \n" +\
"         ;;++;+++;++++++        ;;;,;         \n" +\
"         ;;+;;++;;++;'++';;;;.  ;:;;          \n" +\
"       :;;;;'+;;++;;+++;;  .;  ;              \n" +\
"        ;;;;;;;;;+';;++;;`   :;;;             \n" +\
"       `;;;;;;;;;;;;;+;;;                     \n" +\
"       ;;;;;;;;;;;;;;;;;;                     \n" +\
"       ;;;;;;;;;;;;;;;;;;;                    \n" +\
"      .;;;;;;;;;;;;;;;;;;;:                   \n" +\
"      ;;;;;;;;;;;;;;;;;;;;;;`     .           \n" +\
"     .;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;,         \n" +\
"  ; .;;;;;;;;;;;;;;,;;;;;;;;;;;;;;;;;;;:..;`  \n" +\
"  ;;;;;;;;;;;;;;;;    ;;;;;;;;;;;;;;;;;;;;`   \n" +\
"   .;;;;;;;;;;;;.       ;;;;;;;;;;;;;;;;;     \n" +\
"\n" +\
" /$$$$$$$                  /$$  /$$$$$$                      \n" +\
"| $$__  $$                | $$ /$$__  $$                     \n" +\
"| $$  \ $$  /$$$$$$   /$$$$$$$| $$  \__/  /$$$$$$   /$$$$$$  \n" +\
"| $$$$$$$/ /$$__  $$ /$$__  $$|  $$$$$$  /$$__  $$ |____  $$ \n" +\
"| $$__  $$| $$$$$$$$| $$  | $$ \____  $$| $$$$$$$$  /$$$$$$$ \n" +\
"| $$  \ $$| $$_____/| $$  | $$ /$$  \ $$| $$_____/ /$$__  $$ \n" +\
"| $$  | $$|  $$$$$$$|  $$$$$$$|  $$$$$$/|  $$$$$$$|  $$$$$$$ \n" +\
"|__/  |__/ \_______/ \_______/ \______/  \_______/ \_______/ \n"\
.replace(';', '\x1B[91m;\x1B[0m')\
.replace('$', '\x1B[[97m$\x1B[0m')

def main():
    print(logo)

    #
    # argparse setup
    #
    parser = argparse.ArgumentParser(description='A music downloader for Tidal.')

    parser.add_argument('-o', 
        default='rs_config.json',
        metavar='filename', 
        help='The path to a config file. If not supplied, uses `rs_config.json\' in the current directory.')

    parser.add_argument('media', choices=['album', 'playlist', 'track', 'auth'], help='the media type to download. Pass \'auth\' to authenticate.')
    parser.add_argument('id', help='The media or collection ID to download. If authenticating, pass -')

    args = parser.parse_args()

    # Load config
    config = {}
    with open(args.o) as f:
        config = json.load(f)

    # Create a new API object
    api = TidalApi(config['tidal']['session'], config['tidal']['country_code'])

    # Authentication
    if args.media == 'auth':
        uname = input('Username: ')
        pswd = getpass.getpass('Password: ')
        print('Attempting authentication...')
        auth = TidalApi.login(uname, pswd, config['tidal']['auth_token'])
        config['tidal']['session'] = auth['sessionId']
        config['tidal']['country_code'] = auth['countryCode']
        with open(args.o, 'w') as f:
            json.dump(config, f, indent='\t')
        print('Success!')
        exit()

    # Check if we need to authenticate
    if config['tidal']['session'] == '':
        print('Authentication required. Run again with auth 0')
        exit()

    # Create a media downloader
    md = MediaDownloader(api, config['download'], Tagger(config['tagging']))

    # Single track
    if args.media == 'track':
        print('<<< Downloading single track >>>\n')
        track = api.get_track(args.id)
        md.download_media(track, config['tidal']['quality'])

    # Multiple track
    elif args.media == 'playlist' or args.media == 'album':
        tracks = []
        print('<<< Downloading {0}: getting info... >>> '.format(args.media), end='\r')
        media_info = None
        if args.media == 'playlist':
            tracks = api.get_playlist_items(args.id)['items']
        else:
            media_info = api.get_album(args.id)
            tracks = api.get_album_tracks(args.id)['items']

        total = len(tracks)
        print('<<< Downloading {0}: {1} track(s) in total >>>\n'.format(args.media, total))
        cur = 0
        for track in tracks:
            md.download_media(track, config['tidal']['quality'], media_info)
            cur += 1
            print('=== {0}/{1} complete ({2:.0f}% done) ===\n'.format(cur, total, (cur / total) * 100))

    print('<<< All downloads completed >>>')

# Run from CLI - catch Ctrl-C and handle it gracefully
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n^C pressed - abort')
        exit()
