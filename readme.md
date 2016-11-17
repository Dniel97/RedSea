If you are a Windows user, you might want to check out [Athame](https://github.com/svbnet/Athame), a graphical music download client. It also seems to work well on Mono, if you use Linux or OS X.

RedSea
======
Music downloader and tagger for Tidal. For educational use only, and may break in the future.

Current state
-------------
RedSea is currently not being worked on any more. You are more than welcome to contribute, especially
if you would like to fix the numerous Unicode issues.

Introduction
------------
RedSea is a music downloader and tagger for the Tidal music streaming service. It is designed partially as a Tidal API example ~~and partially as a proof-of-concept of the Tidal
lossless download hack~~. Tidal seems to have fixed this hack, so you can't download FLACs on a normal subscription. :(. This repository also hosts a wildly incomplete Python Tidal
API implementation - it is contained in `tidal_api.py` and only requires `requests` to be
installed. Note that you will you have to implement the Tidal lossless download hack yourself -- you can find this in `mediadownloader.py`.

Requirements
------------
* Python 3.5
* requests
* mutagen

Setting up
----------
1. Run `pip install -r requirements.txt` to install dependencies
2. Rename  `rs_config.txt` to `rs_config.json`
3. Run `redsea auth` (or `python redsea.py auth`) to authenticate

How to use
----------
    usage: redsea.py [-h] [-o filename] [-p option] urls [urls ...]

    A music downloader for Tidal.

    positional arguments:
      urls         The URLs to download. You may need to wrap the URLs in double
                   quotes if you have issues downloading.

    optional arguments:
      -h, --help   show this help message and exit
      -o filename  The path to a config file. If not supplied, uses
                   `rs_config.json' in the current directory.
      -p option    Any options specified here in `key=value' form will override
                   the config file -- e.g. `tidal.quality=LOW' to force the
                   quality to low. This can be used multiple times.

Note that the old x:id syntax still works, but it will be removed in future commits.

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
### `tidal`

`session`: Automatically generated from authentication

`country_code`: Automatically generated from authentication

`auth_token`: Special Tidal authentication token

`quality`: either LOW (96kbps M4A), HIGH (320kbps M4A), LOSSLESS (FLAC) - both lossy formats are VBR

### `download`

`path`: Base download directory

Format variables are `{title}`, `{artist}`, `{album}`, `{tracknumber}`.

`album_format`: Base album directory - tracks and cover art are stored here. May have slashes in it, for instance {artist}/{album}.

`track_format`: How tracks are formatted. The relevant extension is appended to the end.

`keep_cover_jpg`: Whether to keep the cover.jpg file in the album directory

`tries`: How many times to attempt to get a valid stream URL.

### `tagging`

`embed_album_art`: Whether to embed album art or not into the file.