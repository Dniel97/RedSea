If you are a Windows user, you might want to check out [Athame](https://github.com/svbnet/Athame), a graphical music download client. It also seems to work well on Mono, if you use Linux or OS X.

RedSea
======
Music downloader and tagger for Tidal. For educational use only, and may break in the future.

Current state
-------------
RedSea is currently being worked on by members of RED. Reach out to RedSudo for more info

Introduction
------------
RedSea is a music downloader and tagger for the Tidal music streaming service. It is designed partially as a Tidal API example ~~and partially as a proof-of-concept of the Tidal
lossless download hack~~. Tidal seems to have fixed this hack, so you can't download FLACs on a normal subscription. :(. This repository also hosts a wildly incomplete Python Tidal
API implementation - it is contained in `config/tidal_api.py` and only requires `requests` to be
installed. Note that you will you have to implement the Tidal lossless download hack yourself -- you can find this in `mediadownloader.py`.

Requirements
------------
* Python 3.5
* requests
* mutagen
* pycrypto

Setting up (with pip)
------------------------
1. Run `pip install -r requirements.txt` to install dependencies
2. Run `python redsea.py -h` to view the help file
3. Run `python redsea.py urls` to download lossless files from urls

Setting up (with Pipenv)
------------------------
1. Run `pipenv install --three` to install dependencies in a virtual env using Pipenv
2. Run `pipenv run python redsea.py -h` to view the help file
3. Run `pipenv run python redsea.py urls` to download lossless files from urls

How to use
----------
    usage: redsea.py [-h] [-p PRESET] [-a ACCOUNT] [-s] urls [urls ...]

    A music downloader for Tidal.

    positional arguments:
    urls                  The URLs to download. You may need to wrap the URLs in
                            double quotes if you have issues downloading.

    optional arguments:
    -h, --help            show this help message and exit
    -p PRESET, --preset PRESET
                            Select a download preset. Defaults to Lossless only.
                            See /config/settings.py for presets
    -a ACCOUNT, --account ACCOUNT
                            Select an account to use. Defaults to desktop account
                            as defined in /config/accounts.json
    -s, --skip            Pass this flag to skip track and continue when a track
                            does not meet the requested quality

Tidal issues
------------
* Sometimes, tracks will be tagged with a useless version (for instance, "(album version)"), or have the same version twice "(album version)(album version)". This is because tracks in
    Tidal are not consistent in terms of metadata - sometimes a version may be included in the track title, included in the version field, or both.
    
* Tracks may be tagged with an inaccurate release year; this may be because of Tidal only having the "rerelease" or "remastered" version but showing it as the original.

TODO
----
* Filename sanitisation is overzealous
* Playlists are treated like albums

Config reference
----------------

### `Stock Presets`

`default`: FLAC 44.1k / 16bit only

`best_available`: Download the highest available quality (MQA > FLAC > 320 > 96)

`mqa_flac`: Accept both MQA 24bit and FLAC 16bit

`MQA`: Only allow FLAC 44.1k / 24bit (includes 'folded' 96k content)

`FLAC`: FLAC 44.1k / 16bit only

`320`: AAC ~320 VBR only

`96`: AAC ~96 VBR only


### `Preset Configuration Variables`

`keep_cover_jpg`: Whether to keep the cover.jpg file in the album directory

`embed_album_art`: Whether to embed album art or not into the file.

`save_album_json`: save the album metadata as a json file

`tries`: How many times to attempt to get a valid stream URL.

`path`: Base download directory

Format variables are `{title}`, `{artist}`, `{album}`, `{tracknumber}`.

`track_format`: How tracks are formatted. The relevant extension is appended to the end.

`album_format`: Base album directory - tracks and cover art are stored here. May have slashes in it, for instance {artist}/{album}.


### `Accounts`

`sessionId`: Automatically generated from authentication

`countryCode`: Automatically generated from authentication

`auth_token`: Special Tidal authentication token which tells Tidal where the request is from

`userId`: Your unique Tidal account user ID