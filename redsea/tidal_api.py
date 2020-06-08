import pickle
import uuid
import os
import json
import urllib.parse as urlparse
from urllib.parse import parse_qs
import hashlib
import base64
import secrets
from datetime import datetime, timedelta

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from config.settings import TIDALSESSION, AUTHHEADER


class TidalRequestError(Exception):
    def __init__(self, payload):
        sf = '{subStatus}: {userMessage} (HTTP {status})'.format(**payload)
        self.payload = payload
        super(TidalRequestError, self).__init__(sf)


class TidalAuthError(Exception):
    def __init__(self, message):
        super(TidalAuthError, self).__init__(message)


class TidalError(Exception):
    def __init__(self, message):
        self.message = message
        super(TidalError, self).__init__(message)


class TidalApi(object):
    TIDAL_API_BASE = 'https://api.tidalhifi.com/v1/'
    TIDAL_CLIENT_VERSION = '2.25.1'

    def __init__(self, session):
        self.session = session
        self.s = requests.Session()
        retries = Retry(total=10,
                        backoff_factor=0.4,
                        status_forcelist=[429, 500, 502, 503, 504])

        self.s.mount('http://', HTTPAdapter(max_retries=retries))
        self.s.mount('https://', HTTPAdapter(max_retries=retries))

    def _get(self, url, params={}, refresh=False):
        params['countryCode'] = 'US'
        if 'limit' not in params:
            params['limit'] = '9999'
        resp = self.s.get(
            self.TIDAL_API_BASE + url,
            headers={'X-Tidal-SessionId': TIDALSESSION, 'User-Agent': 'TIDAL_ANDROID/992 okhttp/3.13.1', 'Authorization': AUTHHEADER},
            params=params)

        # if the request 401s or 403s, try refreshing the session in case that helps
        if not refresh and (resp.status_code == 401 or resp.status_code == 403) and isinstance(self.session, TidalMobileSession):
            self.session.refresh()
            return self._get(url, params, True)

        resp_json = None
        try:
            resp_json = resp.json()
        except:  # some tracks seem to return a JSON with leading whitespace
            try:
                resp_json = json.loads(resp.text.strip())
            except:  # if this doesn't work, the HTTP status probably isn't 200. Are we rate limited?
                pass

        if not resp_json:
            raise TidalError('Response was not valid JSON. HTTP status {}. {}'.format(resp.status_code, resp.text))

        if 'status' in resp_json and resp_json['status'] == 404 and resp_json['subStatus'] == 2001:
            raise TidalError('Error: {}. This might be region-locked.'.format(resp_json['userMessage']))

        if 'status' in resp_json and not resp_json['status'] == 200:
            raise TidalRequestError(resp_json)

        return resp_json

    def get_stream_url(self, track_id, quality):
        return self._get('tracks/' + str(track_id) + '/streamUrl',
                         {'soundQuality': quality})

    def get_stream_url_workaround(self, track_id, quality):

        return self._get('tracks/' + str(track_id) + '/playbackinfopostpaywall', {
            'audioMode': 'DOLBY_ATMOS',
            'playbackmode': 'STREAM',
            'assetpresentation': 'FULL',
            'audioquality': 'LOW'  # TODO: use highest quality from 'quality' arg instead of defaulting to HI_RES
        })

    def get_playlist_items(self, playlist_id):
        result = self._get('playlists/' + playlist_id + '/items', {
            'offset': 0,
            'limit': 100
        })

        if (result['totalNumberOfItems'] <= 100):
            return result

        offset = len(result['items'])
        while True:
            buf = self._get('playlists/' + playlist_id + '/items', {
                'offset': offset,
                'limit': 100
            })
            offset += len(buf['items'])
            result['items'] += buf['items']

            if offset >= result['totalNumberOfItems']:
                break

        return result

    def get_album_tracks(self, album_id):
        return self._get('albums/' + str(album_id) + '/tracks')

    def get_track(self, track_id):
        return self._get('tracks/' + str(track_id))

    def get_album(self, album_id):
        return self._get('albums/' + str(album_id))

    def get_video(self, video_id):
        return self._get('videos/' + str(video_id))

    def get_favorite_tracks(self, user_id):
        return self._get('users/' + str(user_id) + '/favorites/tracks')

    def get_track_contributors(self, track_id):
        return self._get('tracks/' + str(track_id) + '/contributors')

    def get_video_stream_url(self, video_id):
        return self._get('videos/' + str(video_id) + '/streamurl')

    def get_artist(self, artist_id):
        return self._get('artists/' + str(artist_id))

    def get_artist_albums(self, artist_id):
        return self._get('artists/' + str(artist_id) + '/albums')

    def get_artist_albums_ep_singles(self, artist_id):
        return self._get('artists/' + str(artist_id) + '/albums', params={'filter': 'EPSANDSINGLES'})

    @classmethod
    def get_album_artwork_url(cls, album_id, size=1280):
        return 'https://resources.tidal.com/images/{0}/{1}x{1}.jpg'.format(
            album_id.replace('-', '/'), size)


class TidalSession(object):
    '''
    Tidal session object which can be used to communicate with Tidal servers
    '''

    def __init__(self, username, password, token='wc8j_yBJd20zOmx0'):
        '''
        Initiate a new session
        '''
        self.TIDAL_CLIENT_VERSION = '2.25.1'
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

        r = requests.post(self.TIDAL_API_BASE + 'login/username', data=postParams)

        password = None

        if 'status' in r and not r['status'] == 200:
            raise TidalRequestError(r)

        self.session_id = r['sessionId']
        self.user_id = r['userId']
        self.country_code = r['countryCode']

        assert self.valid(), 'This session has an invalid sessionId. Please re-authenticate'

    def session_type(self):
        '''
        Returns the type of token used to create the session
        '''
        if self.token == 'MbjR4DLXz1ghC4rV':
            return 'Desktop'
        elif self.token == 'wc8j_yBJd20zOmx0':
            return 'Mobile'
        else:
            return 'Other/Unknown'

    def valid(self):
        '''
        Checks if session is still valid and returns True/False
        '''

        r = requests.get(self.TIDAL_API_BASE + 'users/' + str(self.user_id), headers=self.auth_headers()).json()

        if 'status' in r and not r['status'] == 200:
            return False
        else:
            return True

    def auth_headers(self):
        return {'X-Tidal-SessionId': self.session_id}


class TidalMobileSession(TidalSession):
    '''
    Tidal session object based on the mobile Android oauth flow
    '''
    def __init__(self, username, password, client_id='ck3zaWMi8Ka_XdI0'):
        self.TIDAL_LOGIN_BASE = 'https://login.tidal.com/'
        self.TIDAL_AUTH_BASE = 'https://auth.tidal.com/v1/'

        self.username = username
        self.client_id = client_id
        self.redirect_uri = 'https://tidal.com/android/login/auth'
        self.code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=')
        self.code_challenge = base64.urlsafe_b64encode(hashlib.sha256(self.code_verifier).digest()).rstrip(b'=')
        self.client_unique_key = secrets.token_hex(16)

        self.access_token = None
        self.refresh_token = None
        self.expires = None
        self.user_id = None
        self.country_code = None

        self.auth(password)

    def auth(self, password):
        s = requests.Session()

        params = {
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'lang': 'en_US',
            'appMode': 'android',
            'client_id': self.client_id,
            'client_unique_key': self.client_unique_key,
            'code_challenge': self.code_challenge,
            'code_challenge_method': 'S256'
        }

        # retrieve csrf token for subsequent request
        r = s.get('https://login.tidal.com/authorize', params=params)

        # enter email, verify email is valid
        r = s.post('https://login.tidal.com/email', params=params, json={
            '_csrf': s.cookies['token'],
            'email': self.username,
            'recaptchaResponse': ''
        })
        assert(r.status_code == 200)
        if not r.json()['isValidEmail']:
            raise TidalAuthError('Invalid email')
        if r.json()['newUser']:
            raise TidalAuthError('User does not exist')

        # login with user credentials
        r = s.post('https://login.tidal.com/email/user/existing', params=params, json={
            '_csrf': s.cookies['token'],
            'email': self.username,
            'password': password
        })
        assert(r.status_code == 200)

        # retrieve access code
        r = s.get('https://login.tidal.com/success?lang=en', allow_redirects=False)
        if r.status_code == 401:
            raise TidalAuthError('Incorrect password')
        assert(r.status_code == 302)
        url = urlparse.urlparse(r.headers['location'])
        oauth_code = parse_qs(url.query)['code'][0]

        # exchange access code for oauth token
        r = requests.post('https://auth.tidal.com/v1/oauth2/token', data={
            'code': oauth_code,
            'client_id': self.client_id,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'scope': 'r_usr w_usr w_sub',
            'code_verifier': self.code_verifier,
            'client_unique_key': self.client_unique_key
        })
        assert(r.status_code == 200)

        self.access_token = r.json()['access_token']
        self.refresh_token = r.json()['refresh_token']
        self.expires = datetime.now() + timedelta(seconds=r.json()['expires_in'])

        r = requests.get('https://api.tidal.com/v1/sessions', headers=self.auth_headers())
        assert(r.status_code == 200)
        self.user_id = r.json()['userId']
        self.country_code = r.json()['countryCode']

    def valid(self):
        if self.access_token is None or datetime.now() > self.expires:
            return False
        r = requests.get('https://api.tidal.com/v1/sessions', headers=self.auth_headers())
        return r.status_code == 200

    def refresh(self):
        assert(self.refresh_token is not None)
        r = requests.post('https://auth.tidal.com/v1/oauth2/token', data={
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'grant_type': 'refresh_token'
        })
        if r.status_code == 200:
            self.access_token = r.json()['access_token']
            self.expires = datetime.now() + timedelta(seconds=r.json()['expires_in'])
            if 'refresh_token' in r.json():
                self.refresh_token = r.json()['refresh_token']
        return r.status_code == 200

    def session_type(self):
        return 'Mobile'

    def auth_headers(self):
        return {
            'User-Agent': 'TIDAL_ANDROID/992 okhttp/3.13.1',
            'authorization': 'Bearer {}'.
            format(self.access_token),
            }


class TidalSessionFile(object):
    '''
    Tidal session storage file which can save/load
    '''

    def __init__(self, session_file):
        self.VERSION = '1.0'
        self.session_file = session_file  # Session file path
        self.session_store = {}  # Will contain data from session file
        self.sessions = {}  # Will contain sessions from session_store['sessions']
        self.default = None  # Specifies the name of the default session to use

        if os.path.isfile(self.session_file):
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
                    raise ValueError('Existing session file is malformed. Please delete/rebuild session file.')
                f.close()
        else:
            self._save()
            self = TidalSessionFile(session_file=self.session_file)

    def _save(self):
        '''
        Attempts to write current session store to file
        '''

        self.session_store['version'] = self.VERSION
        self.session_store['sessions'] = self.sessions
        self.session_store['default'] = self.default

        with open(self.session_file, 'wb') as f:
            pickle.dump(self.session_store, f)

    def new_session(self, session_name, username, password, mobileSession=True):
        '''
        Create a new TidalSession object and auth with Tidal server
        '''

        if session_name not in self.sessions:
            if mobileSession:
                session = TidalMobileSession(username, password)
            else:
                session = TidalSession(username, password)
            self.sessions[session_name] = session
            password = None

            if len(self.sessions) == 1:
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

        #if len(self.sessions) == 0:
        #    raise ValueError('There are no sessions in session file!')

        if session_name is None:
            session_name = self.default

        if session_name in self.sessions:
            if not self.sessions[session_name].valid() and isinstance(self.sessions[session_name], TidalMobileSession):
                self.sessions[session_name].refresh()
            assert self.sessions[session_name].valid(), '{} has an invalid sessionId. Please re-authenticate'.format(session_name)
            return self.sessions[session_name]

        #raise ValueError('Session "{}" could not be found.'.format(session_name))

    def set_default(self, session_name):
        '''
        Set a default session to return when
        load() is called without a session name
        '''

        if session_name in self.sessions:
            assert self.sessions[session_name].valid(), '{} has an invalid sessionId. Please re-authenticate'.format(session_name)
            self.default = session_name
            self._save()
