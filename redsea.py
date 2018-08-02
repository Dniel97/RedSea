#!/usr/bin/env python

import json

import redsea.cli as cli

from redsea.mediadownloader import MediaDownloader
from redsea.tagger import Tagger
from redsea.tidal_api import TidalApi, TidalRequestError, TidalError
from redsea.sessions import RedseaSessionFile

from config.settings import PRESETS, AUTOSELECT, BRUTEFORCEREGION


LOGO = """
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

MEDIA_TYPES = {'t': 'track', 'p': 'playlist', 'a': 'album', 'f':'album'}

def main():
    # Get args
    args = cli.get_args()

    # Check for auth flag / session settings
    RSF = RedseaSessionFile('./config/sessions.pk')
    if args.urls[0] == 'auth' and len(args.urls) == 1:
        print('\nThe "auth" command provides the following methods:')
        print('\n  list:     list the currently stored sessions')
        print('  add:      login and store a new session')
        print('  remove:   permanently remove a stored session')
        print('  default:  set a session as default')
        print('\nUsage: redsea.py auth add\n')
        exit()
    elif args.urls[0] == 'auth' and len(args.urls) > 1:
        if args.urls[1] == 'list':
            RSF.list_sessions()
            exit()
        elif args.urls[1] == 'add':
            RSF.new_session()
            exit()
        elif args.urls[1] == 'remove':
            RSF.remove_session()
            exit()
        elif args.urls[1] == 'default':
            RSF.set_default()
            exit()

    print(LOGO)

    # Load config
    preset = PRESETS[args.preset]

    # Parse options
    preset['quality'] = []
    preset['quality'].append('HI_RES') if preset['MQA_FLAC_24'] else None
    preset['quality'].append('LOSSLESS') if preset['FLAC_16'] else None
    preset['quality'].append('HIGH') if preset['AAC_320'] else None
    preset['quality'].append('LOW') if preset['AAC_96'] else None
    media_to_download = cli.parse_media_option(args.urls)

    # Check session to ensure that sessionId is still valid
    session = RSF.default if args.account == '' else args.account
    assert RSF.load_session(args.account).valid(), 'Session "{}" is not valid. Please re-authenticate.'.format(session)

    # Create a new TidalApi and pass it to a new MediaDownloader
    md = MediaDownloader(TidalApi(RSF.load_session(args.account)), preset, Tagger(preset))

    cm = 0
    for mt in media_to_download:
        md.api = TidalApi(RSF.load_session(args.account))
        cm += 1
        id = mt['id']
        tracks = []

        # Is it an acceptable media type?
        if not mt['type'] in MEDIA_TYPES:
            print('Unknown media type - ' + mt['type'])
            continue
        
        print('<<< Getting {0} info... >>>'.format(MEDIA_TYPES[mt['type']]), end='\r')
        media_info = None

        # Prepare a single track for download
        if mt['type'] == 't':
            tracks.append(md.api.get_track(id))

        # Prepare a playlist for download
        elif mt['type'] == 'p':

            # Make sure only tracks are in playlist items
            playlistItems = md.api.get_playlist_items(id)['items']
            for item in playlistItems:
                if item['type'] == 'track':
                    tracks.append(item['item'])

        # Prepare an album for download
        else:
            try:
                # Try to get album information
                media_info = md.api.get_album(id)
            except TidalError as e:
                if 'not found. This might be region-locked.' in str(e) and (AUTOSELECT or BRUTEFORCEREGION):
                    print(e)

                    # Try to select a better TidalSession based on the region parsed from the URL
                    if not BRUTEFORCEREGION:
                        if mt['region'] is not None and len(mt['region']) == 2:
                            print('Region appears to be "{}" based on URL. Autoselect is enabled. Checking accounts..'.format(mt['region']))
                            session = get_session(tsf=RSF, id=id, quality=preset['quality'], album=True, country_code=mt['region'])
                        else:
                            print('Autoselect is enabled but region could not be determined. Try bruteforce. Skipping..')
                            continue
                    
                    # Try to get media info with all available TidalSessions
                    else:
                        print('Session brute force is enabled. Trying all accounts..')
                        session = get_session(tsf=RSF, id=id, quality=preset['quality'], album=True)

                    # If we got session match, load a new TidalApi instance into the MediaDownloader
                    if session:
                        md.api = TidalApi(RSF.load_session(session))
                        media_info = md.api.get_album(id)

                    # Let the user know we cannot download this release and skip it
                    else:
                        print('None of the available accounts were able to download release {}. Skipping..'.format(id))
                        continue

            # Helpful unspecified API error is helpful /s
            except:
                print('API Error, Skipping\n', end='\r')
                continue

            # Get a list of the tracks on the album
            tracks = md.api.get_album_tracks(id)['items']

        total = len(tracks)

        # Single
        if total == 1:
            print('<<< Downloading single track... >>>')

        # Playlist or album
        else:
            print('<<< Downloading {0}: {1} track(s) in total >>>'.format(
                MEDIA_TYPES[mt['type']], total))

        cur = 0
        for track in tracks:
            # Actually download the track (finally)
            try:
                md.download_media(track, preset['quality'], media_info)
            except ValueError as e:
                print("\t" + str(e))
                if args.skip is True:
                    print('Skipping track "{} - {}" due to insufficient quality'.format(
                        track['artist']['name'], track['title']))
                else:
                    print('Halting on track "{} - {}" due to insufficient quality'.format(
                        track['artist']['name'], track['title']))
                    quit()

            cur += 1
            print('=== {0}/{1} complete ({2:.0f}% done) ===\n'.format(
                cur, total, (cur / total) * 100))
        

        print('> Download queue: {0}/{1} items complete ({2:.0f}% done) <\n'.
              format(cm, len(media_to_download),
                     (cm / len(media_to_download)) * 100))

    print('> All downloads completed. <')

def get_session(tsf, id, quality, album, country_code=None):
    '''
    Loops through all available sessions and attempts
    to find a session capable of downloading the release

    tsf: an instace of TidalSessionFile or RedseaSessionFile
    id: release ID
    quality: requested stream quality
    album: boolean True if album, boolen False if track
    country_code: the two-character country_code of an acceptable region for the release
                  if blank, function will test all available sessions
    '''

    for session in tsf.sessions:

        cc = tsf.sessions[session].country_code
        if country_code is not None and country_code != cc:
            continue

        if not tsf.load_session(session).valid():
            print('WARNING: Session "{}" is not valid. Please re-authenticate.'.format(session))
            continue

        tidal = TidalApi(tsf.load_session(session))

        try:
            print('Fetching track info with session "{}" in region {}'.format(session, cc), end="", flush=True)
            tracks = tidal.get_album_tracks(id)['items']
            print('  [success]')
        except TidalError as e:
            if 'not found. This might be region-locked.' in str(e):
                print('  [failed]')
                continue
            else:
                raise(e)

        try:
            print('Fetching audio stream with session "{}"'.format(session), end="", flush=True)
            tidal.get_stream_url(tracks[0]['id'], quality)
            print('  [success]')
            return session
        except Exception as e:
            print('  [failed]')
            raise(e)

        return False

# Run from CLI - catch Ctrl-C and handle it gracefully
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n^C pressed - abort')
        exit()
