import getpass

from redsea.tidal_api import TidalSessionFile, TidalRequestError

class RedseaSessionFile(TidalSessionFile):
    '''
    Redsea - TidalSession interpreter

    Provides more user-friendly cli feedback for the
    TidalSessionFile class
    '''

    def new_session(self):
        '''
        Authenticates with Tidal service

        Returns True if successful
        '''
        
        while True:
            print('LOGIN: Enter your Tidal username and password:\n')
            username = input('Username: ')
            password = getpass.getpass('Password: ')

            name = ''
            while name == '':
                name = input('What would you like to call this new session? ')
                if not name == '':
                    if name in self.sessions:
                        confirm = input('A session with name "{}" already exists. Overwrite [y/N]? '.format(name))
                        if confirm.upper() == 'Y':
                            super().remove(name)
                        else:
                            name = ''
                            continue
                else:
                    confirm = input('Invalid entry! Would you like to cancel [y/N]? ')
                    if confirm.upper() == 'Y':
                        print('Operation cancelled.')
                        return False
            
            try:
                super().new_session(name, username, password)
                break
            except TidalRequestError as e:
                if str(e).startswith('3001'):
                    print('\nUSERNAME OR PASSWORD INCORRECT. Please try again.\n\n')
                    continue
            except AssertionError as e:
                if 'invalid sessionId' in str(e):
                    print(e)
                    confirm = input('Would you like to try again [Y/n]? ')
                    if not confirm.upper() == 'N':
                        continue

        print('Session saved!')
        if not self.default == name:
            print('Session named "{}". Use the -a flag when running redsea to choose session'.format(name))
            
        return True

    def load_session(self, session_name=None):
        '''
        Loads session from session store by name
        '''

        if session_name == '':
            session_name = None

        try:
            return super().load(session_name=session_name)

        except ValueError as e:
            print(e)
            if session_name is None:
                confirm = input('No sessions found. Would you like to add one [Y/n]? ')
            else:
                confirm = input('No session "{}" found. Would you like to create it [Y/n]? '.format(session_name))

            if confirm.upper() == 'Y':
                if self.new_session():
                    if len(self.sessions) == 1:
                        return self.sessions[self.default]
                    else:
                        return self.sessions[session_name]

    def get_session(self):
        '''
        Generator which iterates through available sessions
        '''

        for session in self.sessions:
            yield self.sessions[session], session

    def remove_session(self):
        '''
        Removes a session from the session store
        '''

        self.list_sessions()

        name = ''
        while name == '':
            name = input('Type the full name of the session you would like to remove: ')
            if not name == '':
                super().remove(name)
                print('Session "{}" has been removed.'.format(name))
            else:
                confirm = input('Invalid entry! Would you like to cancel [y/N]? ')
                if confirm.upper() == 'Y':
                    return False

    def list_sessions(self):
        '''
        List all available sessions
        '''

        if len(self.sessions) == 0:
            confirm = input('No sessions found. Would you like to add one [Y/n]? ')
            if confirm.upper() == '' or confirm.upper() == 'Y':
                if self.new_session():
                    self.list_sessions()
            else:
                exit()

        print('\nSESSIONS:')
        for s in self.sessions:
            print('   [{}] {} | {}'.format(self.sessions[s].country_code, self.sessions[s].username, s))

        print('')
        if self.default is not None:
            print('Default session is currently set to: {}'.format(self.default))
            print('')

    def set_default(self):
        '''
        Sets a session as the default
        '''

        self.list_sessions()

        while True:
            name = input('Please provide the name of the session you would like to set as default: ')
            if name is not '' and name in self.sessions:
                super().set_default(name)
                print('Default session has successfully been set to "{}"'.format(name))
                return
            else:
                print('ERROR: Session "{}" not found in sessions store!'.format(name))

    def reauth(self):
        '''
        Requests password from the user and then re-auths
        with the Tidal server to get a new (valid) sessionId
        '''

        self.list_sessions()

        while True:
            name = input('Please provide the name of the session you would like to reauthenticate: ')
            if name is not '' and name in self.sessions:
                try:
                    session = self.sessions[name]

                    print('LOGIN: Enter your Tidal password for account {}:\n'.format(session.username))
                    password = getpass.getpass('Password: ')
                    session.auth(password)
                    self._save()

                    print('Session "{}" has been successfully reauthed.'.format(name))
                    return

                except TidalRequestError as e:
                    if 'Username or password is wrong' in str(e):
                        print('Error ' + str(e) + '. Please try again..')
                        continue
                    else:
                        raise(e)
                
                except AssertionError as e:
                    if 'invalid sessionId' in str(e):
                        print('Reauthentication failed. SessionID is still invalid. Please try again.')
                        print('Note: If this fails more than once, please check your account and subscription status.')
                        continue
                    else:
                        raise(e)
            else:
                print('ERROR: Session "{}" not found in sessions store!'.format(name))
