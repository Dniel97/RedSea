'''
Store your redsea download presets here

You may modify/add/remove as you wish. The only preset which must exist is "default"
and you may change the default as needed.

=== Stock Presets ===
(use these with the -p flag)
default:            FLAC 44.1k / 16bit only
best_available:     Download the highest available quality (MQA > FLAC > 320 > 96)
mqa_flac:           Accept both MQA 24bit and FLAC 16bit
MQA:                Only allow FLAC 44.1k / 24bit (includes 'folded' 96k content)
FLAC:               FLAC 44.1k / 16bit only
320:                AAC ~320 VBR only
96:                 AAC ~96 VBR only

=== Options ===
keep_cover_jpg: save the cover art to the album directory
embed_album_art: embed the album art into each audio file
save_album_json: save the album metadata as a json file
tries: number of attempts before giving up on the download
path: where to store downloaded files
track_format: naming mask for tracks
album_format: naming mask for abum directories

=== Formats ===
MQA_FLAC_24: MQA Format / 24bit FLAC with high-frequency "folded" data
FLAC_16: 16bit FLAC
AAC_320: 320Kbps AAC
AAC_96: 96Kbps AAC

'''

import json

PRESETS = {

    # Default settings / only download FLAC_16
    "default": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": False,
        "FLAC_16": True,
        "AAC_320": False,
        "AAC_96": False
    },

    # This will download the highest available quality including MQA
    "best_available": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": True,
        "FLAC_16": True,
        "AAC_320": True,
        "AAC_96": True
    },

    # This preset will allow FLAC_16 and MQA files only
    "mqa_flac": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": True,
        "FLAC_16": True,
        "AAC_320": False,
        "AAC_96": False
    },

    # This preset will only download MQA
    "MQA": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": True,
        "FLAC_16": False,
        "AAC_320": False,
        "AAC_96": False
    },


    # This preset will only download FLAC 16
    "FLAC": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": False,
        "FLAC_16": True,
        "AAC_320": False,
        "AAC_96": False
    },


    # This preset will only download AAC ~320
    "320": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": False,
        "FLAC_16": False,
        "AAC_320": True,
        "AAC_96": False
    },


    # This preset will only download AAC ~96
    "96": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": False,
        "FLAC_16": False,
        "AAC_320": False,
        "AAC_96": True
    },
}

def get_accounts(atext='./config/accounts.txt', 
                 ajson='./config/accounts.json',
                 auth_types={
                     'desktop': '4zx46pyr9o8qZNRw',
                     'mobile': 'kgsOOmYk3zShYrNP',
                 }):
    '''
    This method attempts to load the accounts file. If the file cannot be loaded,
    it attempts to generate the accounts file by providing a method of authentication
    '''
    try:
        with open(ajson) as f:
            return json.load(f)
    except FileNotFoundError as e:
        try:
            import getpass

            from redsea.tidal_api import TidalApi

            print('AUTHENTICATION: Enter your Tidal username and password:\n')
            uname = input('Username: ')
            pswd = getpass.getpass('Password: ')

            print('Attempting authentication...')
            accounts = {}
            for t in auth_types:
                auth = TidalApi.login(uname, pswd, auth_types[t])
                auth['auth_token'] = auth_types[t]
                accounts[t] = auth

            print('Writing sessions to file...')
            with open(ajson, 'w') as f:
                json.dump(accounts, f, indent='\t')
                f.close()

            print('Success! Continuing..')
            return accounts

        except Exception as e:
            print('Authentication failed. Reverting changes..')
            import os
            if ajson is not None and os.path.isfile(ajson):
                os.remove(ajson)
            raise e

ACCOUNTS = get_accounts()