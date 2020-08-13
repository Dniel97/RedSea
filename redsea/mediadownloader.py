import errno
import json
import os
import os.path as path
import re
import base64

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from subprocess import Popen, PIPE

from .decryption import decrypt_file, decrypt_security_token
from .tagger import FeaturingFormat
from .tidal_api import TidalApi, TidalRequestError
from deezer.deezer import Deezer, APIError

# Deezer API
dz = Deezer()


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

        self.session = requests.Session()
        retries = Retry(total=10,
                        backoff_factor=0.4,
                        status_forcelist=[ 429, 500, 502, 503, 504 ])

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
                        'encryptionKey': manifest['keyId'] if 'encryptionType' in manifest and manifest['encryptionType'] != 'NONE' else ''
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

    def download_media(self, track_info, preset, album_info=None, overwrite=False):
        track_id = track_info['id']
        assert track_info['allowStreaming'], 'Unable to download track {0}: not allowed to stream/download'.format(track_id)

        print('=== Downloading track ID {0} ==='.format(track_id))

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
        if len(track_file) > 255: # trim filename to be under OS limit (and account for file extension)
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
        #stream_data = self.get_stream_url(track_id, quality)

        # Hacky way to get extension of file from URL
        #ftype = None
        playback_info = self.api.get_stream_url(track_id, preset['quality'])
        manifest = json.loads(base64.b64decode(playback_info['manifest']))

        # Detect codec
        print('\tCodec: ', end='')
        if manifest['codecs'] == 'eac3':
            print('E-AC-3 JOC (Dolby Digital Plus with Dolby Atmos metadata)')
        elif manifest['codecs'] == 'ac4':
            print('AC-4 (Dolby AC-4 with Dolby Atmos immersive stereo)')
        elif manifest['codecs'] == 'mqa' and manifest['mimeType'] == 'audio/flac':
            print('FLAC (Free Lossless Audio Codec) with folded MQA (Master Quality Authenticated) metadata')
        elif manifest['codecs'] == 'flac':
            print('FLAC (Free Lossless Audio Codec)')
        elif manifest['codecs'] == 'alac':
            print('ALAC (Apple Lossless Audio Codec)')
        elif manifest['codecs'] == 'mp4a.40.2':
            print('AAC (Advanced Audio Coding) with a bitrate of 320kb/s')
        elif manifest['codecs'] == 'mp4a.40.5':
            print('AAC (Advanced Audio Coding) with a bitrate of 96kb/s')
        else:
            print('Unknown')


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

        if album_info['numberOfVolumes'] > 1:
            track_path = path.join(disc_location, track_file + '.' + ftype)
        else:
            track_path = path.join(album_location, track_file + '.' + ftype)

        if path.isfile(track_path) and not overwrite:
            print('\tFile {} already exists, skipping.'.format(track_path))
            return None

        self.print_track_info(track_info, album_info)

        try:
            temp_file = self._dl_url(url, track_path)

            aa_location = path.join(album_location, 'Cover.jpg')
            if not path.isfile(aa_location):
                try:
                    print('\tDownloading album art from iTunes...')
                    s = requests.Session()

                    params = {
                        'country': 'US',
                        'entity': 'album',
                        'term': track_info['artist']['name'] + ' ' + track_info['album']['title']
                    }

                    r = s.get('https://itunes.apple.com/search', params=params)
                    # Get first album cover result
                    album_cover = r.json()['results'][0]['artworkUrl100']
                    # Get high resolution album cover

                    if 'artwork_size' in preset:
                        artwork_size = preset['artwork_size']
                    else:
                        artwork_size = 1200
                    album_cover = album_cover.replace('100x100bb.jpg', '{}x{}bb.jpg'.format(artwork_size, artwork_size))
                    self._dl_url(album_cover, aa_location)
                except:
                    print('\tDownloading album art from Tidal...')
                    if not self._dl_picture(track_info['album']['cover'], aa_location):
                        aa_location = None

            # Converting FLAC to ALAC
            if self.opts['convert_to_alac'] and ftype == 'flac':
                pipe = Popen('ffmpeg -version', shell=True, stdout=PIPE).stdout
                output = pipe.read()
                if output.find(b'ffmpeg version?') == -1:
                    print("\tConverting FLAC to ALAC...")
                    conv_file = temp_file[:-5] + ".m4a"
                    command = 'ffmpeg -i "{0}" -vn -c:a alac "{1}"'.format(temp_file, conv_file)
                    pipe = Popen(command, shell=True, stdout=PIPE)
                    pipe.wait()
                    if path.isfile(conv_file) and not overwrite:
                        print("\tConversion successful")
                        os.remove(temp_file)
                        temp_file = conv_file
                        ftype = "m4a"
                else:
                    print("\tFfmpeg couldn't be found")

            # Get lyrics from Deezer using deemix (https://codeberg.org/RemixDev/deemix)
            lyrics = None
            if preset['lyrics']:
                for provider in preset['lyrics_provider_order']:
                    if provider == 'Deezer':
                        if preset['lyrics']:
                            print('\tGetting lyrics from Deezer...')
                            track_lyrics = {}
                            song = None
                            try:
                                song = dz.get_track_by_ISRC(track_info['isrc'])
                            except APIError:
                                print('\tTrack could not be found using ISRC. Searching for track using the title, '
                                      'artist and album...')
                                try:
                                    song = dz.get_track(dz.get_track_from_metadata(track_info['artist']['name'], track_info['title'],
                                                                  track_info['album']['title']))
                                except APIError:
                                    print('\tNo Track could be found!')
                                    continue
                            if song:
                                # Get album genres from Deezer
                                try:
                                    genres = dz.get_album(song['album']['id'])['genres']
                                    if 'data' in genres and len(genres['data']) > 0:
                                        track_info['genre'] = []
                                        for genre in genres['data']:
                                            track_info['genre'].append(genre['name'])
                                except APIError:
                                    print('\tNo genres found!')
                                try:
                                    track_lyrics = dz.get_lyrics_gw(song['id'])
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
                                if not os.path.isfile(os.path.join(album_location, track_file + '.lrc')):
                                    with open(os.path.join(album_location, track_file + '.lrc'), 'wb') as f:
                                        f.write(track['sync'].encode('utf-8'))

                            # Lyrics found, break the loop
                            break

                    elif provider == 'musiXmatch':
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
                        track_subtitles = r.json()['message']['body']['macro_calls']['track.subtitles.get']['message']
                        if track_subtitles['header']['status_code'] == 200:
                            if len(track_subtitles['body']) > 0:
                                track['sync'] = track_subtitles['body']['subtitle_list'][0]['subtitle']['subtitle_body']
                            else:
                                print('\tNo synced lyrics could be found!')
                        elif track_subtitles['header']['status_code'] == 404:
                            print('\tNo synced lyrics could be found!')
                            continue

                        if 'sync' in track:
                            if not os.path.isfile(os.path.join(album_location, track_file + '.lrc')):
                                with open(os.path.join(album_location, track_file + '.lrc'), 'wb') as f:
                                    f.write(track['sync'].encode('utf-8'))

                        # Lyrics found, break the loop
                        break

            # Tagging
            print('\tTagging media file...')

            if ftype == 'flac':
                self.tm.tag_flac(temp_file, track_info, album_info, lyrics, aa_location)
            elif ftype == 'm4a' or ftype == 'mp4':
                self.tm.tag_m4a(temp_file, track_info, album_info, lyrics, aa_location)
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
