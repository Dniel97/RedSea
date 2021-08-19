RedSea
======
Music downloader and tagger for Tidal. For educational use only, and may break in the future.

Current state
-------------
This fork is currently maintained by me ([Dniel97](https://github.com/Dniel97))

Telegram
--------
Join the telegram group [RedSea Community](https://t.me/RedSea_Community) if you have questions, want to get help,
submit bugs or want to talk to the developer.

Introduction
------------
RedSea is a music downloader and tagger for the Tidal music streaming service. It is designed partially as a Tidal API example. This repository also hosts a wildly incomplete Python Tidal
API implementation - it is contained in `redsea/tidal_api.py` and only requires `requests` to be installed.

Choosing login types and client IDs
-----------------------------------
* To get the E-AC-3 codec version of Dolby Atmos Music, the TV sign in must be used with the client ID and secret of one of the supported Android TVs (full list below) (now included)
* To get the AC-4 codec version of Dolby Atmos music, the Mobile sign in must be used with the client ID of one of the supported phones (default mobile works)
* To get MQA, use literally anything that is not the browser, nearly all client IDs work. (In this case change the client ID of the desktop login) (bring your own anything (TV, mobile, desktop))
* To get ALAC without conversion, use the client ID of an iOS device, or the optional desktop token included from macOS (comment out the default FLAC supporting one, and uncomment the ALAC one) (secondary desktop works, or bring your own mobile)
* To get 360, use the client ID of a supported Android or iOS device (nearly all support it anyway, so that's easy) (default mobile works)

Client IDs provided by default:
* TV: FireTV with E-AC-3 (Dolby Atmos) and MQA support
* Mobile: Default has AC-4 support (which also supports MQA by extension). There is also another one which only supports MQA without AC-4 optionally (commented out)
* Desktop: Neither of the included ones support MQA! You must replace it with your own if you want MQA support! Default token can get FLACs only, whereas the optional one can get ALACs only (both are also able to get AAC)
* Browser: Is completely unsupported for now, though why would you want it anyway?

Note: Currently, mobile login is broken due to a recent change server-side on Tidal's end to validate reCAPTCHA responses finally, thus ending the saga unless we find a method to generate these responses automatically (unlikely)

Further Reading on supported devices and codecs:
* https://support.tidal.com/hc/en-us/articles/360004255778-Dolby-Atmos-Music (full up to date list of supported Android TVs for EAC-3 JOC)
* https://github.com/google/ExoPlayer/issues/6667#issuecomment-555845608 (Android phones that are actually capable of decoding AC-4, slightly outdated)
* https://www.dolby.com/experience/tidal/#tidal%20devices (some devices that support Dolby Atmos, missing a few devices that Tidal does actually support, but relatively up-to-date)
* https://avid.secure.force.com/pkb/articles/en_US/faq/AvidPlay-Distributing-Dolby-Atmos-Music-FAQ (bitrates and other background information, really interesting)

Retrieving your client ID
-------------------------
Note: Android TVs use a slightly different system of client IDs plus client secrets, and the only way to retrieve EAC-3s is to root an NVIDIA Shield TV 2019, which is extremely complex and comes with its own issues, to get its client ID and secret, as none of the supported devices can have user certificates installed, and the NVIDIA Shield TV is the only one that can be rooted to do this.

To get a client ID, you must do a man-in-the-middle-attack or otherwise. On Android this involves getting Tidal to accept user certificates. This can be done in two ways:
1. Somehow modify the APK to add the certificate in yourself (difficult!)
2. Force it to target Android Marshmallow (6.0, API 23) as it is the last version that user certificates are allowed

Requirements
------------
* Python (3.6 or higher)
* requests
* mutagen (1.37 or higher)
* pycryptodomex
* ffmpeg-python (0.2.0 or higher)
* deezerapi (already included from [deemix](https://codeberg.org/RemixDev/deemix))


Installation
------------
The new more detailed Installation Guide has been moved to the Wiki: [https://github.com/Dniel97/RedSea/wiki/Installation-Guide](https://github.com/Dniel97/RedSea/wiki/Installation-Guide)

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
    -s, --skip              Pass this flag to skip track and continue when a track
                            does not meet the requested quality
    -f, --file              The URLs to download inside a .txt file with a single 
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

Usage:      `python redsea.py explore (atmos (albums|tracks) | 360)`

Example:    `python redsea.py explore atmos tracks`

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
* Artist album/video download (which downloads all albums/videos from a given artist)

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

`save_credits_txt`: Saves a `{track_format}.txt` file with the file containing all the credits of a specific song

`embed_credits`: Embeds all the credits tags inside a FLAC/MP4 file

`save_lyrics_lrc`: Saves synced lyrics as .lrc using the Deezer API (from [deemix](https://codeberg.org/RemixDev/deemix)) or musiXmatch

`embed_lyrics`: Embed the unsynced lyrics inside a FLAC/MP4 file

`lyrics_provider_order`: Defines the order (from left to right) you want to get the lyrics from

`genre_language`: Select the language of the genres from Deezer to `en-US, de, fr, ...` 

`artwork_size`: Downloads (artwork_size)x(artwork_size) album covers from iTunes, set it to `0` to disable iTunes cover

`resolution`: Which resolution you want to download the videos

### Album/track format

Format variables are `{title}`, `{artist}`, `{album}`, `{tracknumber}`, `{discnumber}`, `{date}`, `{quality}`, `{explicit}`.

* `{quality}` has a whitespace in front, so it will look like this " [Dolby Atmos]", " [360]" or " [M]" according to the downloaded quality

* `{explicit}` has a whitespace in front, so it will look like this " [E]"

`track_format`: How tracks are formatted. The relevant extension is appended to the end.

`album_format`: Base album directory - tracks and cover art are stored here. May have slashes in it, for instance {artist}/{album}.

`playlist_format`: How playlist tracks are formatted, same as track_format just with `{playlistnumber}` added

### Video format

Format variables are `{title}`, `{artist}`, `{tracknumber}`, `{discnumber}`, `{date}`, `{quality}`, `{explicit}`.

* `{quality}` has a whitespace in front, so it will look like this " [1080P]" according to the highest available resolution returned by the API

* `{explicit}` has a whitespace in front, so it will look like this " [E]"

`video_file_format`: How video filenames are formatted. The '.mp4' extension is appended to the end.

`video_folder_format`: The video directory - tmp files and cover art are stored here. May have slashes in it, for instance {artist}/{title}.
