import errno
import json
import os
import os.path as path
import re
import base64
import ffmpeg
import shutil

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from .decryption import decrypt_file, decrypt_security_token
from .tagger import FeaturingFormat
from .tidal_api import TidalApi, TidalRequestError, technical_names
from deezer.deezer import Deezer, APIError
from .videodownloader import download_stream, download_file


def _mkdir_p(path):
    try:
        if not os.path.isdir(path):
            os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class MediaDownloader(object):

    def __init__(self, api, options, tagger=None):
        self.api = api
        self.opts = options
        self.tm = tagger

        # Deezer API
        if 'genre_language' in self.opts:
            self.dz = Deezer(language=self.opts['genre_language'])
        else:
            self.dz = Deezer()

        self.session = requests.Session()
        retries = Retry(total=10,
                        backoff_factor=0.4,
                        status_forcelist=[429, 500, 502, 503, 504])

        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def _dl_url(self, url, where):
        r = self.session.get(url, stream=True, verify=False)
        try:
            total = int(r.headers['content-length'])
        except KeyError:
            return False
        with open(where, 'wb') as f:
            cc = 0
            for chunk in r.iter_content(chunk_size=1024):
                cc += 1024
                print(
                    "\tDownload progress: {0:.0f}%".format((cc / total) * 100),
                    end='\r')
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
            print()
        return where

    def _dl_picture(self, album_id, where):
        if album_id is not None:
            rc = self._dl_url(TidalApi.get_album_artwork_url(album_id), where)
            if not rc:
                return False
            else:
                return rc
        else:
            return False

    def _sanitise_name(self, name):
        name = re.sub(r'[\\\/*?"<>|]', '', str(name))

        # Check file length
        if len(name) > 230:
            name = name[:230]

        # Check last character is space
        if len(name) > 0:
            if name[len(name)-1] == ' ':
                name = name[:len(name)-1]

        return re.sub(r'[:]', ' - ', name)

    def _normalise_info(self, track_info, album_info, use_album_artists=False):
        info = {
            k: self._sanitise_name(v)
            for k, v in self.tm.tags(track_info, None, album_info).items()
        }
        if len(album_info['artists']) > 1 and use_album_artists:
            self.featform = FeaturingFormat()

            artists = []
            for a in album_info['artists']:
                if a['type'] == 'MAIN':
                    artists.append(a['name'])

            info['artist'] = self._sanitise_name(self.featform.get_artist_format(artists))
        return info

    def get_stream_url(self, track_id, quality):
        stream_data = None
        print('\tGrabbing stream URL...')
        try:
            stream_data = self.api.get_stream_url(track_id, quality)
        except TidalRequestError as te:
            if te.payload['status'] == 404:
                print('\tTrack does not exist.')
            # in this case, we need to use this workaround discovered by reverse engineering the mobile app, idk why
            elif te.payload['subStatus'] == 4005:
                try:
                    print('\tStatus 4005 when getting stream URL, trying workaround...')
                    playback_info = self.api.get_stream_url(track_id, quality)
                    manifest = json.loads(base64.b64decode(playback_info['manifest']))
                    stream_data = {
                        'soundQuality': playback_info['audioQuality'],
                        'codec': manifest['codecs'],
                        'url': manifest['urls'][0],
                        'encryptionKey': manifest['keyId'] if 'encryptionType' in manifest and manifest[
                            'encryptionType'] != 'NONE' else ''
                    }
                except TidalRequestError as te:
                    print('\t' + str(te))
            else:
                print('\t' + str(te))

        if stream_data is None:
            raise ValueError('Stream could not be acquired')

    def print_track_info(self, track_info, album_info):
        line = '\tTrack: {tracknumber}\n\tTitle: {title}\n\tArtist: {artist}\n\tAlbum: {album}'.format(
            **self.tm.tags(track_info, album_info))
        try:
            print(line)
        except UnicodeEncodeError:
            line = line.encode('ascii', 'replace').decode('ascii')
            print(line)
        print('\t----')

    def search_for_id(self, term):
        return self.api.get_search_data(term)

    def page(self, pageurl):
        return self.api.get_page(pageurl)

    def type_from_id(self, id):
        return self.api.get_type_from_id(id)

    def credits_from_album(self, album_id):
        return self.api.get_credits(album_id)

    def playlist_from_id(self, id):
        return self.api.get_playlist(id)

    def download_media(self, track_info, album_info=None, overwrite=False):
        track_id = track_info['id']
        assert track_info['allowStreaming'], 'Unable to download track {0}: not allowed to stream/download'.format(
            track_id)

        print('=== Downloading track ID {0} ==='.format(track_id))

        # Check if track is video
        if 'type' in track_info:
            playback_info = self.api.get_video_stream_url(track_id)
            url = playback_info['url']
            if not 'resolution' in self.opts:
                self.opts['resolution'] = 1080
            download_stream(self.opts['path'], url, self.opts['resolution'], track_info)

        else:
            if album_info is None:
                print('\tGrabbing album info...')
                tries = self.opts['tries']
                for i in range(tries):
                    try:
                        album_info = self.api.get_album(track_info['album']['id'])
                        break
                    except Exception as e:
                        print(e)
                        print('\tGrabbing album info failed, retrying... ({}/{})'.format(i + 1, tries))
                        if i + 1 == tries:
                            raise

            # Make locations
            album_location = path.join(
                self.opts['path'], self.opts['album_format'].format(
                    **self._normalise_info(track_info, album_info, True))).strip()
            album_location = re.sub(r'\.+$', '', album_location)
            track_file = self.opts['track_format'].format(
                **self._normalise_info(track_info, album_info))
            if len(track_file) > 255:  # trim filename to be under OS limit (and account for file extension)
                track_file = track_file[:250 - len(track_file)]
            track_file = re.sub(r'\.+$', '', track_file)
            _mkdir_p(album_location)
            # Make multi disc directories
            if album_info['numberOfVolumes'] > 1:
                disc_location = path.join(
                    album_location,
                    'CD{num}'.format(num=track_info['volumeNumber']))
                disc_location = re.sub(r'\.+$', '', disc_location)
                _mkdir_p(disc_location)

            # Attempt to get stream URL
            # stream_data = self.get_stream_url(track_id, quality)

            DRM = False 
            playback_info = self.api.get_stream_url(track_id, self.opts['quality'])
                
            manifest_unparsed = base64.b64decode(playback_info['manifest']).decode('UTF-8')
            if 'ContentProtection' in manifest_unparsed:
                DRM = True 
                print("\tWarning: DRM has been detected. If you do not have the decryption key, do not use web login.")
            elif 'manifestMimeType' in playback_info:
                if playback_info['manifestMimeType'] == 'application/dash+xml':
                    raise AssertionError('\tPlease use a mobile session for the track ' + str(playback_info['trackId'])
                                         + ' in ' + str(playback_info['audioQuality']) + ' audio quality. This cannot '
                                                                                         'be downloaded with a TV '
                                                                                         'session for now.\n')
                
            if not DRM:
                manifest = json.loads(manifest_unparsed)
                # Detect codec
                print('\tCodec: ', end='')
                print(technical_names[manifest['codecs']])

                url = manifest['urls'][0]
                if url.find('.flac?') == -1:
                    if url.find('.m4a?') == -1:
                        if url.find('.mp4?') == -1:
                            ftype = ''
                        else:
                            ftype = 'm4a'
                    else:
                        ftype = 'm4a'
                else:
                    ftype = 'flac'
            #ftype needs to be changed to work with audio codecs instead when with web auth
            else:
                ftype ='flac'

            if album_info['numberOfVolumes'] > 1:
                track_path = path.join(disc_location, track_file + '.' + ftype)
            else:
                track_path = path.join(album_location, track_file + '.' + ftype)

            if path.isfile(track_path) and not overwrite:
                print('\tFile {} already exists, skipping.'.format(track_path))
                return None

            self.print_track_info(track_info, album_info)

            if DRM:
                manifest = manifest_unparsed
                # Get playback link
                pattern = re.compile(r'(?<=media=")[^"]+')
                playback_link = pattern.findall(manifest)[0].replace("amp;", "")

                # Create album tmp folder
                tmp_folder = os.path.join(album_location, 'tmp/')

                if not os.path.isdir(tmp_folder):
                    os.makedirs(tmp_folder)

                pattern = re.compile(r'(?<= r=")[^"]+')
                # Add 2?
                length = int(pattern.findall(manifest)[0]) + 3

                # Download all chunk files from MPD
                with open(album_location + '/encrypted.mp4','wb') as encrypted_file:    
                    for i in range(length):
                        link = playback_link.replace("$Number$", str(i))
                        filename = os.path.join(tmp_folder, str(i).zfill(3) + '.mp4')
                        download_file([link], 0, filename)
                        with open(filename,'rb') as fd:
                            shutil.copyfileobj(fd, encrypted_file)
                        print(
                        "\tDownload progress: {0:.0f}%".format(((i+1) / length) * 100),
                        end='\r')
                print()
                os.chdir(album_location)

                decryption_key = input("\tInput key (ID:key): ")
                print("\tDecrypting m4a")
                try:
                    os.system('mp4decrypt --key {} encrypted.mp4 "{}"'.format(decryption_key, track_file + '.m4a'))
                    ('tmp')
                except Exception as e:
                    print(e)
                    print('mp4decrypt not found!')

                temp_file = track_path
                print("\tRemuxing m4a to FLAC")
                (
                    ffmpeg
                        .input(track_file + '.m4a')
                        .output(track_file + '.flac', acodec="copy", loglevel='warning')
                        .overwrite_output()
                        .run()
                )
                shutil.rmtree("tmp")
                os.remove('encrypted.mp4')
                os.remove(track_file + '.m4a')
                os.chdir('../../')

            if not DRM:
                temp_file = self._dl_url(url, track_path)

                if 'encryptionType' in manifest and manifest['encryptionType'] != 'NONE':
                    if not manifest['keyId'] == '':
                        print('\tLooks like file is encrypted. Decrypting...')
                        key, nonce = decrypt_security_token(manifest['keyId'])
                        decrypt_file(temp_file, key, nonce)

            try:
                aa_location = path.join(album_location, 'Cover.jpg')
                if not path.isfile(aa_location):
                    try:
                        artwork_size = 1200
                        if 'artwork_size' in self.opts:
                            if self.opts['artwork_size'] == 0:
                                raise Exception
                            artwork_size = self.opts['artwork_size']

                        print('\tDownloading album art from iTunes...')
                        s = requests.Session()

                        params = {
                            'country': 'US',
                            'entity': 'album',
                            'term': track_info['artist']['name'] + ' ' + track_info['album']['title']
                        }

                        r = s.get('https://itunes.apple.com/search', params=params)
                        r = r.json()
                        album_cover = None

                        for i in range(len(r['results'])):
                            if album_info['title'] == r['results'][i]['collectionName']:
                                # Get high resolution album cover
                                album_cover = r['results'][i]['artworkUrl100']
                                break

                        if album_cover is None:
                            raise Exception

                        compressed = 'bb'
                        if 'uncompressed_artwork' in self.opts:
                            if self.opts['uncompressed_artwork']:
                                compressed = '-999'
                        album_cover = album_cover.replace('100x100bb.jpg',
                                                          '{}x{}{}.jpg'.format(artwork_size, artwork_size, compressed))
                        self._dl_url(album_cover, aa_location)

                        if ftype == 'flac':
                            # Open cover.jpg to check size
                            with open(aa_location, 'rb') as f:
                                data = f.read()

                            # Check if cover is smaller than 16MB
                            max_size = 16777215
                            if len(data) > max_size:
                                print('\tCover file size is too large, only {0:.2f}MB are allowed.'.format(
                                    max_size / 1024 ** 2))
                                print('\tFallback to compressed iTunes cover')

                                album_cover = album_cover.replace('-999', 'bb')
                                self._dl_url(album_cover, aa_location)
                    except:
                        print('\tDownloading album art from Tidal...')
                        if not self._dl_picture(track_info['album']['cover'], aa_location):
                            aa_location = None

                # Converting FLAC to ALAC
                if self.opts['convert_to_alac'] and ftype == 'flac':
                    print("\tConverting FLAC to ALAC...")
                    conv_file = temp_file[:-5] + ".m4a"
                    # command = 'ffmpeg -i "{0}" -vn -c:a alac "{1}"'.format(temp_file, conv_file)
                    (
                        ffmpeg
                            .input(temp_file)
                            .output(conv_file, acodec='alac', loglevel='warning')
                            .overwrite_output()
                            .run()
                    )

                    if path.isfile(conv_file) and not overwrite:
                        print("\tConversion successful")
                        os.remove(temp_file)
                        temp_file = conv_file
                        ftype = "m4a"

                # Get credits from album id
                print('\tSaving credits to file')
                album_credits = self.credits_from_album(str(album_info['id']))
                credits_dict = {}
                try:
                    track_credits = album_credits['items'][track_info['trackNumber']-1]['credits']
                    for i in range(len(track_credits)):
                        credits_dict[track_credits[i]['type']] = ''
                        contributors = track_credits[i]['contributors']
                        for j in range(len(contributors)):
                            if j != len(contributors) - 1:
                                credits_dict[track_credits[i]['type']] += contributors[j]['name'] + ', '
                            else:
                                credits_dict[track_credits[i]['type']] += contributors[j]['name']

                    if credits_dict != {}:
                        if 'save_credits_txt' in self.opts:
                            if self.opts['save_credits_txt']:
                                data = ''
                                for key, value in credits_dict.items():
                                    data += key + ': '
                                    data += value + '\n'
                                with open((os.path.splitext(track_path)[0] + '.txt'), 'w') as f:
                                    f.write(data)
                        # Janky way to set the dict to None to tell the tagger not to include it
                        if 'embed_credits' in self.opts:
                            if not self.opts['embed_credits']:
                                credits_dict = None
                except IndexError:
                    credits_dict = None

                # Get lyrics from Deezer using deemix (https://codeberg.org/RemixDev/deemix)
                lyrics = None
                if self.opts['lyrics']:
                    for provider in self.opts['lyrics_provider_order']:
                        if provider == 'Deezer':
                            if self.opts['lyrics']:
                                print('\tGetting lyrics from Deezer...')
                                track_lyrics = {}
                                song = None
                                try:
                                    song = self.dz.get_track_by_ISRC(track_info['isrc'])
                                except APIError:
                                    print('\tTrack could not be found using ISRC. Searching for track using the title, '
                                          'artist and album...')
                                    try:
                                        song = self.dz.get_track(self.dz.get_track_from_metadata(
                                            track_info['artist']['name'], track_info['title'],
                                            track_info['album']['title']))
                                    except APIError:
                                        print('\tNo Track could be found!')
                                        continue
                                if song:
                                    # Get album genres from Deezer
                                    try:
                                        genres = self.dz.get_album(song['album']['id'])['genres']
                                        if 'data' in genres and len(genres['data']) > 0:
                                            track_info['genre'] = []
                                            for genre in genres['data']:
                                                track_info['genre'].append(genre['name'])
                                    except APIError:
                                        print('\tNo genres found!')
                                    try:
                                        track_lyrics = self.dz.get_lyrics_gw(song['id'])
                                    except APIError:
                                        print('\tNo lyrics for the given track could be found!')
                                        continue

                                track = {}
                                if "LYRICS_TEXT" in track_lyrics:
                                    lyrics = track_lyrics["LYRICS_TEXT"]
                                else:
                                    print('\tNo unsynced lyrics could be found!')
                                if "LYRICS_SYNC_JSON" in track_lyrics:
                                    track['sync'] = ""
                                    lastTimestamp = ""
                                    for i in range(len(track_lyrics["LYRICS_SYNC_JSON"])):
                                        if "lrc_timestamp" in track_lyrics["LYRICS_SYNC_JSON"][i]:
                                            track['sync'] += track_lyrics["LYRICS_SYNC_JSON"][i]["lrc_timestamp"]
                                            lastTimestamp = track_lyrics["LYRICS_SYNC_JSON"][i]["lrc_timestamp"]
                                        else:
                                            track['sync'] += lastTimestamp
                                        track['sync'] += track_lyrics["LYRICS_SYNC_JSON"][i]["line"] + "\r\n"
                                else:
                                    print('\tNo synced lyrics could be found!')

                                if 'sync' in track:
                                    if not os.path.isfile(os.path.splitext(track_path)[0] + '.lrc'):
                                        with open((os.path.splitext(track_path)[0] + '.lrc'), 'wb') as f:
                                            f.write(track['sync'].encode('utf-8'))

                                # Lyrics found, break the loop
                                break
                        if provider == 'musiXmatch':
                            print('\tGetting lyrics from musiXmatch...')
                            track = {}
                            s = requests.Session()

                            params = {
                                'q_artist': track_info['artist']['name'],
                                'q_track': track_info['title'],
                                'usertoken': '2008072b3b27588cf3e55818e5582da7032354ad9978df228acaf5',
                                'app_id': 'android-player-v1.0'
                            }

                            r = s.get('https://apic.musixmatch.com/ws/1.1/macro.subtitles.get', params=params)

                            # Get unsynced lyrics
                            track_lyrics = r.json()['message']['body']['macro_calls']['track.lyrics.get']['message']
                            if track_lyrics['header']['status_code'] == 200:
                                lyrics = track_lyrics['body']['lyrics']['lyrics_body']
                            elif track_lyrics['header']['status_code'] == 404:
                                print('\tNo unsynced lyrics could be found!')

                            # Get synced lyrics
                            track_subtitles = r.json()['message']['body']['macro_calls']['track.subtitles.get'][
                                'message']
                            if track_subtitles['header']['status_code'] == 200:
                                if len(track_subtitles['body']) > 0:
                                    track['sync'] = track_subtitles['body']['subtitle_list'][0]['subtitle'][
                                        'subtitle_body']
                                else:
                                    print('\tNo synced lyrics could be found!')
                            elif track_subtitles['header']['status_code'] == 404:
                                print('\tNo synced lyrics could be found!')
                                continue

                            if 'sync' in track:
                                if not os.path.isfile(os.path.splitext(track_path)[0] + '.lrc'):
                                    with open((os.path.splitext(track_path)[0] + '.lrc'), 'wb') as f:
                                        f.write(track['sync'].encode('utf-8'))

                            # Lyrics found, break the loop
                            break

                # Tagging
                print('\tTagging media file...')

                if ftype == 'flac':
                    self.tm.tag_flac(temp_file, track_info, album_info, lyrics, credits_dict=credits_dict,
                                     album_art_path=aa_location)
                elif ftype == 'm4a' or ftype == 'mp4':
                    self.tm.tag_m4a(temp_file, track_info, album_info, lyrics, credits_dict=credits_dict,
                                    album_art_path=aa_location)
                else:
                    print('\tUnknown file type to tag!')

                # Cleanup
                if not self.opts['keep_cover_jpg'] and aa_location:
                    os.remove(aa_location)

                return album_location, temp_file

            # Delete partially downloaded file on keyboard interrupt
            except KeyboardInterrupt:
                if path.isfile(track_path):
                    print('Deleting partially downloaded file ' + str(track_path))
                    os.remove(track_path)
                raise
