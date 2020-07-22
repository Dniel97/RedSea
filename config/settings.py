'''
Store your redsea download presets here

You may modify/add/remove as you wish. The only preset which must exist is "default"
and you may change the default as needed.

=== Stock Presets ===
(use these with the -p flag)
default:            FLAC 44.1k / 16bit only
best_available:     Download the highest available quality (MQA > FLAC > 320 > 96)
mqa_flac:           Accept both MQA 24bit and FLAC 16bit
MQA:                Only allow FLAC 44.1k / 24bit (includes 'folded' 96k content)
FLAC:               FLAC 44.1k / 16bit only
320:                AAC ~320 VBR only
96:                 AAC ~96 VBR only

=== Options ===
keep_cover_jpg: save the cover art to the album directory
embed_album_art: embed the album art into each audio file
save_album_json: save the album metadata as a json file
tries: number of attempts before giving up on the download
path: where to store downloaded files
track_format: naming mask for tracks
album_format: naming mask for abum directories

=== Formats ===
MQA_FLAC_24: MQA Format / 24bit FLAC with high-frequency "folded" data
FLAC_16: 16bit FLAC
AAC_320: 320Kbps AAC
AAC_96: 96Kbps AAC

'''

# BRUTEFORCEREGION: Attempts to download the track/album with all available accounts if dl fails
BRUTEFORCEREGION = True

# This usually comes along with the authorization header
TOKEN = "4ywnjRfroi84hz7i"

# AUTHHEADER will look like "Bearer abcd......."
AUTHHEADER = "Bearer "

path = "./downloads/"

PRESETS = {

    # Default settings / only download FLAC_16
    "default": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": path,
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": False,
        "FLAC_16": False,
        "AAC_320": False,
        "AAC_96": True
    },

    # This will download the highest available quality including MQA
    "best_available": {
        "keep_cover_jpg": False,
        "embed_album_art": True,
        "save_album_json": False,
        "aggressive_remix_filtering": True,
        "skip_singles_when_possible": True,
        "skip_360ra": True,
        "tries": 5,
        "path": path,
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": True,
        "FLAC_16": True,
        "AAC_320": True,
        "AAC_96": True
    },

    # This preset will allow FLAC_16 and MQA files only
    "mqa_flac": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": True,
        "FLAC_16": True,
        "AAC_320": False,
        "AAC_96": False
    },

    # This preset will only download MQA
    "MQA": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": True,
        "FLAC_16": False,
        "AAC_320": False,
        "AAC_96": False
    },


    # This preset will only download FLAC 16
    "FLAC": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": False,
        "FLAC_16": True,
        "AAC_320": False,
        "AAC_96": False
    },


    # This preset will only download AAC ~320
    "320": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": False,
        "FLAC_16": False,
        "AAC_320": True,
        "AAC_96": False
    },


    # This preset will only download AAC ~96
    "96": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": "./",
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}",
        "MQA_FLAC_24": False,
        "FLAC_16": False,
        "AAC_320": False,
        "AAC_96": True
    },
}
