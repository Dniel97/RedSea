RedSea
======
Music downloader and tagger for Tidal. For educational use only, and may break in the future.

Current state
-------------
This fork is currently maintained by me ([Dniel97](https://github.com/Dniel97))

Introduction
------------
RedSea is a music downloader and tagger for the Tidal music streaming service. It is designed partially as a Tidal API example. This repository also hosts a wildly incomplete Python Tidal
API implementation - it is contained in `redsea/tidal_api.py` and only requires `requests` to be installed.

Requirements
------------
* Python (3.6 or higher)
* requests
* mutagen (1.37 or higher)
* pycryptodomex
* ffmpeg-python (0.2.0 or higher)
* deezerapi (already included from [deemix](https://codeberg.org/RemixDev/deemix))


First setup
-----------
After downloading RedSea, copy `config/settings.example.py` and rename it to `config/settings.py`, now you can set all your preferences inside `settings.py`.

#### Linux:
1. Run `sudo apt update` 
2. Run `sudo apt install ffmpeg`

#### MacOS:
1. If you haven't already installed Homebew: Run `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"`
2. Run `brew install ffmpeg`

#### Windows:
1. Download [ffmpeg](https://ffmpeg.zeranoe.com/builds/)
2. Unpack the zip folder `ffmpeg-XXXXX-win64-static.zip` inside `C:\Program Files\ffmpeg\`
3. Go to `Control Panel > System and Security > System > Advanced system settings > Environment Variables ...`
4. In the Environment Variables window, click the `Path` row under the `Variable` column, then click `Edit..`
5. Click on `New` inside the `Edit environment variable` window and paste `C:\Program Files\ffmpeg\bin\`

Setting up (with pip)
------------------------
1. Run `pip install -r requirements.txt` to install dependencies
2. Run `python redsea.py -h` to view the help file
3. Run `python redsea.py urls` to download lossless files from urls
4. Run `python redsea.py --file links.txt` to download tracks/albums/artists/ from a file where each line is a link

Setting up (with Pipenv)
------------------------
1. Run `pipenv install --three` to install dependencies in a virtual env using Pipenv
2. Run `pipenv run python redsea.py -h` to view the help file
3. Run `pipenv run python redsea.py urls` to download lossless files from urls

How to add accounts/sessions
----------------------------
    usage:  redsea.py auth list
            redsea.py auth add
            redsea.py auth remove
            redsea.py auth default
            redsea.py auth reauth

    positional arguments:

    list                Lists stored sessions if any exist

    add                 Prompts for a TV or Mobile session. The TV option
                        displays a 6 digit key which should be entered inside 
                        link.tidal.com where the user can login. The Mobile option
                        prompts for a Tidal username and password. Both options
                        authorize a session which then gets stored in
                        the sessions file

    remove              Removes a stored session from the sessions file
                        by name

    default             Set a default account for redsea to use when the
                        -a flag has not been passed

    reauth              Reauthenticates with server to get new sessionId

How to use
----------
    usage: redsea.py [-h] [-p PRESET] [-a ACCOUNT] [-s] [--file FILE] urls [urls ...]

    A music downloader for Tidal.

    positional arguments:
    urls                    The URLs to download. You may need to wrap the URLs in
                            double quotes if you have issues downloading.

    optional arguments:
    -h, --help              show this help message and exit
    -p PRESET, --preset PRESET
                            Select a download preset. Defaults to Lossless only.
                            See /config/settings.py for presets
    -a ACCOUNT, --account ACCOUNT
                            Select a session/account to use. Defaults to
                            the "default" session. If it does not exist, you
                            will be prompted to create one
    -s, --skip            Pass this flag to skip track and continue when a track
                            does not meet the requested quality
    --file                The URLs to download inside a .txt file with a single 
                            track/album/artist each line.

#### Searching

Searching for tracks, albums and videos is now supported.

Usage:      `python redsea.py search [track/album/video] [name of song/video, spaces are allowed]`

Example:    `python redsea.py search video Darkside Alan Walker`

#### ID downloading

Download an album/track/artist/video/playlist with just the ID instead of an URL

Usage:      `python redsea.py id [album/track/artist/video/playlist ID]`

Example:    `python redsea.py id id 92265335`

#### Exploring

Exploring new Dolby Atmos or 360 Reality Audio releases is now supported

Usage:      `python redsea.py explore (dolby atmos/sony 360)`

Example:    `python redsea.py explore dolby atmos`

Lyrics Support
--------------
Redsea supports retrieving synchronized lyrics from the services LyricFind via Deezer, and Musixmatch, automatically falling back if one doesn't have lyrics, depending on the configuration

Tidal issues
------------
* Sometimes, tracks will be tagged with a useless version (for instance, "(album version)"), or have the same version twice "(album version)(album version)". This is because tracks in
    Tidal are not consistent in terms of metadata - sometimes a version may be included in the track title, included in the version field, or both.
    
* Tracks may be tagged with an inaccurate release year; this may be because of Tidal only having the "rerelease" or "remastered" version but showing it as the original.

To do/Whishlist
---------------
* ~~ID based downloading (check if ID is a track, album, video, ...)~~
* Complete `mediadownloader.py` rewrite
* Move lyrics support to tagger.py
* Support for being used as a python module (maybe pip?)
* Maybe Spotify playlist support

Config reference
----------------

`BRUTEFORCEREGION`: When True, redsea will iterate through every available account and attempt to download when the default or specified session fails to download the release

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

`convert_to_alac`: Converts a .flac file to an ALAC .m4a file (requires ffmpeg)

`lyrics`: Enable lyrics tagging and synced lyrics as .lrc download using the Deezer API (from [deemix](https://codeberg.org/RemixDev/deemix)) or musiXmatch

`lyrics_provider_order`: Defines the order (from left to right) you want to get the lyrics from

`artwork_size`: Downloads (artwork_size)x(artwork_size) album covers from iTunes

`resolution`: Which resolution you want to download the videos

Format variables are `{title}`, `{artist}`, `{album}`, `{tracknumber}`.

`track_format`: How tracks are formatted. The relevant extension is appended to the end.

`album_format`: Base album directory - tracks and cover art are stored here. May have slashes in it, for instance {artist}/{album}.
