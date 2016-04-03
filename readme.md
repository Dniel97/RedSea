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

Music downloader for Tidal. For educational use only.

Requirements
------------
* Python 3.5
* requests
* mutagen

Setting up
----------
* Get a mobile session ID
* Rename rs_config.txt to rs_config.json
* Put your session ID into the `tidal_session` field in the config file
* Run redsea -h for how to use

Config file
-----------

### `tidal`

`session`: The Tidal session ID to use. Must be a mobile session.

`country_code`: Should be automatically generated. Look at sample Tidal requests to obtain.

`auth_token`: For future use.

`quality`: either LOW (96kbps M4A), HIGH (320kbps M4A), LOSSLESS (FLAC) - both lossy formats are VBR

### `download`

`path`: Base download directory

Format variables are `{title}`, `{artist}`, `{album}`, `{tracknumber}`.

`album_format`: Base album directory - tracks and cover art are stored here. May have slashes in it, for instance {artist}/{album}.

`track_format`: How tracks are formatted. The relevant extension is appended to the end.

`keep_cover_jpg`: For future use.

`save_album_json`: For future use.

`tries`: How many times to attempt to get a valid stream URL.

### `tagging`

`embed_album_art`: For future use.

`featuring_format`: For future use.

`featuring_field`: For future use.

`version_format`: If a track has a Tidal `version` field, it will be appended to the title like so (with a space in between). `{0}` is the version name.

TODO
----
* Authenticating with a username and password