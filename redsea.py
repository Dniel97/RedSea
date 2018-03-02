#!/usr/bin/env python

import json

import redsea.cli as cli

from redsea.mediadownloader import MediaDownloader
from redsea.tagger import Tagger
from redsea.tidal_api import TidalApi, TidalError

from config.settings import PRESETS, ACCOUNTS


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
    preset = PRESETS[args.preset]
    ACCOUNT = ACCOUNTS[args.account]

    # Create a new API object
    api = TidalApi(ACCOUNT['session'], ACCOUNT['country_code'])

    # Parse options
    preset['quality'] = []
    preset['quality'].append('HI_RES') if preset['MQA_FLAC_24'] else None
    preset['quality'].append('LOSSLESS') if preset['FLAC_16'] else None
    preset['quality'].append('HIGH') if preset['AAC_320'] else None
    preset['quality'].append('LOW') if preset['AAC_96'] else None
    media_to_download = cli.parse_media_option(args.urls)

    # Create a media downloader
    md = MediaDownloader(api, preset, Tagger(preset))

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
            try:
                _, filepath = md.download_media(track, preset['quality'])
            except ValueError as e:
                print("\t" + str(e))
                if args.skip is True:
                    print('Skipping track "{} - {}" due to insufficient quality'.format(
                        track['artist']['name'], track['title']))
                else:
                    print('Halting on track "{} - {}" due to insufficient quality'.format(
                        track['artist']['name'], track['title']))
                    quit()

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
                try:
                    media_info = api.get_album(id)
                except:
                    print('api error, skipping\n', end='\r')
                    continue
                tracks = api.get_album_tracks(id)['items']

            total = len(tracks)
            print('<<< Downloading {0}: {1} track(s) in total >>>'.format(
                typename, total))
            cur = 0

            for track in tracks:
                md.download_media(track, preset['quality'],
                                  media_info)
                cur += 1
                print('=== {0}/{1} complete ({2:.0f}% done) ===\n'.format(
                    cur, total, (cur / total) * 100))
        else:
            print('Unknown media type - ' + mt['type'])
        print('> Download queue: {0}/{1} items complete ({2:.0f}% done) <\n'.
              format(cm, len(media_to_download),
                     (cm / len(media_to_download)) * 100))

    print('> All downloads completed. <')


# Run from CLI - catch Ctrl-C and handle it gracefully
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n^C pressed - abort')
        exit()
