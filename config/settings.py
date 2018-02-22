'''
Store your redsea download presets here

You may modify/add/remove as you wish. The only preset which must exist is "default"
and you may change the default as needed.
'''

from accounts import ACCOUNTS

PRESETS = {

    # Default settings only download LOSSLESS
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

    # This preset will allow only LOSSLESS and MQA files
    "mqa_enabled": {
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