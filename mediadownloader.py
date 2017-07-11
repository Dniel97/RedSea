import os
import os.path as path
import errno
import re
import json

import requests

from tidal_api import TidalApi, TidalError
import FeaturingFormat

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
        if album_id is not None:
            return self._dl_url(TidalApi.get_album_artwork_url(album_id), where)
        else:
            return False

    def _sanitise_name(self, name):
        return re.sub('[^\w\-_\. \(\)&\']', '-', name)

    def _normalise_info(self, track_info, album_info, use_album_artists=False):
        info = {k: self._sanitise_name(v) for k, v in self.tm.tags(track_info, album_info).items()}
        if len(album_info['artists']) > 1 and use_album_artists:
            info['artist'] = self._sanitise_name(FeaturingFormat.get_artist_format([a['name'] for a in album_info['artists'] if a['type'] == 'MAIN']))
        return info
    
    def get_stream_url(self, track_id, quality):
        tries = self.opts['tries']
        def try_get_url(ntries):
            if ntries > tries:
                print('\tExceeded maximum number of tries! Giving up...')
                return
            print('\tGrabbing stream URL...')
            try:
                return self.api.get_stream_url(track_id, quality)
            except TidalError as te:
                if te.payload['status'] == 404:
                    print('\tTrack does not exist.')
                elif te.payload['subStatus'] == 4005:
                    print('\t' + str(te))
                else:
                    print('\t' + str(te))
                    if ntries == 0 and quality == 'LOSSLESS':
                        print('\tTrying HIGH -> LOSSLESS workaround...')
                        self.api.get_stream_url(track_id, 'HIGH')
                    print('\tTrying download again...')
                    ntries += 1
                    return try_get_url(ntries)
                return

        stream_data = try_get_url(0)
        if stream_data is None:
            return
            
        if not stream_data['soundQuality'] == quality:
            print('\tWARNING: {} quality requested, but only {} quality available.'.format(quality, stream_data['soundQuality']))

        if not stream_data['encryptionKey'] == '':
            print('\tUh-oh! Stream is encrypted. Perhaps you are using a desktop session ID?')
            return
        
        return stream_data
    
    def print_track_info(self, track_info, album_info):
        line = '\tTrack: {tracknumber}\n\tTitle: {title}\n\tArtist: {artist}\n\tAlbum: {album}'.format(**self.tm.tags(track_info, album_info))
        try:
            print(line)
        except UnicodeEncodeError:
            line = line.encode('ascii', 'replace').decode('ascii')
            print(line)
        print('\t----')

    def download_media(self, track_info, quality, album_info=None):
        track_id = track_info['id']
        if not track_info['allowStreaming']:
            print('Unable to download track {0}: not allowed to stream/download. Continuing...'.format(track_id))
            return
        print('=== Downloading track ID {0} ==='.format(track_id))
        self.print_track_info(track_info, album_info)

        if album_info is None:
            print('\tGrabbing album info...')
            album_info = self.api.get_album(track_info['album']['id'])

        # Make locations
        album_location = path.join(self.opts['path'], self.opts['album_format'].format(**self._normalise_info(track_info, album_info, True)))
        track_file = self.opts['track_format'].format(**self._normalise_info(track_info, album_info))
        _mkdir_p(album_location)

        # Attempt to get stream URL
        stream_data = self.get_stream_url(track_id, quality)
        if stream_data is None:
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
            if not self._dl_picture(track_info['album']['cover'], aa_location):
                aa_location = None

        #Tagging
        print('\tTagging media file...')

        if ftype == 'flac':
            self.tm.tag_flac(temp_file, track_info, album_info, aa_location)
        elif ftype == 'm4a':
            self.tm.tag_m4a(temp_file, track_info, album_info, aa_location)
        else:
            print('\tUnknown file type to tag!')

        # Cleanup
        if not self.opts['keep_cover_jpg']:
            os.remove(aa_location)

        return (album_location, temp_file)
