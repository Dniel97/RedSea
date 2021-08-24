import pickle
import uuid
import os
import re
import json
import urllib.parse as urlparse
import webbrowser
from urllib.parse import parse_qs
import hashlib
import base64
import secrets
from datetime import datetime, timedelta
import urllib3
import time
import sys
import prettytable

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from subprocess import Popen, PIPE

from config.settings import TOKEN, MOBILE_TOKEN, TV_TOKEN, TV_SECRET, WEB_TOKEN, SHOWAUTH

technical_names = {
    'eac3': 'E-AC-3 JOC (Dolby Digital Plus with Dolby Atmos, with 5.1 bed)',
    'mha1': 'MPEG-H 3D Audio (Sony 360 Reality Audio)',
    'ac4': 'AC-4 IMS (Dolby AC-4 with Dolby Atmos immersive stereo)',
    'mqa': 'MQA (Master Quality Authenticated) in FLAC container',
    'flac': 'FLAC (Free Lossless Audio Codec)',
    'alac': 'ALAC (Apple Lossless Audio Codec)',
    'mp4a.40.2': 'AAC 320 (Advanced Audio Coding) with a bitrate of 320kb/s',
    'mp4a.40.5': 'AAC 96 (Advanced Audio Coding) with a bitrate of 96kb/s'
}


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


class TidalApi:
    TIDAL_API_BASE = 'https://api.tidal.com/v1/'
    TIDAL_VIDEO_BASE = 'https://api.tidalhifi.com/v1/'
    TIDAL_CLIENT_VERSION = '2.26.1'

    def __init__(self, session):
        self.session = session
        self.s = requests.Session()
        retries = Retry(total=10,
                        backoff_factor=0.4,
                        status_forcelist=[429, 500, 502, 503, 504])

        self.s.mount('http://', HTTPAdapter(max_retries=retries))
        self.s.mount('https://', HTTPAdapter(max_retries=retries))

    def _get(self, url, params=None, refresh=False):
        if params is None:
            params = {}
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        params['countryCode'] = self.session.country_code
        if 'limit' not in params:
            params['limit'] = '9999'

        # Catch video for different base
        if url[:5] == 'video':
            resp = self.s.get(
                self.TIDAL_VIDEO_BASE + url,
                headers=self.session.auth_headers(),
                params=params,
                verify=False)
        else:
            resp = self.s.get(
                self.TIDAL_API_BASE + url,
                headers=self.session.auth_headers(),
                params=params,
                verify=False)

        # if the request 401s or 403s, try refreshing the TV/Mobile session in case that helps
        if not refresh and (resp.status_code == 401 or resp.status_code == 403):
            if isinstance(self.session, TidalMobileSession) or isinstance(self.session, TidalTvSession):
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

        if 'status' in resp_json and resp_json['status'] == 404 and \
                'subStatus' in resp_json and resp_json['subStatus'] == 2001:
            raise TidalError('Error: {}. This might be region-locked.'.format(resp_json['userMessage']))

        # Really hacky way
        if 'status' in resp_json and resp_json['status'] == 404 and \
                'error' in resp_json and resp_json['error'] == 'Not Found':
            return resp_json

        if 'status' in resp_json and not resp_json['status'] == 200:
            raise TidalRequestError(resp_json)

        return resp_json

    def get_stream_url(self, track_id, quality):

        return self._get('tracks/' + str(track_id) + '/playbackinfopostpaywall', {
            'playbackmode': 'STREAM',
            'assetpresentation': 'FULL',
            'audioquality': quality[0],
            'prefetch': 'false'
        })

    def get_search_data(self, searchterm):
        return self._get('search', params={
            'query': str(searchterm),
            'offset': 0,
            'limit': 20,
            'includeContributors': 'true'
        })

    def get_page(self, page_url, offset=None):
        return self._get('pages/' + page_url, params={
            'deviceType': 'TV',
            'locale': 'en_US',
            'limit': 50,
            'offset': offset if offset else None
        })

    def get_credits(self, album_id):
        return self._get('albums/' + album_id + '/items/credits', params={
            'replace': True,
            'offset': 0,
            'limit': 50,
            'includeContributors': True
        })

    def get_video_credits(self, video_id):
        return self._get('videos/' + video_id + '/contributors', params={
            'limit': 50
        })

    def get_lyrics(self, track_id):
        return self._get('tracks/' + str(track_id) + '/lyrics', params={
            'deviceType': 'PHONE',
            'locale': 'en_US'
        })

    def get_playlist_items(self, playlist_id):
        result = self._get('playlists/' + playlist_id + '/items', {
            'offset': 0,
            'limit': 100
        })

        if result['totalNumberOfItems'] <= 100:
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

    def get_playlist(self, playlist_id):
        return self._get('playlists/' + str(playlist_id))

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

    def get_type_from_id(self, id_):
        result = None
        try:
            result = self.get_album(id_)
            return 'a'
        except TidalError:
            pass
        try:
            result = self.get_artist(id_)
            return 'r'
        except TidalError:
            pass
        try:
            result = self.get_track(id_)
            return 't'
        except TidalError:
            pass
        try:
            result = self.get_video(id_)
            return 'v'
        except TidalError:
            pass

        return result

    @classmethod
    def get_album_artwork_url(cls, album_id, size=1280):
        return 'https://resources.tidal.com/images/{0}/{1}x{1}.jpg'.format(
            album_id.replace('-', '/'), size)


class SessionFormats:
    def __init__(self, session):
        self.mqa_trackid = '91950969'
        self.dolby_trackid = '131069353'
        self.sony_trackid = '142292058'

        self.quality = ['HI_RES', 'LOSSLESS', 'HIGH', 'LOW']

        self.formats = {
            'eac3': False,
            'mha1': False,
            'ac4': False,
            'mqa': False,
            'flac': False,
            'alac': False,
            'mp4a.40.2': False,
            'mp4a.40.5': False
        }

        try:
            self.check_formats(session)
        except TidalRequestError:
            print('\tERROR: No (HiFi) subscription found!')

    def check_formats(self, session):
        api = TidalApi(session)

        for id in [self.dolby_trackid, self.sony_trackid]:
            playback_info = api.get_stream_url(id, ['LOW'])
            if playback_info['manifestMimeType'] == 'application/dash+xml':
                continue
            manifest_unparsed = base64.b64decode(playback_info['manifest']).decode('UTF-8')
            if 'ContentProtection' not in manifest_unparsed:
                self.formats[json.loads(manifest_unparsed)['codecs']] = True

        for i in range(len(self.quality)):
            playback_info = api.get_stream_url(self.mqa_trackid, [self.quality[i]])
            if playback_info['manifestMimeType'] == 'application/dash+xml':
                continue

            manifest_unparsed = base64.b64decode(playback_info['manifest']).decode('UTF-8')
            if 'ContentProtection' not in manifest_unparsed:
                self.formats[json.loads(manifest_unparsed)['codecs']] = True

    def print_fomats(self):
        table = prettytable.PrettyTable()
        table.field_names = ['Codec', 'Technical name', 'Supported']
        table.align = 'l'
        for format in self.formats:
            table.add_row([format, technical_names[format], self.formats[format]])

        string_table = '\t' + table.__str__().replace('\n', '\n\t')
        print(string_table)
        print('')


class ReCaptcha(object):
    def __init__(self):
        self.captcha_path = 'captcha/'

        self.response_v3 = None
        self.response_v2 = None

        self.get_response()

    @staticmethod
    def check_npm():
        pipe = Popen('npm -version', shell=True, stdout=PIPE).stdout
        output = pipe.read().decode('UTF-8')
        found = re.search(r'[0-9].[0-9]+.', output)
        if not found:
            print("NPM could not be found.")
            return False
        return True

    def get_response(self):
        if self.check_npm():
            print("Opening reCAPTCHA check...")
            command = 'npm start --prefix '
            pipe = Popen(command + self.captcha_path, shell=True, stdout=PIPE)
            pipe.wait()
            output = pipe.stdout.read().decode('UTF-8')
            pattern = re.compile(r"(?<='response': ')[0-9A-Za-z-_]+")
            response = pattern.findall(output)
            if len(response) > 2:
                print('You only need to complete the captcha once.')
                return False
            elif len(response) == 1:
                self.response_v3 = response[0]
                return True
            elif len(response) == 2:
                self.response_v3 = response[0]
                self.response_v2 = response[1]
                return True

            print('Please complete the reCAPTCHA check.')
            return False


class TidalSession:
    '''
    Tidal session object which can be used to communicate with Tidal servers
    '''

    def __init__(self, username, password):
        '''
        Initiate a new session
        '''
        self.TIDAL_CLIENT_VERSION = '2.26.1'
        self.TIDAL_API_BASE = 'https://api.tidal.com/v1/'

        self.username = username
        self.token = TOKEN
        self.unique_id = str(uuid.uuid4()).replace('-', '')[16:]

        self.session_id = None
        self.user_id = None
        self.country_code = None

        # simple fix for OOB
        if username != '' and password != '':
            self.auth(password)

        password = None

    def auth(self, password):
        '''
        Attempts to authorize and create a new valid session
        '''

        params = {
            'username': self.username,
            'password': password,
            'token': self.token,
            'clientUniqueKey': self.unique_id,
            'clientVersion': self.TIDAL_CLIENT_VERSION
        }

        r = requests.post(self.TIDAL_API_BASE + 'login/username', data=params, verify=False)

        password = None

        if not r.status_code == 200:
            raise TidalRequestError(r)

        self.session_id = r.json()['sessionId']
        self.user_id = r.json()['userId']
        self.country_code = r.json()['countryCode']

        assert self.valid(), 'This session has an invalid sessionId. Please re-authenticate'
        self.check_subscription()

    @staticmethod
    def session_type():
        '''
        Returns the type of token used to create the session
        '''
        return 'Desktop'

    def check_subscription(self):
        '''
        Checks if subscription is either HiFi or Premium Plus
        '''
        r = requests.get(f'{self.TIDAL_API_BASE}users/{self.user_id}/subscription',
                         headers=self.auth_headers(), verify=False)
        assert (r.status_code == 200)
        if r.json()['subscription']['type'] not in ['HIFI', 'PREMIUM_PLUS']:
            raise TidalAuthError('You need a HiFi subscription')

    def valid(self):
        '''
        Checks if session is still valid and returns True/False
        '''
        if not isinstance(self, TidalSession):
            if self.access_token is None or datetime.now() > self.expires:
                return False

        r = requests.get(f'{self.TIDAL_API_BASE}sessions', headers=self.auth_headers(), verify=False)
        return r.status_code == 200

    def auth_headers(self):
        return {
            'Host': 'api.tidal.com',
            'User-Agent': 'okhttp/3.12.3',
            'X-Tidal-Token': self.token,
            'X-Tidal-SessionId': self.session_id,
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
        }


class TidalMobileSession(TidalSession):
    '''
    Tidal session object based on the mobile Android oauth flow
    '''

    def __init__(self, username, password):
        # init the TidalSession class first
        super(TidalMobileSession, self).__init__('', '')

        self.TIDAL_LOGIN_BASE = 'https://login.tidal.com/api/'
        self.TIDAL_AUTH_BASE = 'https://auth.tidal.com/v1/'

        self.username = username
        self.client_id = MOBILE_TOKEN
        self.redirect_uri = 'https://tidal.com/android/login/auth'
        self.code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=')
        self.code_challenge = base64.urlsafe_b64encode(hashlib.sha256(self.code_verifier).digest()).rstrip(b'=')
        self.client_unique_key = secrets.token_hex(16)
        self.user_agent = 'Mozilla/5.0 (Linux; Android 10; wv) AppleWebKit/537.36''(KHTML, like Gecko)' \
                          'Version/4.0 Chrome/90.0.4430.91 Mobile Safari/537.36'

        self.access_token = None
        self.refresh_token = None
        self.expires = None
        self.user_id = None
        self.cid = None
        self.country_code = None

        self.auth(password)

    def auth(self, password, use_recaptcha=False):
        s = requests.Session()

        params = {
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'lang': 'en_US',
            'appMode': 'android',
            'client_id': self.client_id,
            'client_unique_key': self.client_unique_key,
            'code_challenge': self.code_challenge,
            'code_challenge_method': 'S256',
            'restrict_signup': True
        }

        # retrieve csrf token for subsequent request
        r = s.get('https://login.tidal.com/authorize', params=params, verify=False, headers={
            'User-Agent': self.user_agent
        })

        if r.status_code == 400:
            raise TidalAuthError("Authorization failed! Is the clientid/token up to date?")
        elif r.status_code == 403:
            raise TidalAuthError("Tidal BOT Protection, try again later!")

        recaptcha_response = ''

        if use_recaptcha:
            captcha = ReCaptcha()

            r = s.post(self.TIDAL_LOGIN_BASE + 'recaptcha/verify/v3', json={
                'token': captcha.response_v3
            }, verify=False, headers={
                'User-Agent': self.user_agent,
                'x-csrf-token': s.cookies['_csrf-token']
            })

            assert (r.status_code == 200)

            print('reCAPTCHA v3 score: ' + str(r.json()['score']))

            if not r.json()['success']:
                raise TidalAuthError(r.json())

            if not r.json()['skipRecaptchaV2']:
                recaptcha_response = captcha.response_v2

        # enter email, verify email is valid
        r = s.post(self.TIDAL_LOGIN_BASE + 'email', params=params, json={
            'email': self.username,
            'recaptchaResponse': recaptcha_response
        }, verify=False, headers={
            'User-Agent': self.user_agent,
            'x-csrf-token': s.cookies['_csrf-token']
        })

        if r.status_code == 401:
            raise TidalAuthError('Recaptcha check is missing')

        assert (r.status_code == 200)
        if not r.json()['isValidEmail']:
            raise TidalAuthError('Invalid email')
        if r.json()['newUser']:
            raise TidalAuthError('User does not exist')

        # login with user credentials
        r = s.post(self.TIDAL_LOGIN_BASE + 'email/user/existing', params=params, json={
            'email': self.username,
            'password': password
        }, verify=False, headers={
            'User-Agent': self.user_agent,
            'x-csrf-token': s.cookies['_csrf-token']
        })

        assert (r.status_code == 200)

        # retrieve access code
        r = s.get('https://login.tidal.com/success?lang=en', allow_redirects=False, verify=False, headers={
            'User-Agent': self.user_agent
        })
        if r.status_code == 401:
            raise TidalAuthError('Incorrect password')
        assert (r.status_code == 302)
        url = urlparse.urlparse(r.headers['location'])
        oauth_code = parse_qs(url.query)['code'][0]

        # exchange access code for oauth token
        r = requests.post(self.TIDAL_AUTH_BASE + 'oauth2/token', data={
            'code': oauth_code,
            'client_id': self.client_id,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'scope': 'r_usr w_usr w_sub',
            'code_verifier': self.code_verifier,
            'client_unique_key': self.client_unique_key
        }, verify=False, headers={
            'User-Agent': self.user_agent
        })
        assert (r.status_code == 200)

        self.access_token = r.json()['access_token']
        self.refresh_token = r.json()['refresh_token']
        self.expires = datetime.now() + timedelta(seconds=r.json()['expires_in'])

        if SHOWAUTH:
            print('Your Authorization token: ' + self.access_token)

        r = requests.get(f'{self.TIDAL_API_BASE}sessions', headers=self.auth_headers(), verify=False)
        assert (r.status_code == 200)
        self.user_id = r.json()['userId']
        self.country_code = r.json()['countryCode']

        self.check_subscription()

    def refresh(self):
        assert (self.refresh_token is not None)
        r = requests.post(self.TIDAL_AUTH_BASE + 'oauth2/token', data={
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'grant_type': 'refresh_token'
        }, verify=False)

        if r.status_code == 200:
            print('\tRefreshing token successful')
            self.access_token = r.json()['access_token']
            self.expires = datetime.now() + timedelta(seconds=r.json()['expires_in'])

            if SHOWAUTH:
                print('Your Authorization token: ' + self.access_token)

            if 'refresh_token' in r.json():
                self.refresh_token = r.json()['refresh_token']

        elif r.status_code == 401:
            print('\tERROR: ' + r.json()['userMessage'])

        return r.status_code == 200

    def session_type(self):
        return 'Mobile'

    def auth_headers(self):
        return {
            'Host': 'api.tidal.com',
            'X-Tidal-Token': self.client_id,
            'Authorization': 'Bearer {}'.format(self.access_token),
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'User-Agent': 'TIDAL_ANDROID/1039 okhttp/3.14.9'
        }


class TidalTvSession(TidalSession):
    '''
    Tidal session object based on the mobile Android oauth flow
    '''

    def __init__(self):
        # init the TidalSession class first
        super(TidalTvSession, self).__init__('', '')

        self.TIDAL_AUTH_BASE = 'https://auth.tidal.com/v1/'

        self.username = None
        self.client_id = TV_TOKEN
        self.client_secret = TV_SECRET

        self.device_code = None
        self.user_code = None

        self.access_token = None
        self.refresh_token = None
        self.expires = None
        self.user_id = None
        self.country_code = None

        self.auth()

    def auth(self, password=''):
        s = requests.Session()

        # retrieve csrf token for subsequent request
        r = s.post(self.TIDAL_AUTH_BASE + 'oauth2/device_authorization', data={
            'client_id': self.client_id,
            'scope': 'r_usr w_usr'
        }, verify=False)

        if r.status_code == 400:
            raise TidalAuthError("Authorization failed! Is the clientid/token up to date?")
        elif r.status_code == 403:
            raise TidalAuthError("Tidal BOT Protection, try again later!")

        self.device_code = r.json()['deviceCode']
        self.user_code = r.json()['userCode']
        print('Go to https://link.tidal.com/{} and log in or sign up to TIDAL.'.format(self.user_code))
        webbrowser.open('https://link.tidal.com/' + self.user_code, new=2)

        data = {
            'client_id': self.client_id,
            'device_code': self.device_code,
            'client_secret': self.client_secret,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            'scope': 'r_usr w_usr'
        }

        status_code = 400
        print('Checking link ', end='')

        while status_code == 400:
            for index, char in enumerate("." * 5):
                sys.stdout.write(char)
                sys.stdout.flush()
                # exchange access code for oauth token
                time.sleep(0.2)
            r = requests.post(self.TIDAL_AUTH_BASE + 'oauth2/token', data=data, verify=False)
            status_code = r.status_code
            index += 1  # lists are zero indexed, we need to increase by one for the accurate count
            # backtrack the written characters, overwrite them with space, backtrack again:
            sys.stdout.write("\b" * index + " " * index + "\b" * index)
            sys.stdout.flush()

        if r.status_code == 200:
            print('\nSuccessfully linked!')
        elif r.status_code == 401:
            raise TidalAuthError('Auth Error: ' + r.json()['error'])

        self.access_token = r.json()['access_token']
        self.refresh_token = r.json()['refresh_token']
        self.expires = datetime.now() + timedelta(seconds=r.json()['expires_in'])

        if SHOWAUTH:
            print('Your Authorization token: ' + self.access_token)

        r = requests.get('https://api.tidal.com/v1/sessions', headers=self.auth_headers(), verify=False)
        assert (r.status_code == 200)
        self.user_id = r.json()['userId']
        self.country_code = r.json()['countryCode']

        r = requests.get('https://api.tidal.com/v1/users/{}?countryCode={}'.format(self.user_id, self.country_code),
                         headers=self.auth_headers(), verify=False)
        assert (r.status_code == 200)
        self.username = r.json()['username']

        self.check_subscription()

    def refresh(self):
        assert (self.refresh_token is not None)
        r = requests.post(self.TIDAL_AUTH_BASE + 'oauth2/token', data={
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token'
        }, verify=False)

        if r.status_code == 200:
            print('\tRefreshing token successful')
            self.access_token = r.json()['access_token']
            self.expires = datetime.now() + timedelta(seconds=r.json()['expires_in'])

            if SHOWAUTH:
                print('Your Authorization token: ' + self.access_token)

            if 'refresh_token' in r.json():
                self.refresh_token = r.json()['refresh_token']

        return r.status_code == 200

    def session_type(self):
        return 'Tv'

    def auth_headers(self):
        return {
            'Host': 'api.tidal.com',
            'X-Tidal-Token': self.client_id,
            'Authorization': 'Bearer {}'.format(self.access_token),
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'User-Agent': 'TIDAL_ANDROID/1039 okhttp/3.14.9'
        }


class TidalWebSession(TidalSession):
    def __init__(self, username, password):
        # init the TidalSession class first
        super(TidalWebSession, self).__init__('', '')

        self.TIDAL_LOGIN_BASE = 'https://login.tidal.com/api/'
        self.TIDAL_AUTH_BASE = 'https://auth.tidal.com/v1/'

        self.username = username
        self.client_id = WEB_TOKEN
        self.redirect_uri = 'https://listen.tidal.com/login/auth'
        self.code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=')
        self.code_challenge = base64.urlsafe_b64encode(hashlib.sha256(self.code_verifier).digest()).rstrip(b'=')
        self.client_unique_key = secrets.token_hex(16)

        self.access_token = None
        self.refresh_token = None
        self.expires = None
        self.user_id = None
        self.cid = None
        self.country_code = None

        self.auth(password)

    def auth(self, password, use_recaptcha=False):
        s = requests.Session()
        params = {
            'appMode': 'WEB',
            'client_id': self.client_id,
            'client_unique_key': self.client_unique_key,
            'code_challenge': self.code_challenge,
            'code_challenge_method': 'S256',
            'lang': 'en',
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'restrictSignup': 'true',
            'scope': "r_usr w_usr",
            'state': 'TIDAL_1600566663994_MjAwLDEwMCwxMiw2MSw1NiwxNSwxNDUsODYsMTg3LDkwLDI5LDMyLDE5MSw3NywxMzQsMjA2LDE3Nyw2NCwxMTMsMjUsMjEwLDMxLDIyMSwyNTEsMTQyLDE1MSwyNDcsMjA3LDE4MSwyMDAsNTEsMjI5',
            'utm_banner': 'na',
            'utm_campaign': 'na',
            'utm_content': 'left_menu',
            'utm_medium': 'web_player',
            'utm_source': 'tidal'
        }

        # retrieve csrf token for subsequent request
        r = s.get(self.TIDAL_LOGIN_BASE + 'authorize', params=params, verify=False)

        if r.status_code == 400:
            raise TidalAuthError("Authorization failed! Is the clientid/token up to date?")
        elif r.status_code == 403:
            raise TidalAuthError("Tidal BOT Protection, try again later!")

        recaptcha_response = ''

        if use_recaptcha:
            captcha = ReCaptcha()

            r = s.post(self.TIDAL_LOGIN_BASE + 'recaptcha/verify/v3', json={
                'token': captcha.response_v3
            }, verify=False, headers={
                'x-csrf-token': s.cookies['_csrf-token']
            })

            assert (r.status_code == 200)

            print('reCAPTCHA v3 score: ' + str(r.json()['score']))

            if not r.json()['success']:
                raise TidalAuthError(r.json())

            if not r.json()['skipRecaptchaV2']:
                recaptcha_response = captcha.response_v2

        # enter email, verify email is valid
        r = s.post('https://login.tidal.com/email', params=params, json={
            'email': self.username,
            'recaptchaResponse': recaptcha_response
        }, verify=False, headers={
            'x-csrf-token': s.cookies['_csrf-token']
        })

        if r.status_code == 401:
            raise TidalAuthError('Recaptcha check is missing')

        assert (r.status_code == 200)
        if not r.json()['isValidEmail']:
            raise TidalAuthError('Invalid email')
        if r.json()['newUser']:
            raise TidalAuthError('User does not exist')

        # login with user credentials
        r = s.post(self.TIDAL_LOGIN_BASE + 'email/user/existing', params=params, json={
            'email': self.username,
            'password': password
        }, verify=False, headers={
            'x-csrf-token': s.cookies['_csrf-token']
        })

        assert (r.status_code == 200)

        # retrieve access code
        r = s.get('https://login.tidal.com/success?lang=en', allow_redirects=False, verify=False)
        if r.status_code == 401:
            raise TidalAuthError('Incorrect password')
        assert (r.status_code == 302)
        url = urlparse.urlparse(r.headers['location'])
        oauth_code = parse_qs(url.query)['code'][0]

        # exchange access code for oauth token
        r = requests.post(self.TIDAL_AUTH_BASE + 'oauth2/token', data={
            'code': oauth_code,
            'client_id': self.client_id,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'scope': 'r_usr w_usr w_sub',
            'code_verifier': self.code_verifier,
            'client_unique_key': self.client_unique_key
        }, verify=False)
        assert (r.status_code == 200)

        self.access_token = r.json()['access_token']
        self.refresh_token = r.json()['refresh_token']
        self.expires = datetime.now() + timedelta(seconds=r.json()['expires_in'])

        if SHOWAUTH:
            print('Your Authorization token: ' + self.access_token)

        r = requests.get('https://api.tidal.com/v1/sessions', headers=self.auth_headers(), verify=False)
        assert (r.status_code == 200)
        self.user_id = r.json()['userId']
        self.country_code = r.json()['countryCode']

        self.check_subscription()

    def refresh(self):
        assert (self.refresh_token is not None)
        r = requests.post(self.TIDAL_AUTH_BASE + 'oauth2/token', data={
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'grant_type': 'refresh_token'
        }, verify=False)

        if r.status_code == 200:
            print('\tRefreshing token successful')
            self.access_token = r.json()['access_token']
            self.expires = datetime.now() + timedelta(seconds=r.json()['expires_in'])

            if SHOWAUTH:
                print('Your Authorization token: ' + self.access_token)

            if 'refresh_token' in r.json():
                self.refresh_token = r.json()['refresh_token']

        elif r.status_code == 401:
            print('\tERROR: ' + r.json()['userMessage'])

        return r.status_code == 200

    def session_type(self):
        return 'Web'

    def auth_headers(self):
        return {
            'Host': 'api.tidal.com',
            'X-Tidal-Token': self.client_id,
            'Authorization': 'Bearer {}'.format(self.access_token),
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'User-Agent': 'TIDAL_ANDROID/1039 okhttp/3.14.9'
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

    def new_session(self, session_name, username, password, device):
        '''
        Create a new TidalSession object and auth with Tidal server
        '''

        if session_name not in self.sessions:
            if device == 'mobile':
                session = TidalMobileSession(username, password)
            elif device == 'tv':
                session = TidalTvSession()
            elif device == 'web':
                session = TidalWebSession(username, password)
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

        if len(self.sessions) == 0:
            raise ValueError('There are no sessions in session file and no valid AUTHHEADER was provided!')

        if session_name is None:
            session_name = self.default

        if session_name in self.sessions:
            # TODO: Only required for old sessions, remove if possible
            if not hasattr(self.sessions[session_name], 'TIDAL_API_BASE'):
                self.sessions[session_name].TIDAL_API_BASE = 'https://api.tidal.com/v1/'

            if not self.sessions[session_name].valid() and isinstance(self.sessions[session_name], TidalMobileSession):
                self.sessions[session_name].refresh()
            if not self.sessions[session_name].valid() and isinstance(self.sessions[session_name], TidalTvSession):
                self.sessions[session_name].refresh()
            if not self.sessions[session_name].valid() and isinstance(self.sessions[session_name], TidalWebSession):
                self.sessions[session_name].refresh()
            assert self.sessions[session_name].valid(), '{} has an invalid sessionId. Please re-authenticate'.format(
                session_name)

            self._save()
            
            return self.sessions[session_name]

        raise ValueError('Session "{}" could not be found.'.format(session_name))

    def set_default(self, session_name):
        '''
        Set a default session to return when
        load() is called without a session name
        '''

        if session_name in self.sessions:
            # TODO: Only required for old sessions, remove if possible
            if not hasattr(self.sessions[session_name], 'TIDAL_API_BASE'):
                self.sessions[session_name].TIDAL_API_BASE = 'https://api.tidal.com/v1/'

            if not self.sessions[session_name].valid() and isinstance(self.sessions[session_name], TidalMobileSession):
                self.sessions[session_name].refresh()
            if not self.sessions[session_name].valid() and isinstance(self.sessions[session_name], TidalTvSession):
                self.sessions[session_name].refresh()
            if not self.sessions[session_name].valid() and isinstance(self.sessions[session_name], TidalWebSession):
                self.sessions[session_name].refresh()
            assert self.sessions[session_name].valid(), '{} has an invalid sessionId. Please re-authenticate'.format(
                session_name)
            self.default = session_name
            self._save()
