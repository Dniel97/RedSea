#!/usr/bin/env python

import argparse
import json
import getpass
from os import path
import subprocess
import m3u_writer

from tagger import Tagger
from tidal_api import TidalApi, TidalError
from mediadownloader import MediaDownloader

logo = """
 /$$$$$$$                  /$$  /$$$$$$                     
| $$__  $$                | $$ /$$__  $$                    
| $$  \ $$  /$$$$$$   /$$$$$$$| $$  \__/  /$$$$$$   /$$$$$$ 
| $$$$$$$/ /$$__  $$ /$$__  $$|  $$$$$$  /$$__  $$ |____  $$
| $$__  $$| $$$$$$$$| $$  | $$ \____  $$| $$$$$$$$  /$$$$$$$
| $$  \ $$| $$_____/| $$  | $$ /$$  \ $$| $$_____/ /$$__  $$
| $$  | $$|  $$$$$$$|  $$$$$$$|  $$$$$$/|  $$$$$$$|  $$$$$$$
|__/  |__/ \_______/ \_______/ \______/  \_______/ \_______/\n\n"""

def open_handler(handler, files):
    args = [handler] + files
    subprocess.Popen(args, close_fds=True)

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
    
    parser.add_argument('-s', 
        default=False, 
        action='store_true', 
        help='Don\'t download, just get the stream URL and pass it to a program (specified in config file).')
        
    parser.add_argument('-q',
        metavar='quality',
        help='Override the quality specified in the config file. See readme for valid values.')

    parser.add_argument('media', nargs='+', help='The media to download. See readme for media download format.')

    args = parser.parse_args()
    
    # Load config
    config = {}
    with open(args.o) as f:
        config = json.load(f)
    
    if args.q is not None:
        config['tidal']['quality'] = args.q
    
    # Create a new API object
    api = TidalApi(config['tidal']['session'], config['tidal']['country_code'])

    # Authentication
    if args.media[0] == 'auth':
        print('[[[ Enter your Tidal username and password ]]]\n')
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
    media_to_download = parse_media_option(args.media)

    # Create a media downloader
    md = MediaDownloader(api, config['download'], Tagger(config['tagging']))
    
    print('[[[ {} items requested ]]]'.format(len(media_to_download)))
    for mt in media_to_download:
        id = mt['id']
        tracks = []
        # Single track
        if mt['type'] == 't':
            print('<<< Getting track info... >>>', end='\r')
            track = api.get_track(id)
            
            # Stream action -- before download
            if args.s:
                print('<<< Preparing to stream track... >>>')
                md.print_track_info(track)
                stream = md.get_stream_url(track['id'], config['tidal']['quality'])
                if stream is None:
                    print('\tCan\'t stream!')
                else:
                    print('\tGenerating playlist...')
                    track['stream_url'] = stream['url']
                    pl = m3u_writer.temp_path()
                    m3u_writer.write_tracks([track], pl)
                    print('\tOpening streaming program...')
                    open_handler(config['programs']['stream'], [pl])
                exit()
            
            # Download and tag file
            _, filepath = md.download_media(track, config['tidal']['quality'])
            print('=== 1/1 complete (100% done) ===\n')
        # Collection
        elif mt['type'] == 'p' or mt['type'] == 'a':
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
            # Stream action
            if args.s:
                print('<<< Preparing to stream tracks... >>>')
                streams = []
                for track in tracks:
                    md.print_track_info(track)
                    stream = md.get_stream_url(track['id'], config['tidal']['quality'])
                    if stream is None:
                        print('Can\'t stream!')
                        continue
                    print()
                    track['stream_url'] = stream['url']
                    streams.append(track)
                
                print('\tGenerating playlist...')
                pl = m3u_writer.temp_path()
                m3u_writer.write_tracks(streams, pl)
                print('\tOpening streaming program...')
                open_handler(config['programs']['stream'], [pl])
                exit()

            total = len(tracks)
            print('<<< Downloading {0}: {1} track(s) in total >>>'.format(typename, total))
            cur = 0
            for track in tracks:
                md.download_media(track, config['tidal']['quality'], media_info)
                cur += 1
                print('=== {0}/{1} complete ({2:.0f}% done) ===\n'.format(cur, total, (cur / total) * 100))
        else:
            print('Unknown media type!')

    print('[[[ All downloads completed. ]]]')

# Run from CLI - catch Ctrl-C and handle it gracefully
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n^C pressed - abort')
        exit()
