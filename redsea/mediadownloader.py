import errno
import json
import os
import os.path as path
import re
import sys
import pathlib
import base64

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from .decryption import decrypt_file, decrypt_security_token
from .tagger import FeaturingFormat
from .tidal_api import TidalApi, TidalRequestError


def _mkdir_p(path):
    try:
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
        r = self.session.get(url, stream=True)
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
        name = re.sub(r'[\\\/*?"<>|]', '', name)
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
                    playback_info = self.api.get_stream_url_workaround(track_id, quality)
                    manifest = json.loads(base64.b64decode(playback_info['manifest']))
                    stream_data = {
                        'soundQuality': playback_info['audioQuality'],
                        'codec': manifest['codecs'],
                        'url': manifest['urls'][0],
                        'encryptionKey': manifest['keyId']
                    }
                except TidalRequestError as te:
                    print('\t' + str(te))
            else:
                print('\t' + str(te))

        if stream_data is None:
            raise ValueError('Stream could not be acquired')

        if stream_data['soundQuality'] not in quality:
            if not (stream_data['codec'] == 'MQA' and quality[0] == 'HI_RES'):
                raise ValueError('ERROR: {} quality requested, but only {} quality available.'.
                    format(quality, stream_data['soundQuality']))

        return stream_data

    def print_track_info(self, track_info, album_info):
        line = '\tTrack: {tracknumber}\n\tTitle: {title}\n\tArtist: {artist}\n\tAlbum: {album}'.format(
            **self.tm.tags(track_info, album_info))
        try:
            print(line)
        except UnicodeEncodeError:
            line = line.encode('ascii', 'replace').decode('ascii')
            print(line)
        print('\t----')

    def download_media(self, track_info, quality, album_info=None, overwrite=False):
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
            **self._normalise_info(track_info, album_info)).strip()
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
        stream_data = self.get_stream_url(track_id, quality)

        # Hacky way to get extension of file from URL
        ftype = None
        url = stream_data['url']
        if url.find('.flac?') == -1:
            if url.find('.m4a?') == -1:
                if url.find('.mp4?') == -1:
                    ftype = ''
                else:
                    ftype = 'mp4'
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
            temp_file = self._dl_url(stream_data['url'], track_path)

            if not stream_data['encryptionKey'] == '':
                print('\tLooks like file is encrypted. Decrypting...')
                key, nonce = decrypt_security_token(stream_data['encryptionKey'])
                decrypt_file(temp_file, key, nonce)

            aa_location = path.join(album_location, 'Cover.jpg')
            if not path.isfile(aa_location):
                print('\tDownloading album art...')
                if not self._dl_picture(track_info['album']['cover'], aa_location):
                    aa_location = None

            # Tagging
            print('\tTagging media file...')

            if ftype == 'flac':
                self.tm.tag_flac(temp_file, track_info, album_info, aa_location)
            elif ftype == 'm4a' or ftype == 'mp4':
                self.tm.tag_m4a(temp_file, track_info, album_info, aa_location)
            else:
                print('\tUnknown file type to tag!')

            # Cleanup
            if not self.opts['keep_cover_jpg'] and aa_location:
                os.remove(aa_location)

            return (album_location, temp_file)

        # Delete partially downloaded file on keyboard interrupt
        except KeyboardInterrupt:
            if path.isfile(track_path):
                print('Deleting partially downloaded file ' + str(track_path))
                os.remove(track_path)
            raise
