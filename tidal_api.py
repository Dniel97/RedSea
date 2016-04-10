import json
import uuid

import requests

class TidalError(Exception):
    def __init__(self, payload):
        sf = '{subStatus}: {userMessage} (HTTP {status})'.format(**payload)
        self.payload = payload
        super(TidalError, self).__init__(sf)

class TidalApi(object):
    TIDAL_API_BASE = 'https://api.tidalhifi.com/v1/'
    TIDAL_CLIENT_VERSION = '1.9.1'

    def __init__(self, session_id, country_code):
        self.session_id = session_id
        self.country_code = country_code

    def _get(self, url, params={}):
        params['countryCode'] = self.country_code
        resp = requests.get(self.TIDAL_API_BASE + url, headers={'X-Tidal-SessionId': self.session_id}, params=params).json()
        if 'status' in resp and not resp['status'] == 200:
            raise TidalError(resp)
        return resp

    @classmethod
    def login(cls, username, password, token):
        url = 'login/username'
        uniqueId = str(uuid.uuid4()).replace('-', '')[16:]
        postParams = {
            'username': username, 
            'password': password, 
            'token': token, 
            'clientUniqueKey': uniqueId, 
            'clientVersion': cls.TIDAL_CLIENT_VERSION
        }
        resp = requests.post(cls.TIDAL_API_BASE + url, data=postParams).json()
        if 'status' in resp and not resp['status'] == 200:
            raise TidalError(resp)
        return resp

    def get_stream_url(self, track_id, quality):
        return self._get('tracks/' + str(track_id) +'/streamUrl', {'soundQuality': quality})

    def get_playlist_items(self, playlist_id):
        return self._get('playlists/' + playlist_id + '/items', {'offset': 0, 'limit': 100})

    def get_album_tracks(self, album_id):
        return self._get('albums/' + str(album_id) + '/tracks')

    def get_track(self, track_id):
        return self._get('tracks/' + str(track_id))

    def get_album(self, album_id):
        return self._get('albums/' + str(album_id))
    
    def get_video(self, video_id):
        return self._get('videos/' + str(video_id))
    
    # def get_video_streams(self, video_id, quality):
    #     url = self._get('videos/' + str(video_id) + '/streamurl')['url']
    #     base_url = url[:url.rfind('/')] + '/'
    #     quality_playlist = requests.get('url').text
    #     streams_playlist = ''
    #     next_line_is_streams_url = False
    #     for line in quality:
    #         if next_line_is_streams_url:
    #             streams_playlist = base_url + line.rstrip()
    #             break
    #         if line.rstrip().endswith(quality):
    #             next_line_is_streams_url = True

    @classmethod
    def get_album_artwork_url(cls, album_id, size=1280):
        return 'https://resources.tidal.com/images/{0}/{1}x{1}.jpg'.format(album_id.replace('-', '/'), size)