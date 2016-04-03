import json

import requests

class TidalError(Exception):
    def __init__(self, payload):
        sf = '{subStatus}: {userMessage} (HTTP {status})'.format(**payload)
        self.payload = payload
        super(TidalError, self).__init__(sf)

class TidalApi(object):
    TIDAL_API_BASE = 'https://api.tidalhifi.com/v1/'

    def __init__(self, session_id, country_code):
        self.session_id = session_id
        self.country_code = country_code

    def _get(self, url, params={}):
        params['countryCode'] = self.country_code
        resp = json.loads(requests.get(self.TIDAL_API_BASE + url, headers={'X-Tidal-SessionId': self.session_id}, params=params).text)
        if 'status' in resp and not resp['status'] == 200:
            raise TidalError(resp)
        return resp

    def login(self, username, password, token, clientUniqueId):
        pass

    def get_stream_url(self, track_id, quality):
        return self._get('tracks/' + str(track_id) +'/offlineUrl', {'soundQuality': quality})

    def get_playlist_items(self, playlist_id):
        return self._get('playlists/' + playlist_id + '/items', {'offset': 0, 'limit': 100})

    def get_album_tracks(self, album_id):
        return self._get('albums/' + str(album_id) + '/tracks')

    def get_track(self, track_id):
        return self._get('tracks/' + str(track_id))

    def get_album(self, album_id):
        return self._get('albums/' + str(album_id))

    @classmethod
    def get_album_artwork_url(cls, album_id, size=1280):
        return 'https://resources.tidal.com/images/{0}/{1}x{1}.jpg'.format(album_id.replace('-', '/'), size)