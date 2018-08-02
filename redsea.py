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

    # Loop through media and download if possible
    cm = 0
    for mt in media_to_download:

        # Is it an acceptable media type? (skip if not)
        if not mt['type'] in MEDIA_TYPES:
            print('Unknown media type - ' + mt['type'])
            continue

        cm += 1
        id = mt['id']
        media_info = None
        tracks = []
        
        print('<<< Getting {0} info... >>>'.format(MEDIA_TYPES[mt['type']]), end='\r')
        
        # Create a new TidalApi and pass it to a new MediaDownloader
        api = get_api(rsf=RSF, preferred=args.account, mt=mt, quality=preset['quality'])
        md = MediaDownloader(api, preset, Tagger(preset))

        # Get media info
        try:

            # Track
            if mt['type'] == 't':
                tracks.append(md.api.get_track(id))

            # Playlist
            elif mt['type'] == 'p':

                # Make sure only tracks are in playlist items
                playlistItems = md.api.get_playlist_items(id)['items']
                for item in playlistItems:
                    if item['type'] == 'track':
                        tracks.append(item['item'])

            # Album
            else:
                # Get album information
                media_info = md.api.get_album(id)

                # Get a list of the tracks from the album
                tracks = md.api.get_album_tracks(id)['items']

        except TidalError as e:
            if 'not found. This might be region-locked.' in str(e) and (AUTOSELECT or BRUTEFORCEREGION):
                print(e)

                # Let the user know we cannot download this release and skip it
                print('None of the available accounts were able to download release {}. Skipping..'.format(id))
                if not BRUTEFORCEREGION:
                    print('TIP: Try using the bruteforce option to test all available accounts')
                continue

        # Helpful unspecified API error is helpful /s
        except Exception as e:
            print('API Error, Skipping\n', end='\r')
            print(e)
            continue

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
            # Actually download the track (finally )
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


def get_api(rsf, preferred, mt, quality):
    '''
    Loops through all available sessions and attempts
    to find a session capable of downloading the release.
    Returns a TidalApi object

    rsf: an instace of TidalSessionFile or RedseaSessionFile
    preferred: name of the session preferred by the user
    mt: dict of media info (id, type, region)
    quality: requested stream quality

    '''

    preferred = rsf.default if preferred == '' else preferred

    # Should we dynamically select a session? If not, use default or preferred session
    if not (AUTOSELECT or BRUTEFORCEREGION):

        # Check user-preferred session to ensure that sessionId is still valid
        assert rsf.load_session(preferred).valid(), 'Session "{}" is not valid. Please re-authenticate.'.format(preferred)

    # Dyanamically select session based on release ID if AUTOSELECT or BRUTEFORCE are enabled
    else:
        for session in rsf.sessions:
            
            # Get country_code of session
            cc = rsf.sessions[session].country_code

            # If AUTOSELECT, skip all non-matching regions
            if AUTOSELECT and not BRUTEFORCEREGION:
                if mt['region'] is None:
                    print('WARNING: Autoselect is enabled but region could not be determined. Using default session..')
                    break
                elif mt['region'] != cc:
                    continue

            # Is this sessionId still valid?
            if not rsf.load_session(session).valid():
                print('WARNING: Session "{}" is not valid. Please re-authenticate.'.format(session))
                continue

            # Initialize TidalApi for test
            tidal = TidalApi(rsf.load_session(session))

            # Can we get album / track info?
            try:
                print('Checking info fetch with session "{}" in region {}'.format(session, cc), end="", flush=True)

                # Track
                if mt['type'] == 't':
                    track = tidal.get_track(mt['id'])

                # Playlist
                elif mt['type'] == 'p':

                    # Get first "track" in playlist
                    tracks = tidal.get_playlist_items(mt['id'])['items']
                    for t in tracks:
                        if t['type'] == 'track':
                            track = t
                            break

                # Album
                else:
                    tracks = tidal.get_album_tracks(mt['id'])['items']
                    track = tidal.get_track(tracks[0]['id'])

                print('  [success]')
            except TidalError as e:
                if 'not found. This might be region-locked.' in str(e):
                    print('  [failed]')
                    continue
                else:
                    raise(e)

            # Can we get an audio stream?
            try:
                print('Checking audio stream with session "{}"'.format(session), end="", flush=True)
                tidal.get_stream_url(track['id'], quality)
                print('  [success]')
                return TidalApi(rsf.load_session(session))
            except Exception as e:
                print('  [failed]')
                continue

    return TidalApi(rsf.load_session(preferred))

# Run from CLI - catch Ctrl-C and handle it gracefully
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n^C pressed - abort')
        exit()
