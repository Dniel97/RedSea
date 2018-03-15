import getpass
import pickle
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
        resp = requests.get(
            self.TIDAL_API_BASE + url,
            headers={
                'X-Tidal-SessionId': self.session_id
            },
            params=params).json()
        if 'status' in resp and not resp['status'] == 200:
            raise TidalError(resp)
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


class TidalSessionStore(object):
    '''
    Tidal session store which can get/set/list/save sessions

    NOTE: This is hacky shit! Needs a rewrite
    TODO: Refactor into two classes (one for session file, one for session)
    '''

    def __init__(self, session_file):
        self.token_desktop = '4zx46pyr9o8qZNRw'
        self.token_mobile = 'kgsOOmYk3zShYrNP'
        self.TIDAL_CLIENT_VERSION = '1.9.1'
        self.TIDAL_API_BASE = 'https://api.tidalhifi.com/v1/'

        self.sessions = None
        self.active = None

        self.session_file = session_file
        if not self.load_file():
            raise ValueError('Session file could not be loaded!')

    def new_session(self):
        '''
        Authenticates with Tidal service

        Returns True if successful
        '''
        print('LOGIN: Enter your Tidal username and password:\n')
        username = input('Username: ')
        password = getpass.getpass('Password: ')

        token = None
        while token is None:
            auth_type = input('Would you like to auth as a desktop or mobile device [D/m]? ')
            if auth_type.upper() == 'D' or auth_type == '':
                token = self.token_desktop
            elif auth_type.upper() == 'M':
                token = self.token_mobile
            else:
                print('Invalid entry! Please choose "D" or "m".')

        self.uniqueId = str(uuid.uuid4()).replace('-', '')[16:]

        postParams = {
            'username': username,
            'password': password,
            'token': token,
            'clientUniqueKey': self.uniqueId,
            'clientVersion': self.TIDAL_CLIENT_VERSION
        }

        self.active = requests.post(self.TIDAL_API_BASE + 'login/username', data=postParams).json()
        self.active['auth_token'] = token
        self.active['default'] = False

        if 'status' in self.active and not self.active['status'] == 200:
            raise TidalError(self.active)
        return True

    def load_file(self):
        '''
        Attempts to load sessions file and return contents

        Returns False if file does not exist and is not created
        '''
        try:
            with open(self.session_file, 'rb') as f:
                self.sessions = pickle.load(f)
                f.close()
                return True
        except FileNotFoundError:
            print('Sessions file "{}" not found!'.format(self.session_file))
            confirm = input('Would you like to create one [Y/n]? ')
            if confirm is '' or confirm.upper() == 'Y':
                self.sessions = {}
                with open(self.session_file, 'wb') as f:
                    pickle.dump(self.sessions, f)
                    f.close()
                    return True
            else:
                print('No sessions file created.')
                return False

    def save_file(self):
        '''
        Attempts to write current session store to file

        Returns True on success
        '''
        if self.sessions is not None:
            with open(self.session_file, 'wb') as f:
                pickle.dump(self.sessions, f)
            return True
        else:
            raise ValueError('There are no currently loaded sessions')

    def load_session(self, name=''):
        '''
        Loads session from session store by name
        '''
        if self.sessions is None:
            raise ValueError('There are no currently loaded sessions')

        if name is '' and len(self.sessions) > 0:
            while self.active is None:
                for s in self.sessions:
                    if 'default' in self.sessions[s] and self.sessions[s]['default'] == True:
                        self.active = self.sessions[s]
                        return self.active
                print('ERROR: No default session has been set!')
                self.set_default()
        elif name in self.sessions:
            self.active = self.sessions[name]
            return self.active
        elif len(self.sessions) == 0:
            confirm = input('No sessions found. Would you like to login now [Y/n]? ')
        else:
            confirm = input('No session "{}" found. Would you like to login now [Y/n]? '.format(name))
            
        if confirm is '' or confirm.upper() == 'Y':
            if self.new_session():
                self.save_session(name=name)

        return self.active

    def save_session(self, name=''):
        '''
        Save session to session store file
        '''
        if self.sessions is None:
            raise ValueError('There is no session file loaded')

        if self.active is None:
            raise ValueError('Active session is missing. Make sure you are logged in.')

        while name == '':
            name = input('What would you like to call this new session? ')
            if not name == '':
                if len(self.sessions) == 0:
                    self.active['default'] = True
                    print('Session "{}" has been set as the default session.'.format(name))
                else:
                    confirm = input('Would you like to set this session as default [y/N]? ')
                    if confirm.upper() == 'Y':
                        self.active['default'] = True
                print('Session named "{}". Use the -a flag when running redsea to choose session'.format(name))
            else:
                confirm = input('Invalid entry! Would you like to cancel [y/N]? ')
                if confirm is not '' and confirm.upper() == 'Y':
                    return False
        
        if name in self.sessions:
            confirm = input('A session with name "{}" already exists. Overwrite [y/N]? '.format(name))
            if confirm is not '' and confirm.upper() == 'Y':
                return False
        
        self.sessions[name] = self.active
        self.save_file()
        print('New session "{}" has been added'.format(name))

    def remove_session(self, name=None):
        '''
        Removes a session from the session store
        '''

        if not self.list_accounts():
            return False

        while name == None:
            n = input('Type the full name of the session you would like to remove: ')
            if not n == '':
                name = n
            else:
                confirm = input('Invalid entry! Would you like to cancel [y/N]? ')
                if confirm is not '' and confirm.upper() == 'Y':
                    return False
        
        if self.sessions.pop(name, True) == True:
            print('Error removing session "{}"'.format(name))
        else:
            self.save_file()
            print('Session "{}" successfully removed'.format(name))

    def list_accounts(self):
        '''
        doc
        '''
        if self.sessions is None:
            raise ValueError('There is no session file loaded')
        
        if len(self.sessions) == 0:
            print('No sessions currently stored')
            return False

        default = None
        print('\nSESSIONS:')
        for s in self.sessions:
            print('  ' + s)
            if 'default' in self.sessions[s] and self.sessions[s]['default'] == True:
                default = s
        print('')
        if default is not None:
            print('Default session is currently set to: {}'.format(default))
            print('')
        
        return True

    def set_default(self):
        '''
        Sets a session as the default
        '''

        if not self.list_accounts():
            return False

        while True:
            name = input('Please provide the name of the session you would like to set as default: ')
            if name is not '' and name in self.sessions:
                for s in self.sessions:
                    self.sessions[s]['default'] = False
                self.sessions[name]['default'] = True
                self.save_file()
                print('Default session has successfully been set to "{}"'.format(name))
                return True
            else:
                print('ERROR: Session "{}" not found in sessions store!'.format(name))

        return False
