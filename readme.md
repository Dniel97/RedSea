                             `.:;::`
                         `;;;;;;;;;;;;;,
                       ,;;:           .;;;
                     ,;;;                ;;.
                    ;;++:                 `;:
                  ,;;++++++                 ;`
                 :;++++++.                  ,;
                :;+++++++                    ;
               :;++++++++++              ,;` ;
              .;++++++++++`               ;;;,
              ;++++++++++             ;,  ;
             ;;++;++++++++'           ;;:;;
            ;;++;;+++++++++:      ,   ;.;:
            ;++;;++';+++++;       ;;  ;`
           ;;++;+++;++++++        ;;;,;
           ;;+;;++;;++;'++';;;;.  ;:;;
         :;;;;'+;;++;;+++;;  .;  ;
          ;;;;;;;;;+';;++;;`   :;;;
         `;;;;;;;;;;;;;+;;;
         ;;;;;;;;;;;;;;;;;;
         ;;;;;;;;;;;;;;;;;;;
        .;;;;;;;;;;;;;;;;;;;:
        ;;;;;;;;;;;;;;;;;;;;;;`     .
       .;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;,
    ; .;;;;;;;;;;;;;;,;;;;;;;;;;;;;;;;;;;:..;`
    ;;;;;;;;;;;;;;;;    ;;;;;;;;;;;;;;;;;;;;`
     .;;;;;;;;;;;;.       ;;;;;;;;;;;;;;;;;

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
2. Run `redsea auth -` (or `python redsea.py auth -`) to authenticate

How to use
----------
You need to pass media collection identifiers to RedSea so it knows what to download. These can be obtained from Tidal URLs - for instance, in `http://listen.tidal.com/album/52331911` it is a URL for an album, with the ID `52331911`, so you would download it by executing `redsea album 52331911`.

    usage: redsea.py [-h] [-o filename] {album,playlist,track,auth} id

    A music downloader for Tidal.

    positional arguments:
      {album,playlist,track,auth}
                            the media type to download. Pass 'auth' to
                            authenticate.
      id                    The media or collection ID to download. If
                            authenticating, pass -

    optional arguments:
      -h, --help            show this help message and exit
      -o filename           The path to a config file. If not supplied, uses
                            `rs_config.json' in the current directory.

Notes on downloading
-----------------------------
Lossless downloads on a "standard" subscription may only work sometimes: this is due to a weird bug where Tidal will sometimes return a URL, but sometimes it will return a 403. This is where the `tries` config parameter comes in, as it continually repeats the stream URL request until it gets a successful response.

Config file
-----------

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

`save_album_json`: Saves the Tidal JSON representation as an album.json file.

`tries`: How many times to attempt to get a valid stream URL.

### `tagging`

`embed_album_art`: Whether to embed album art or not into the file.

### `programs`

`stream`: Program launched when RedSea is passed the `-s` option. RedSea passes one or more URLs as arguments.

`local_stream`: Program launched when RedSea is passed the `-l` option. RedSea passes one or more file paths as arguments.