#!/usr/bin/env python

import traceback
import sys
import os
import re
import urllib3

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

MEDIA_TYPES = {'t': 'track', 'p': 'playlist', 'a': 'album', 'r': 'artist', 'v': 'video'}

def main():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    os.chdir(sys.path[0])
    # Get args
    args = cli.get_args()

    # Load config
    BRUTEFORCE = args.bruteforce or BRUTEFORCEREGION
    preset = PRESETS[args.preset]

    # Parse options
    preset['quality'] = []
    preset['quality'].append('HI_RES') if preset['MQA_FLAC_24'] else None
    preset['quality'].append('LOSSLESS') if preset['FLAC_16'] else None
    preset['quality'].append('HIGH') if preset['AAC_320'] else None
    preset['quality'].append('LOW') if preset['AAC_96'] else None

    # Check for auth flag / session settings
    RSF = RedseaSessionFile('./config/sessions.pk')
    if args.urls[0] == 'auth' and len(args.urls) == 1:
        print('\nThe "auth" command provides the following methods:')
        print('\n  list:     Lists stored sessions if any exist')
        print('  add:      Prompts for a TV or Mobile session. The TV option displays a 6 digit key which should be '
              'entered inside link.tidal.com where the user can login. The Mobile option prompts for a Tidal username '
              'and password. Both options authorize a session which then gets stored in the sessions file')
        print('  remove:   Removes a stored session from the sessions file by name')
        print('  default:  Set a default account for redsea to use when the -a flag has not been passed')
        print('  reauth:   Reauthenticates with server to get new sessionId')
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

    elif args.urls[0] == 'id':
        type = None
        md = MediaDownloader(TidalApi(RSF.load_session(args.account)), preset, Tagger(preset))

        if len(args.urls) == 2:
            id = args.urls[1]
            if not id.isdigit():
                # Check if id is playlist (UUIDv4)
                pattern = re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
                if pattern.match(id):
                    try:
                        result = md.playlist_from_id(id)
                        type = 'p'
                    except TidalError:
                        print("The playlist id " + str(id) + " could not be found!")
                        exit()

                else:
                    print('The id ' + str(id) + ' is not valid.')
                    exit()
        else:
            print('Example usage: python redsea.py id 92265335')
            exit()

        if type is None:
            type = md.type_from_id(id)

        if type:
            media_to_download = [{'id': id, 'type': type}]

        else:
            print("The id " + str(id) + " could not be found!")
            exit()

    elif args.urls[0] == 'explore':
        try:
            if args.urls[1] == 'atmos':
                page = 'dolby_atmos'
                if args.urls[2] == 'tracks':
                    title = 'Tracks'
                elif args.urls[2] == 'albums':
                    title = 'New Albums'
            elif args.urls[1] == '360':
                page = '360'
                if args.urls[2] == 'tracks':
                    title = 'New Tracks'
                elif args.urls[2] == 'albums':
                    title = 'Now Available'
        except IndexError:
            print("Example usage of explore: python redsea.py explore (atmos|360) (albums|tracks)")
            exit()

        print(f'Selected: {page.replace("_", " ").title()} - {title}')

        md = MediaDownloader(TidalApi(RSF.load_session(args.account)), preset, Tagger(preset))
        page_content = md.page(page)

        # Iterate though all the page and find the module with the title: "Now Available" or "Tracks"
        show_more_link = [module['modules'][0]['showMore']['apiPath'] for module in page_content['rows'] if
                          module['modules'][0]['title'] == title]

        singe_page_content = md.page(show_more_link[0][6:])
        # Get the number of all items for offset and the dataApiPath
        page_list = singe_page_content['rows'][0]['modules'][0]['pagedList']

        total_items = page_list['totalNumberOfItems']
        more_items_link = page_list['dataApiPath'][6:]

        # Now fetch all the found total_items
        items = []
        for offset in range(0, total_items//50 + 1):
            print(f'Fetching {offset * 50}/{total_items}', end='\r')
            items += md.page(more_items_link, offset * 50)['items']

        print()
        total_items = len(items)

        # Beauty print all found items
        for i in range(total_items):
            item = items[i]

            if item['audioModes'] == ['DOLBY_ATMOS']:
                specialtag = " [Dolby Atmos]"
            elif item['audioModes'] == ['SONY_360RA']:
                specialtag = " [360 Reality Audio]"
            else:
                specialtag = ""

            if item['explicit']:
                explicittag = " [E]"
            else:
                explicittag = ""

            date = " (" + item['streamStartDate'].split('T')[0] + ")"

            print(str(i + 1) + ") " + str(item['title']) + " - " + str(
                item['artists'][0]['name']) + explicittag + specialtag + date)

        print(str(total_items + 1) + ") Download all items listed above")
        print(str(total_items + 2) + ") Exit")

        while True:
            chosen = int(input("Selection: ")) - 1
            if chosen == total_items + 1:
                exit()
            elif chosen > total_items + 1 or chosen < 0:
                print("Enter an existing number")
            else:
                break
            print()

        # if 'album' in item['url'] is a really ugly way but well should be fine for now
        if chosen == total_items:
            print('Downloading all albums')
            media_to_download = [{'id': str(item['id']), 'type': 'a' if 'album' in item['url'] else 't'} for item in items]
        else:
            media_to_download = [{'id': str(items[chosen]['id']), 'type': 'a' if 'album' in items[chosen]['url'] else 't'}]

    elif args.urls[0] == 'search':
        md = MediaDownloader(TidalApi(RSF.load_session(args.account)), preset, Tagger(preset))
        while True:
            searchresult = md.search_for_id(args.urls[2:])
            if args.urls[1] == 'track':
                searchtype = 'tracks'
            elif args.urls[1] == 'album':
                searchtype = 'albums'
            elif args.urls[1] == 'video':
                searchtype = 'videos'
            else:
                print("Example usage of search: python redsea.py search [track/album/video] Darkside Alan Walker")
                exit()
            # elif args.urls[1] == 'playlist':
            #    searchtype = 'playlists'

            numberofsongs = int(searchresult[searchtype]['totalNumberOfItems'])
            if numberofsongs > 20:
                numberofsongs = 20
            for i in range(numberofsongs):
                song = searchresult[searchtype]['items'][i]

                if searchtype != 'videos':
                    if song['audioModes'] == ['DOLBY_ATMOS']:
                        specialtag = " [Dolby Atmos]"
                    elif song['audioModes'] == ['SONY_360RA']:
                        specialtag = " [360 Reality Audio]"
                    elif song['audioQuality'] == 'HI_RES':
                        specialtag = " [MQA]"
                    else:
                        specialtag = ""
                else:
                    specialtag = " [" + song['quality'].replace('MP4_', '') + "]"

                if song['explicit']:
                    explicittag = " [E]"
                else:
                    explicittag = ""

                print(str(i + 1) + ") " + str(song['title']) + " - " + str(
                    song['artists'][0]['name']) + explicittag + specialtag)

            query = None

            if numberofsongs > 0:
                print(str(numberofsongs + 1) + ") Not found? Try a new search")
                while True:
                    chosen = int(input("Song Selection: ")) - 1
                    if chosen == numberofsongs:
                        query = input("Enter new search query: [track/album/video] Darkside Alan Walker: ")
                        break
                    elif chosen > numberofsongs:
                        print("Enter an existing number")
                    else:
                        break
                print()
                if query:
                    args.urls = ("search " + query).split()
                    continue
            else:
                print("No results found for '" + ' '.join(args.urls[2:]))
                print("1) Not found? Try a new search")
                print("2) Quit")
                while True:
                    chosen = int(input("Selection: "))
                    if chosen == 1:
                        query = input("Enter new search query: [track/album/video] Darkside Alan Walker: ")
                        break
                    else:
                        exit()
                print()
                if query:
                    args.urls = ("search " + query).split()
                    continue

            if searchtype == 'tracks':
                media_to_download = [{'id': str(searchresult[searchtype]['items'][chosen]['id']), 'type': 't'}]
            elif searchtype == 'albums':
                media_to_download = [{'id': str(searchresult[searchtype]['items'][chosen]['id']), 'type': 'a'}]
            elif searchtype == 'videos':
                media_to_download = [{'id': str(searchresult[searchtype]['items'][chosen]['id']), 'type': 'v'}]
            # elif searchtype == 'playlists':
            #    media_to_download = [{'id': str(searchresult[searchtype]['items'][chosen]['id']), 'type': 'p'}]
            break

    else:
        media_to_download = cli.parse_media_option(args.urls, args.file)

    print(LOGO)

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
        md = MediaDownloader(TidalApi(RSF.load_session(args.account)), preset.copy(), Tagger(preset))

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
                        # Stupid mess to get the preset path rather than the modified path when > 2 playlist links added
                        # md = MediaDownloader(TidalApi(RSF.load_session(args.account)), preset, Tagger(preset))

                        # Get playlist title to create path
                        playlist = md.api.get_playlist(media['id'])

                        # Ugly way to get the playlist creator
                        creator = None
                        if playlist['creator']['id'] == 0:
                            creator = 'Tidal'
                        elif 'name' in playlist['creator']:
                            creator = md._sanitise_name(playlist["creator"]["name"])

                        if creator:
                            md.opts['path'] = os.path.join(md.opts['path'], f'{creator} - {md._sanitise_name(playlist["title"])}')
                        else:
                            md.opts['path'] = os.path.join(md.opts['path'], md._sanitise_name(playlist["title"]))

                        # Make sure only tracks are in playlist items
                        playlist_items = md.api.get_playlist_items(media['id'])['items']
                        for item_ in playlist_items:
                            tracks.append(item_['item'])

                    # Album
                    elif media['type'] == 'a':
                        # Get album information
                        media_info = md.api.get_album(media['id'])

                        # Get a list of the tracks from the album
                        tracks = md.api.get_album_tracks(media['id'])['items']

                    # Video
                    elif media['type'] == 'v':
                        # Get video information
                        tracks.append(md.api.get_video(media['id']))

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
            if mt['type'] == 'p':
                name = md.playlist_from_id(mt['id'])['title']
            else:
                name = track_info[0][1]['title']
                
            print('<<< Downloading {0} "{1}": {2} track(s) in total >>>'.format(
                MEDIA_TYPES[mt['type']] + (' ' + media_name if media_name else ''), name, total))

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
                        md.download_media(track, media_info, overwrite=args.overwrite,
                                          track_num=cur+1 if mt['type'] == 'p' else None)
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
                            break

                    # Catch file name errors
                    except OSError as e:
                        print(e)
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

                        elif 'Please use a mobile session' in str(e):
                            print(e)
                            print('Choose one of the following mobile sessions: ')
                            RSF.list_sessions(True)
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
            format(cm, len(media_to_download), (cm / len(media_to_download)) * 100))

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
