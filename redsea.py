#!/usr/bin/env python

import json

import redsea.cli as cli

from redsea.mediadownloader import MediaDownloader
from redsea.tagger import Tagger
from redsea.tidal_api import TidalApi, TidalRequestError, TidalError
from redsea.sessions import RedseaSessionFile

from config.settings import PRESETS, AUTOSELECT, BRUTEFORCEREGION


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

    # Load config
    print(logo)
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

        # Single track
        if mt['type'] == 't':
            print('<<< Getting track info... >>>', end='\r')
            track = md.api.get_track(id)

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
                playlistItems = md.api.get_playlist_items(id)['items']
                for item in playlistItems:
                    if item['type'] == 'track':
                        tracks.append(item['item'])
            else:
                try:
                    media_info = md.api.get_album(id)
                except TidalError as e:
                    if 'not found. This might be region-locked.' in str(e) and (AUTOSELECT or BRUTEFORCEREGION):
                        print(e)

                        if not BRUTEFORCEREGION:
                            print('Region appears to be "{}" based on URL. Autoselect is enabled. Checking accounts..'.format(mt['region']))
                            session = get_session(tsf=RSF, id=id, quality=preset['quality'], album=True, country_code=mt['region'])
                        else:
                            print('Session brute force is enabled. Trying all accounts..')
                            session = get_session(tsf=RSF, id=id, quality=preset['quality'], album=True)

                        if session:
                            md.api = TidalApi(RSF.load_session(session))
                            media_info = md.api.get_album(id)
                        else:
                            print('None of the available accounts were able to download release {}. Skipping..'.format(id))
                            continue
                except:
                    print('API Error, Skipping\n', end='\r')
                    continue
                tracks = md.api.get_album_tracks(id)['items']

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
