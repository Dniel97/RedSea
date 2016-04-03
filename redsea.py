import argparse
import json
from os import path

import tagger
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

print(logo)

#
# argparse setup
#
parser = argparse.ArgumentParser(description='A music downloader for Tidal.')

parser.add_argument('-o', 
    default='rs_config.json', 
    type=argparse.FileType('r+'), 
    metavar='filename', 
    help='The path to a config file. If not supplied, uses `rs_config.json\' in the current directory.')

parser.add_argument('media', choices=['album', 'playlist', 'track', 'auth'], help='The media type to download. Pass \'auth\' to authenticate.')
parser.add_argument('id', help='The media or collection ID to download.')

args = parser.parse_args()

# Load config
config = json.load(args.o)

# Authentication
if args.media == 'auth':
    print('Authentication is not yet implemented yet. You must use a mobile device session ID to request media.')
    exit()

# Check if we need to authenticate
if config['tidal']['session'] == '':
    print('Authentication required. Run again with auth 0')
    exit()

# Create a new API object
api = TidalApi(config['tidal']['session'], config['tidal']['country_code'])

# Create a media downloader
md = MediaDownloader(api, path.join(config['download']['path'], config['download']['album_format']), config['download']['track_format'])

# Single track
if args.media == 'track':
    print('<<< Downloading single track >>>\n')
    track = api.get_track(args.id)
    md.download_media(track, config['tidal']['quality'], config['download']['tries'], None, config['tagging'])

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
        md.download_media(track, config['tidal']['quality'], config['download']['tries'], media_info, config['tagging'])
        cur += 1
        print('=== {0}/{1} complete ({2:.0f}% done) ===\n'.format(cur, total, (cur / total) * 100))

print('<<< All downloads completed >>>')