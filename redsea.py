#!/usr/bin/env python

import traceback
import sys
import os

import redsea.cli as cli

from redsea.mediadownloader import MediaDownloader
from redsea.tagger import Tagger
from redsea.tidal_api import TidalApi, TidalError
from redsea.sessions import RedseaSessionFile

from config.settings import PRESETS, BRUTEFORCEREGION


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

MEDIA_TYPES = {'t': 'track', 'p': 'playlist', 'a': 'album', 'r': 'artist'}

def main():
    os.chdir(sys.path[0])
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
        print('  reauth:   reauthenticate with Tidal to get new sessionId')
        print('\nUsage: redsea.py auth add\n')
        exit()
    elif args.urls[0] == 'auth' and len(args.urls) > 1:
        if args.urls[1] == 'list':
            RSF.list_sessions()
            exit()
        elif args.urls[1] == 'add':
            if len(args.urls) == 5:
                RSF.create_session(args.urls[2], args.urls[3], args.urls[4])
            else:
                RSF.new_session()
            exit()
        elif args.urls[1] == 'remove':
            RSF.remove_session()
            exit()
        elif args.urls[1] == 'default':
            RSF.set_default()
            exit()
        elif args.urls[1] == 'reauth':
            RSF.reauth()
            exit()

    print(LOGO)

    # Load config
    BRUTEFORCE = args.bruteforce or BRUTEFORCEREGION
    preset = PRESETS[args.preset]

    # Parse options
    preset['quality'] = []
    preset['quality'].append('HI_RES') if preset['MQA_FLAC_24'] else None
    preset['quality'].append('LOSSLESS') if preset['FLAC_16'] else None
    preset['quality'].append('HIGH') if preset['AAC_320'] else None
    preset['quality'].append('LOW') if preset['AAC_96'] else None
    media_to_download = cli.parse_media_option(args.urls, args.file)

    # Loop through media and download if possible
    cm = 0
    for mt in media_to_download:

        # Is it an acceptable media type? (skip if not)
        if not mt['type'] in MEDIA_TYPES:
            print('Unknown media type - ' + mt['type'])
            continue

        cm += 1
        print('<<< Getting {0} info... >>>'.format(MEDIA_TYPES[mt['type']]))

        # Create a new TidalApi and pass it to a new MediaDownloader
        md = MediaDownloader(TidalApi(RSF.load_session(args.account)), preset, Tagger(preset))

        # Create a new session generator in case we need to switch sessions
        session_gen = RSF.get_session()

        # Get media info
        def get_tracks(media):
            media_name = None
            tracks = []
            media_info = None
            track_info = []

            while True:
                try:
                    if media['type'] == 'f':
                        lines = media['content'].split('\n')
                        for i, l in enumerate(lines):
                            print('Getting info for track {}/{}'.format(i, len(lines)), end='\r')
                            tracks.append(md.api.get_track(l))
                        print()


                    # Track
                    elif media['type'] == 't':
                        tracks.append(md.api.get_track(media['id']))

                    # Playlist
                    elif media['type'] == 'p':

                        # Make sure only tracks are in playlist items
                        playlistItems = md.api.get_playlist_items(media['id'])['items']
                        for item in playlistItems:
                            if item['type'] == 'track':
                                tracks.append(item['item'])

                    # Album
                    elif media['type'] == 'a':
                        # Get album information
                        media_info = md.api.get_album(media['id'])

                        # Get a list of the tracks from the album
                        tracks = md.api.get_album_tracks(media['id'])['items']

                    # Artist
                    else:
                        # Get the name of the artist for display to user
                        media_name = md.api.get_artist(media['id'])['name']

                        # Collect all of the tracks from all of the artist's albums
                        albums = md.api.get_artist_albums(media['id'])['items'] + md.api.get_artist_albums_ep_singles(media['id'])['items']
                        eps_info = []
                        singles_info = []
                        for album in albums:
                            if 'aggressive_remix_filtering' in preset and preset['aggressive_remix_filtering']:
                                title = album['title'].lower()
                                if 'remix' in title or 'commentary' in title or 'karaoke' in title:
                                    print('\tSkipping ' + album['title'])
                                    continue

                            # remove sony 360 reality audio albums if there's another (duplicate) album that isn't 360 reality audio
                            if 'skip_360ra' in preset and preset['skip_360ra']:
                                if 'SONY_360RA' in album['audioModes']:
                                    is_duplicate = False
                                    for a2 in albums:
                                        if album['title'] == a2['title'] and album['numberOfTracks'] == a2['numberOfTracks']:
                                            is_duplicate = True
                                            break
                                    if is_duplicate:
                                        print('\tSkipping duplicate Sony 360 Reality Audio album - ' + album['title'])
                                        continue

                            # Get album information
                            media_info = md.api.get_album(album['id'])

                            # Get a list of the tracks from the album
                            tracks = md.api.get_album_tracks(album['id'])['items']

                            if 'type' in media_info and str(media_info['type']).lower() == 'single':
                                singles_info.append((tracks, media_info))
                            else:
                                eps_info.append((tracks, media_info))

                        if 'skip_singles_when_possible' in preset and preset['skip_singles_when_possible']:
                            # Filter singles that also appear in albums (EPs)
                            def track_in_ep(title):
                                for tracks, _ in eps_info:
                                    for t in tracks:
                                        if t['title'] == title:
                                            return True
                                return False
                            for track_info in singles_info[:]:
                                for t in track_info[0][:]:
                                    if track_in_ep(t['title']):
                                        print('\tSkipping ' + t['title'])
                                        track_info[0].remove(t)
                                        if len(track_info[0]) == 0:
                                            singles_info.remove(track_info)

                        track_info = eps_info + singles_info

                    if not track_info:
                        track_info = [(tracks, media_info)]
                    return media_name, track_info

                # Catch region error
                except TidalError as e:
                    if 'not found. This might be region-locked.' in str(e) and BRUTEFORCE:
                        # Try again with a different session
                        try:
                            session, name = next(session_gen)
                            md.api = TidalApi(session)
                            print('Checking info fetch with session "{}" in region {}'.format(name, session.country_code))
                            continue

                        # Ran out of sessions
                        except StopIteration as s:
                            print(e)
                            raise s

                    # Skip or halt
                    else:
                        raise(e)

        try:
            media_name, track_info = get_tracks(media=mt)
        except StopIteration:
            # Let the user know we cannot download this release and skip it
            print('None of the available accounts were able to get info for release {}. Skipping..'.format(mt['id']))
            continue

        total = sum([len(t[0]) for t in track_info])

        # Single
        if total == 1:
            print('<<< Downloading single track... >>>')

        # Playlist or album
        else:
            print('<<< Downloading {0}: {1} track(s) in total >>>'.format(
                MEDIA_TYPES[mt['type']] + (' ' + media_name if media_name else ''), total))


        if args.resumeon and len(media_to_download) == 1 and mt['type'] == 'p':
            print('<<< Resuming on track {} >>>'.format(args.resumeon))
            args.resumeon -= 1
        else:
            args.resumeon = 0


        cur = args.resumeon
        for tracks, media_info in track_info:
            for track in tracks[args.resumeon:]:
                first = True

                # Actually download the track (finally)
                while True:
                    try:
                        md.download_media(track, preset['quality'], media_info, overwrite=args.overwrite)
                        break

                    # Catch quality error
                    except ValueError as e:
                        print("\t" + str(e))
                        traceback.print_exc()
                        if args.skip is True:
                            print('Skipping track "{} - {}" due to insufficient quality'.format(
                                track['artist']['name'], track['title']))
                            break
                        else:
                            print('Halting on track "{} - {}" due to insufficient quality'.format(
                                track['artist']['name'], track['title']))
                            quit()

                    # Catch file name errors
                    except OSError as e:
                        print("\tFile name too long or contains apostrophes")
                        file = open('failed_tracks.txt', 'a')
                        file.write(str(track['url']) + "\n")
                        file.close()
                        break

                    # Catch session audio stream privilege error
                    except AssertionError as e:
                        if 'Unable to download track' in str(e) and BRUTEFORCE:

                            # Try again with a different session
                            try:
                                # Reset generator if this is the first attempt
                                if first:
                                    session_gen = RSF.get_session()
                                    first = False
                                session, name = next(session_gen)
                                md.api = TidalApi(session)
                                print('Attempting audio stream with session "{}" in region {}'.format(name, session.country_code))
                                continue

                            # Ran out of sessions, skip track
                            except StopIteration:
                                # Let the user know we cannot download this release and skip it
                                print('None of the available accounts were able to download track {}. Skipping..'.format(track['id']))
                                break

                        # Skip
                        else:
                            print(str(e) + '. Skipping..')

                # Progress of current track
                cur += 1
                print('=== {0}/{1} complete ({2:.0f}% done) ===\n'.format(
                    cur, total, (cur / total) * 100))

        # Progress of queue
        print('> Download queue: {0}/{1} items complete ({2:.0f}% done) <\n'.
            format(cm, len(media_to_download),
                    (cm / len(media_to_download)) * 100))

    print('> All downloads completed. <')

    # since oauth sessions can change while downloads are happening if the token gets refreshed
    RSF._save()


# Run from CLI - catch Ctrl-C and handle it gracefully
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n^C pressed - abort')
        exit()
