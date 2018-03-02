'''
Store your redsea download presets here

You may modify/add/remove as you wish. The only preset which must exist is "default"
and you may change the default as needed.

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

try:
    from .accounts import ACCOUNTS
except ModuleNotFoundError as e:
    import shutil
    import fileinput
    import getpass
    from redsea.tidal_api import TidalApi

    print('AUTHENTICATION: Enter your Tidal username and password:\n')
    uname = input('Username: ')
    pswd = getpass.getpass('Password: ')

    print('Creating account store...')
    shutil.copy('./config/accounts.txt', './config/accounts.py')

    print('Attempting authentication...')
    auth = TidalApi.login(uname, pswd, 'kgsOOmYk3zShYrNP')

    for line in fileinput.input('./config/accounts.py', inplace=True):
        print(
            line.replace('{session}', auth['sessionId']).replace(
                '{country_code}', auth['countryCode']), end='')

    print('Success! Continuing..')


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
    "mqa_lossless": {
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
    "mqa_only": {
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
}