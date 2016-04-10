RedSea
======
Music streaming agent and downloader for Tidal. For educational use only, and may break in the future.

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
### The Media argument syntax
RedSea will take one or more *media arguments* when called - strings in the format <type>:<id>#[index]. Media IDs are a more concise way to represent a collection or track on Tidal.

`type` is a single-character media type: it can be **a**lbum, **p**laylist, or **t**rack.
`id` is a Tidal media identifier, which can be obtained from the URL of the media type.
`index` is an optional index to download from in a collection (album or playlist).

#### Examples
* `a:34919559` - Download the album with ID `34919559`.
* `t:26230189 a:44632346#2` - Download track `26230189`, then download track #2 off album `44632346`.
* `p:272acf40-a98f-4c7d-a3ff-c55e0e4aa921#3`- Download track #3 off playlist `272acf40-a98f-4c7d-a3ff-c55e0e4aa921`.

Tidal issues
------------
* Sometimes, tracks will be tagged with a useless version (for instance, "(album version)"), or have the same version twice "(album version)(album version)". This is because tracks in
    Tidal are not consistent in terms of metadata - sometimes a version may be included in the track title, included in the version field, or both.
* Tracks may be tagged with an inaccurate release year; this may be because of Tidal only having the "rerelease" or "remastered" version but showing it as the original.

Config
------
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