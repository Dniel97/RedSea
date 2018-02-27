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
HI_RES: MQA Format / 24bit FLAC with high-frequency "folded" data
LOSSLESS: 16bit FLAC
HIGH: 320Kbps AAC
LOW: 96Kbps AAC

'''

from accounts import ACCOUNTS

PRESETS = {

    # Default settings / only download LOSSLESS
    "default": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "HI_RES": False,
        "LOSSLESS": True,
        "HIGH": False,
        "LOW": False
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
        "HI_RES": True,
        "LOSSLESS": True,
        "HIGH": True,
        "LOW": True
    },

    # This preset will allow LOSSLESS and MQA files only
    "mqa_lossless": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "HI_RES": True,
        "LOSSLESS": True,
        "HIGH": False,
        "LOW": False
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
        "HI_RES": True,
        "LOSSLESS": False,
        "HIGH": False,
        "LOW": False
    },
}