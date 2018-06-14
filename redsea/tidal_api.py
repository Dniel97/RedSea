import pickle
import uuid

import requests


class TidalRequestError(Exception):

    def __init__(self, payload):
        sf = '{subStatus}: {userMessage} (HTTP {status})'.format(**payload)
        self.payload = payload
        super(TidalRequestError, self).__init__(sf)

class TidalError(Exception):

    def __init__(self, message):
        self.message = message
        super(TidalError, self).__init__(message)

class TidalApi(object):
    TIDAL_API_BASE = 'https://api.tidalhifi.com/v1/'
    TIDAL_CLIENT_VERSION = '1.9.1'

    def __init__(self, session_id, country_code):
        self.session_id = session_id
        self.country_code = country_code

    def _get(self, url, params={}):
        params['countryCode'] = self.country_code
        
        resp = requests.get(
            self.TIDAL_API_BASE + url,
            headers={
                'X-Tidal-SessionId': self.session_id
            },
            params=params).json()
        
        if 'status' in resp and resp['status'] == 404 and resp['subStatus'] == 2001:
            raise TidalError('Error: {}. This might be region-locked.'.format(resp['userMessage']))
        
        if 'status' in resp and not resp['status'] == 200:
            raise TidalRequestError(resp)
        
        return resp

    def get_stream_url(self, track_id, quality):
        return self._get('tracks/' + str(track_id) + '/streamUrl',
                         {'soundQuality': quality})

    def get_playlist_items(self, playlist_id):
        return self._get('playlists/' + playlist_id + '/items', {
            'offset': 0,
            'limit': 100
        })

    def get_album_tracks(self, album_id):
        return self._get('albums/' + str(album_id) + '/tracks')

    def get_track(self, track_id):
        return self._get('tracks/' + str(track_id))

    def get_album(self, album_id):
        return self._get('albums/' + str(album_id))

    def get_video(self, video_id):
        return self._get('videos/' + str(video_id))

    def get_favorite_tracks(self, user_id):
        return self._get('users/' + str(user_id) + '/favorites/tracks',
                         {'limit': 9999})

    def get_track_contributors(self, track_id):
        return self._get('tracks/' + str(track_id) + '/contributors')

    def get_video_stream_url(self, video_id):
        return self._get('videos/' + str(video_id) + '/streamurl')

    @classmethod
    def get_album_artwork_url(cls, album_id, size=1280):
        return 'https://resources.tidal.com/images/{0}/{1}x{1}.jpg'.format(
            album_id.replace('-', '/'), size)

class TidalSession(object):
    '''
    Tidal session object which can be used to communicate with Tidal servers
    '''

    def __init__(self, username, password, token='4zx46pyr9o8qZNRw'):
        '''
        Initiate a new session
        '''
        self.TIDAL_CLIENT_VERSION = '1.9.1'
        self.TIDAL_API_BASE = 'https://api.tidalhifi.com/v1/'

        self.username = username
        self.token = token
        self.unique_id = str(uuid.uuid4()).replace('-', '')[16:]

        self.auth(password)

        password = None

    def auth(self, password):
        '''
        Attempts to authorize and create a new valid session
        '''

        postParams = {
            'username': self.username,
            'password': password,
            'token': self.token,
            'clientUniqueKey': self.unique_id,
            'clientVersion': self.TIDAL_CLIENT_VERSION
        }

        r = requests.post(self.TIDAL_API_BASE + 'login/username', data=postParams).json()

        password = None

        if 'status' in r and not r['status'] == 200:
            raise TidalRequestError(r)

        self.session_id = r['sessionId']
        self.user_id = r['userId']
        self.country_code = r['countryCode']

    def session_type(self):
        '''
        Returns the type of token used to create the session
        '''
        if self.token == '4zx46pyr9o8qZNRw':
            return 'Desktop'
        elif self.token == 'kgsOOmYk3zShYrNP':
            return 'Mobile'
        else:
            return 'Other/Unknown'

    def valid(self):
        '''
        Checks if session is still valid and returns True/False
        '''
        r = requests.get(self.TIDAL_API_BASE + 'users/' + self.user_id).json()

        if 'status' in r and not r['status'] == 200:
            return False
        else:
            return True


class TidalSessionFile(object):
    '''
    Tidal session storage file which can save/retrieve/list sessions
    '''

    def __init__(self, session_file):
        self.VERSION = '1.0'
        self.session_file = session_file # Session file path
        self.session_store = None  # Will contain data from session file
        self.sessions = None  # Will contain session from session_store['sessions']
        self.default = None  # Specifies the name of the default session to use

        with open(self.session_file, 'rb') as f:
            self.session_store = pickle.load(f)
            if 'version' in self.session_store and self.session_store['version'] == self.VERSION:
                self.sessions = self.session_store['sessions']
                self.default = self.session_store['default']
            elif 'version' in self.session_store:
                raise ValueError(
                    'Session file is version {} while redsea expects version {}'.
                    format(self.session_store['version'], self.VERSION))
            else:
                raise ValueError('Existing session file is malformed. Please rebuild session file.')
            f.close()

    def _save(self):
        '''
        Attempts to write current session store to file
        '''

        if self.sessions is not None:
            self.session_store['version'] = self.VERSION
            self.session_store['sessions'] = self.sessions
            self.session_store['default'] = self.default

            with open(self.session_file, 'wb') as f:
                pickle.dump(self.session_store, f)
        else:
            raise ValueError('There are no currently loaded sessions')

    def new_session(self, session_name, username, password, token='4zx46pyr9o8qZNRw'):
        '''
        Create a new TidalSession object and auth with Tidal server
        '''

        if session_name not in self.sessions:
            self.sessions[session_name] = TidalSession(username, password, token=token)
            password = None

            if len(self.sessions) < 2:
                self.default = session_name
        else:
            password = None
            raise ValueError('Session "{}" already exists in sessions file!'.format(session_name))

        self._save()

    def remove(self, session_name):
        '''
        Removes a session from the session store and saves the session file
        '''

        if session_name not in self.sessions:
            raise ValueError('Session "{}" does not exist in session store.'.format(session_name))

        self.sessions.pop(session_name)
        self._save()

    def load(self, session_name=None):
        '''
        Returns a session from the session store
        '''

        if session_name is None:
            session_name = self.default
        
        if session_name in self.sessions:
            return self.sessions[session_name]

        raise ValueError('Session "{}" could not be found.'.format(session_name))

    def set_default(self, session_name):
        '''
        Set a default session to return when 
        load() is called without a session name
        '''

        if session_name in self.sessions:
            self.default = session_name