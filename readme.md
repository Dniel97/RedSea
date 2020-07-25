**This fork is based on zpoo32's fork of stephanlensky's fork of redsudo's fork of mreweilk's fork of svbnet's Redsea where I've disabled a bunch of features to allow for Dolby Atmos downloading. It can also download MQAs (Master quality). Now updated for Tidal 2.26.1 to make way for E-AC-3 downloading for when someone with a rooted NVIDIA Shield TV comes to help with this. This method is unlikely to be patched by Tidal, although there is a very easy way to patch it.**

To get this to work you MUST set your own auth header retrieved from MITM'ing a Tidal (version 2.26.1) APK that has its target version changed (and also cloned with something like App Cloner for some reason, maybe some protection is bypassed by it), which you must get yourself, as it is copyrighted material. To use this downloader you must install Fiddler-Everywhere on any computer and follow [this guide](https://www.telerik.com/blogs/how-to-capture-android-traffic-with-fiddler). Note that the guide is for the old version of Fiddler, so the placement of the options will be different, and so will the port (Everywhere usually has port 8866). Once you have done that, play a song on tidal, select any api.tidal.com entry, and copy the text next to 'X-Tidal-Token:' and'Authorization:' in the header tab on the right side, and copy it into the config file.

To download MQA, also add -p MQA to your command line arguments. For other types of files, look at stock presets below, as this downloader is set up to download Dolby Atmos by default. (Also, tagging is broken for AAC files, as nobody cares about them but it is an easy fix, just replace ftype in the tagging section of mediadownloader.py with the codec name provided by the metadata)

If you are a Windows user, you might want to check out [Athame](https://github.com/svbnet/Athame), a graphical music download client. It also seems to work well on Mono, if you use Linux or OS X.

RedSea
======
Music downloader and tagger for Tidal. For educational use only, and may break in the future.

Current state
-------------
RedSea is currently being worked on by members of RED. Reach out to RedSudo for more info

Introduction
------------
RedSea is a music downloader and tagger for the Tidal music streaming service. It is designed partially as a Tidal API example. This repository also hosts a wildly incomplete Python Tidal
API implementation - it is contained in `config/tidal_api.py` and only requires `requests` to be
installed. Note that you will you have to implement the Tidal lossless download hack yourself -- you can find this in `mediadownloader.py`.

Requirements
------------
* Python (3.5 or higher)
* requests
* mutagen (1.37 or higher)
* pycrypto

Optional
--------
* ffmpeg - only needed if `convert_to_alac` is enabled inside a preset

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

Format variables are `{title}`, `{artist}`, `{album}`, `{tracknumber}`.

`track_format`: How tracks are formatted. The relevant extension is appended to the end.

`album_format`: Base album directory - tracks and cover art are stored here. May have slashes in it, for instance {artist}/{album}.
