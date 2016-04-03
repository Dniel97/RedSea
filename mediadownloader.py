import os
import os.path as path
import errno
import re
import json

import requests

import tagger
from tidal_api import TidalApi, TidalError

def _mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

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
        return re.sub('[^\w\-_\. ]', '-', name)

    def _normalise_info(self, track_info):
        return {
            'title': self._sanitise_name(track_info['title']),
            'artist': self._sanitise_name(track_info['artist']['name']),
            'album': self._sanitise_name(track_info['album']['title']),
            'tracknumber': track_info['trackNumber']
        }

    def download_media(self, track_info, quality, tries, album_info=None, extras={}):
        track_id = track_info['id']
        print('=== Downloading track ID {0} ==='.format(track_id))
        print('\tTrack: {tracknumber}\n\tTitle: {title}\n\tArtist: {artist}\n\tAlbum: {album}'.format(**self._normalise_info(track_info)))
        print('\t----')

        # Make locations
        album_location = self.album_format.format(**self._normalise_info(track_info))
        track_file = self.track_format.format(**self._normalise_info(track_info))
        _mkdir_p(album_location)

        def try_get_url(ntries):
            if ntries > tries:
                print('\tExceeded maximum number of tries! Giving up...')
            print('\tGrabbing stream URL...')
            try:
                return self.api.get_stream_url(track_id, quality)
            except TidalError as te:
                if te.payload['status'] == 404:
                    print('\tTrack does not exist.')
                else:
                    print('\t' + str(te))
                    print('\tTrying again...')
                    ntries += 1
                    try_get_url(ntries)
                return

        stream_data = try_get_url(0)
        if stream_data is None:
            return

        if not stream_data['soundQuality'] == quality:
        	print('\tWARNING: {} quality requested, but only {} quality available.'.format(quality, stream_data['soundQuality']))
        if not stream_data['encryptionKey'] == '':
            print('\tUh-oh! Stream is encrypted. Perhaps you are using a desktop session ID?')
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
            tagger.tag_flac(temp_file, track_info, aa_location, extras)
        elif ftype == 'm4a':
            tagger.tag_m4a(temp_file, track_info, aa_location, extras)
        else:
            print('\tUnknown file type to tag!')

        return (album_location, temp_file)