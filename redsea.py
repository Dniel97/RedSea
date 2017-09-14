#!/usr/bin/env python

import json
import getpass
from os import path

from tagger import Tagger
from tidal_api import TidalApi, TidalError
from mediadownloader import MediaDownloader
import cli

logo = """
 /$$$$$$$                  /$$  /$$$$$$                     
| $$__  $$                | $$ /$$__  $$                    
| $$  \ $$  /$$$$$$   /$$$$$$$| $$  \__/  /$$$$$$   /$$$$$$ 
| $$$$$$$/ /$$__  $$ /$$__  $$|  $$$$$$  /$$__  $$ |____  $$
| $$__  $$| $$$$$$$$| $$  | $$ \____  $$| $$$$$$$$  /$$$$$$$
| $$  \ $$| $$_____/| $$  | $$ /$$  \ $$| $$_____/ /$$__  $$
| $$  | $$|  $$$$$$$|  $$$$$$$|  $$$$$$/|  $$$$$$$|  $$$$$$$
|__/  |__/ \_______/ \_______/ \______/  \_______/ \_______/

                    (c) 2016 Joe Thatcher
               https://github.com/svbnet/RedSea
\n"""
    
def main():
    print(logo)
    
    # Get args
    args = cli.get_args()
    
    # Load config
    config = { }
    with open(args.o) as f:
        config = json.load(f)
    
    if args.lossless:
        config['download']['lossless_only'] = True

    # Override loaded config with CLI options if possible
    if args.p is not None:
        cli.rec_update(config, cli.parse_config_overrides(args.p))
    
    # Create a new API object
    api = TidalApi(config['tidal']['session'], config['tidal']['country_code'])

    # Authentication
    if args.urls[0] == 'auth':
        print('AUTHENTICATION: Enter your Tidal username and password:\n')
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
        print('Authentication required. Run again with `auth`.')
        exit()

    # Parse options
    media_to_download = cli.parse_media_option(args.urls)

    # Create a media downloader
    md = MediaDownloader(api, config['download'], Tagger(config['tagging']))
    
    cm = 0
    for mt in media_to_download:
        cm += 1
        id = mt['id']
        tracks = []
        # Single track
        if mt['type'] == 't':
            print('<<< Getting track info... >>>', end='\r')
            track = api.get_track(id)
            
            # Download and tag file
            print('<<< Downloading single track... >>>')
            _, filepath = md.download_media(track, config['tidal']['quality'])
            print('=== 1/1 complete (100% done) ===\n')
        # Collection
        elif mt['type'] == 'p' or mt['type'] == 'a' or mt['type'] == 'f':
            typename = 'playlist' if mt['type'] == 'p' else 'album'
            print('<<< Getting {0} info... >>>'.format(typename), end='\r')
            media_info = None
            if mt['type'] == 'p':
                # Make sure only tracks are in playlist items
                playlistItems = api.get_playlist_items(id)['items']
                for item in playlistItems:
                    if item['type'] == 'track':
                        tracks.append(item['item'])
            else:
                media_info = api.get_album(id)
                tracks = api.get_album_tracks(id)['items']

            total = len(tracks)
            print('<<< Downloading {0}: {1} track(s) in total >>>'.format(typename, total))
            cur = 0
            for track in tracks:
                md.download_media(track, config['tidal']['quality'], media_info)
                cur += 1
                print('=== {0}/{1} complete ({2:.0f}% done) ===\n'.format(cur, total, (cur / total) * 100))
        else:
            print('Unknown media type - ' + mt['type'])
        print('> Download queue: {0}/{1} items complete ({2:.0f}% done) <\n'.format(cm, len(media_to_download), (cm / len(media_to_download)) * 100))

    print('> All downloads completed. <')

# Run from CLI - catch Ctrl-C and handle it gracefully
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n^C pressed - abort')
        exit()
