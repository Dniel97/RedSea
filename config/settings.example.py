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
keep_cover_jpg: Whether to keep the cover.jpg file in the album directory
embed_album_art: Whether to embed album art or not into the file.
save_album_json: save the album metadata as a json file
tries: How many times to attempt to get a valid stream URL.
path: Base download directory
convert_to_alac: Converts a .flac file to an ALAC .m4a file (requires ffmpeg)
lyrics: Enable lyrics tagging and synced lyrics as .lrc download using the Deezer API (from https://codeberg.org/RemixDev/deemix)
Format variables are {title}, {artist}, {album}, {tracknumber}, {discnumber}, {date}, {quality}, {explicit}
{quality} has a whitespaces in front, so it will look like this " [Dolby Atmos]", " [360]" or " [M]" according to the downloaded quality
{explicit} has a whitespaces in front, so it will look like this " [E]"
track_format: How tracks are formatted. The relevant extension is appended to the end.
album_format: Base album directory - tracks and cover art are stored here. May have slashes in it, for instance {artist}/{album}.


=== Formats ===
MQA_FLAC_24: MQA Format / 24bit FLAC with high-frequency "folded" data
FLAC_16: 16bit FLAC
AAC_320: 320Kbps AAC
AAC_96: 96Kbps AAC

'''

# BRUTEFORCEREGION: Attempts to download the track/album with all available accounts if dl fails
BRUTEFORCEREGION = True

# Allows switching the country
COUNTRYCODE = "US"

# Shows the Access JWT after every refresh and creation
SHOWAUTH = True

# This usually comes along with the authorization header
# TOKEN = "WAU9gXp3tHhK4Nns"    # MQA Token
TOKEN = "dN2N95wCyEBTllu4"  # Dolby Atmos AC-4 Token

# The TV_TOKEN and the line below (TV_SECRET) are tied together, so un-/comment both.
TV_TOKEN = "LXujKdmnc6QtydvY"  # FireTV
TV_SECRET = "7iM9rMsPlM2xDY5AiToS7XgVVnG28bjsMhJlhzjCcSA="

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
        "album_format": "{albumartist} - {album}{quality}{explicit}",
        "convert_to_alac": False,
        "lyrics": True,
        "lyrics_provider_order": ["Deezer", "musiXmatch"],
        "artwork_size": 3000,
        "resolution": 1080,
        "MQA_FLAC_24": True,
        "FLAC_16": True,
        "AAC_320": False,
        "AAC_96": False
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
        "album_format": "{albumartist} - {album}{quality}{explicit}",
        "convert_to_alac": True,
        "lyrics": True,
        "lyrics_provider_order": ["Deezer", "musiXmatch"],
        "artwork_size": 3000,
        "resolution": 1080,
        "MQA_FLAC_24": True,
        "FLAC_16": True,
        "AAC_320": True,
        "AAC_96": True
    },

    # This preset will only download FLAC 16
    "FLAC": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": path,
        "track_format": "{tracknumber} - {title}",
        "album_format": "{albumartist} - {album}{quality}{explicit}",
        "convert_to_alac": False,
        "lyrics": True,
        "lyrics_provider_order": ["Deezer", "musiXmatch"],
        "artwork_size": 3000,
        "resolution": 1080,
        "MQA_FLAC_24": False,
        "FLAC_16": True,
        "AAC_320": False,
        "AAC_96": False
    },
}
