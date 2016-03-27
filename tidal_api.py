import json

import requests

class TidalApi(object):
    TIDAL_TOKEN = 'wdgaB1CilGA-S_s2'
    TIDAL_API_BASE = 'https://api.tidalhifi.com/v1/'

    def __init__(self, session_id, country_code):
        self.session_id = session_id
        self.country_code = country_code

    def _get(self, url, params={}):
        params['countryCode'] = self.country_code
        return json.loads(requests.get(self.TIDAL_API_BASE + url, headers={'X-Tidal-SessionId': self.session_id}, params=params).text)

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

    @classmethod
    def get_album_artwork_url(cls, album_id, size=1280):
        return 'https://resources.tidal.com/images/{0}/{1}x{1}.jpg'.format(album_id.replace('-', '/'), size)