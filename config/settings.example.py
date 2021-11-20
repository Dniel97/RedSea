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
save_credits_txt: Saves a {track_format}.txt file with the file containing all the credits of a specific song
embed_credits: Embeds all the credits tags inside a FLAC/MP4 file
save_lyrics_lrc: Saves synced lyrics as .lrc using the official Tidal provider: musixmatch
embed_lyrics: Embed the unsynced lyrics inside a FLAC/MP4 file
genre_language: Select the language of the genres from Deezer to "en-US", "de", "fr", ...
artwork_size: Downloads (artwork_size)x(artwork_size) album covers from iTunes, set it to 0 to disable iTunes cover
resolution: Which resolution you want to download the videos

Format variables are {title}, {artist}, {album}, {tracknumber}, {discnumber}, {date}, {quality}, {explicit}.
quality: has a whitespace in front, so it will look like this " [Dolby Atmos]", " [360]" or " [M]" according to the downloaded quality
explicit: has a whitespace in front, so it will look like this " [E]"
track_format: How tracks are formatted. The relevant extension is appended to the end.
album_format: Base album directory - tracks and cover art are stored here. May have slashes in it, for instance {artist}/{album}.
playlist_format: How playlist tracks are formatted, same as track_format just with {playlistnumber} added

Format variables are {title}, {artist}, {tracknumber}, {discnumber}, {date}, {quality}, {explicit}.
quality has a whitespace in front, so it will look like this " [1080P]" according to the highest available resolution returned by the API
{explicit} has a whitespace in front, so it will look like this " [E]"
video_file_format: How video filenames are formatted. The '.mp4' extension is appended to the end.
video_folder_format: The video directory - tmp files and cover art are stored here. May have slashes in it, for instance {artist}/{title}.


=== Formats ===
MQA_FLAC_24: MQA Format / 24bit FLAC with high-frequency "folded" data
FLAC_16: 16bit FLAC
AAC_320: 320Kbps AAC
AAC_96: 96Kbps AAC

'''

# BRUTEFORCEREGION: Attempts to download the track/album with all available accounts if dl fails
BRUTEFORCEREGION = True

# Shows the Access JWT after every refresh and creation
SHOWAUTH = False

# The Desktop token
TOKEN = 'c7RLy4RJ3OCNeZki'      # MQA Token

# The mobile token which usually comes along with the authorization header
# MOBILE_TOKEN = "WAU9gXp3tHhK4Nns"    # MQA Token
MOBILE_TOKEN = "dN2N95wCyEBTllu4"  # Dolby Atmos AC-4 + MQA + FLAC + AAC

# The TV_TOKEN and the line below (TV_SECRET) are tied together, so un-/comment both.
TV_TOKEN = "7m7Ap0JC9j1cOM3n"  # FireTV Dolby Atmos E-AC-3 + MQA
TV_SECRET = "vRAdA108tlvkJpTsGZS8rGZ7xTlbJ0qaZ2K9saEzsgY="

# Web token for hidden web login (do not use!)
WEB_TOKEN = "CzET4vdadNUFQ5JU"

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
        "playlist_format": "{playlistnumber} - {title}",
        "album_format": "{albumartist} - {album}{quality}{explicit}",
        "video_folder_format": "{artist} - {title}{quality}",
        "video_file_format": "{title}",
        "convert_to_alac": False,
        "save_credits_txt": False,
        "embed_credits": True,
        "save_lyrics_lrc": True,
        "embed_lyrics": True,
        "genre_language": "en-US",
        "artwork_size": 3000,
        "uncompressed_artwork": True,
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
        "playlist_format": "{playlistnumber} - {title}",
        "album_format": "{albumartist} - {album}{quality}{explicit}",
        "video_folder_format": "{artist} - {title}{quality}",
        "video_file_format": "{title}",
        "convert_to_alac": True,
        "save_credits_txt": False,
        "embed_credits": True,
        "save_lyrics_lrc": True,
        "embed_lyrics": True,
        "genre_language": "en-US",
        "artwork_size": 3000,
        "uncompressed_artwork": True,
        "resolution": 1080,
        "MQA_FLAC_24": True,
        "FLAC_16": True,
        "AAC_320": True,
        "AAC_96": True
    },

    # This preset will download every song from playlist inside a playlist folder
    "playlist": {
        "keep_cover_jpg": False,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": path,
        "track_format": "{albumartist} - {title}",
        "playlist_format": "{playlistnumber} - {title}",
        "video_folder_format": "{artist} - {title}{quality}",
        "video_file_format": "{title}",
        "album_format": "",
        "convert_to_alac": False,
        "save_credits_txt": False,
        "embed_credits": True,
        "save_lyrics_lrc": True,
        "embed_lyrics": True,
        "genre_language": "en-US",
        "artwork_size": 3000,
        "uncompressed_artwork": False,
        "resolution": 1080,
        "MQA_FLAC_24": True,
        "FLAC_16": True,
        "AAC_320": False,
        "AAC_96": False
    },

    # This preset will only download FLAC 16
    "FLAC": {
        "keep_cover_jpg": True,
        "embed_album_art": True,
        "save_album_json": False,
        "tries": 5,
        "path": path,
        "track_format": "{tracknumber} - {title}",
        "playlist_format": "{playlistnumber} - {title}",
        "album_format": "{albumartist} - {album}{quality}{explicit}",
        "video_folder_format": "{artist} - {title}{quality}",
        "video_file_format": "{title}",
        "convert_to_alac": False,
        "save_credits_txt": False,
        "embed_credits": True,
        "save_lyrics_lrc": True,
        "embed_lyrics": True,
        "genre_language": "en-US",
        "artwork_size": 3000,
        "uncompressed_artwork": True,
        "resolution": 1080,
        "MQA_FLAC_24": False,
        "FLAC_16": True,
        "AAC_320": False,
        "AAC_96": False
    },
}
