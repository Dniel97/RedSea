import argparse
import json
import os
import os.path as path
import errno

import requests

import tagger
from tidal_api import TidalApi

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

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

#
# Downloading and tagging class
#
class MediaDownloader(object):

    def __init__(self, api, album_format, track_format):
        self.api = api
        self.album_format = album_format
        self.track_format = track_format

    def _dl_url(self, url, where):
        r = requests.get(url, stream=True)
        total = int(r.headers['content-length'])
        with open(where, 'wb') as f:
            cc = 0
            for chunk in r.iter_content(chunk_size=1024):
                cc += 1024
                print("\tDownload progress: {0:.0f}%".format((cc / total) * 100), end='\r')
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
            print()
        return where

    def _dl_picture(self, album_id, where):
        return self._dl_url(TidalApi.get_album_artwork_url(album_id), where)

    def _sanitise_name(self, name):
        return name.replace('/', '-').replace('\\', '-').replace(':', '-').replace('|', '-').replace('*', '-')

    def _normalise_info(self, track_info):
        return {
            'title': self._sanitise_name(track_info['title']),
            'artist': self._sanitise_name(track_info['artist']['name']),
            'album': self._sanitise_name(track_info['album']['title']),
            'tracknumber': track_info['trackNumber']
        }

    def download_and_tag_media(self, track_id, track_info, quality, album_info=None):
        print('=== Downloading track ID {0} ==='.format(track_id))
        print('\tTrack: {tracknumber}\n\tTitle: {title}\n\tArtist: {artist}\n\tAlbum: {album}'.format(**self._normalise_info(track_info)))
        print('\t----')
        album_location = self.album_format.format(**self._normalise_info(track_info))
        track_file = self.track_format.format(**self._normalise_info(track_info))
        mkdir_p(album_location)
        print('\tGrabbing stream URL...')
        stream_data = self.api.get_stream_url(track_id, quality)
        if not stream_data['soundQuality'] == quality:
        	print('\tWARNING: {} quality requested, but only {} quality available.'.format(quality, stream_data['soundQuality']))
        if not stream_data['encryptionKey'] == '':
            print('\tUh-oh! Stream is encrypted. Perhaps you are using a desktop session ID?')
            return

        if 'status' in stream_data:
            if stream_data['status'] == 401:
                print("\tGot a 401 when downloading, trying workaround...")
                stream_data = self.api.get_stream_url(track_id, quality)
                if stream_data['status'] == 401:
                    print('\tWorkaround didn\'t work! Please adjust your quality settings to HIGH instead of LOSSLESS.' )
                    return

        # Hacky way to get extension of file from URL
        ftype = None
        url = stream_data['url']
        if url.find('.flac?') == -1:
            if url.find('.m4a?') == -1:
                ftype = ''
            else:
                ftype = 'm4a'
        else:
            ftype = 'flac'

        track_path = path.join(album_location, track_file + '.' + ftype)
        temp_file = self._dl_url(stream_data['url'], track_path)

        aa_location = path.join(album_location, 'Cover.jpg')
        if not path.isfile(aa_location):
            print('\tDownloading album art...')
            self._dl_picture(track_info['album']['cover'], aa_location)

        if album_info is None:
            print('\tGrabbing album info...')
            album_info = self.api.get_album(track_info['album']['id'])

        track_info['album_info'] = album_info

        print('\tTagging media file...')
        if ftype == 'flac':
            tagger.tag_flac(temp_file, track_info, aa_location)
        elif ftype == 'm4a':
            tagger.tag_m4a(temp_file, track_info, aa_location)
        else:
            print('\tUnknown file type to tag!')

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
parser.add_argument('id', type=int, help='The media or collection ID to download.')

args = parser.parse_args()

# Load config
config = json.load(args.o)

# Authentication
if args.media == 'auth':
    print('Authentication is not yet implemented yet. You must use a mobile device session ID to request media.')
    exit()

# Check if we need to authenticate
if config['tidal_session'] == '':
    print('Authentication required. Run again with auth 0')
    exit()

# Create a new API object
api = TidalApi(config['tidal_session'], config['country_code'])

# Create a media downloader
md = MediaDownloader(api, path.join(config['download_path'], config['album_format']), config['track_format'])

if args.media == 'track':
    print('<<< Downloading single track >>>\n')
    track = api.get_track(args.id)
    md.download_and_tag_media(args.id, track, config['quality'])
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
        md.download_and_tag_media(track['id'], track, config['quality'], media_info)
        cur += 1
        print('=== {0}/{1} complete ({2:.0f}% done) ===\n'.format(cur, total, (cur / total) * 100))

print('<<< All downloads completed >>>')