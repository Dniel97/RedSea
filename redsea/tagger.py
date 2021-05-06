import unicodedata

from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4Cover
from mutagen.mp4 import MP4Tags
from mutagen.id3 import PictureType

# Needed for Windows tagging support
MP4Tags._padding = 0


def normalize_key(s):
    # Remove accents from a given string
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


class FeaturingFormat():
    '''
    Formatter for featuring artist tags
    '''

    def _format(self, featuredArtists, andStr):
        artists = ''
        if len(featuredArtists) == 1:
            artists = featuredArtists[0]
        elif len(featuredArtists) == 2:
            artists = featuredArtists[0] + ' {} '.format(andStr) + featuredArtists[1]
        else:
            for i in range(0, len(featuredArtists)):
                name = featuredArtists[i]
                artists += name
                if i < len(featuredArtists) - 1:
                    artists += ', '
                if i == len(featuredArtists) - 2:
                    artists += andStr + ' '
        return artists

    def get_artist_format(self, mainArtists):
        return self._format(mainArtists, '&')

    def get_feature_format(self, featuredArtists):
        return '(feat. {})'.format(self._format(featuredArtists, 'and'))


class Tagger(object):

    def __init__(self, format_options):
        self.fmtopts = format_options

    def tags(self, track_info, track_type, album_info=None, tagger=None):
        if tagger is None:
            tagger = {}
        title = track_info['title']
        if len(track_info['artists']) == 1:
            tagger['artist'] = track_info['artist']['name']
        else:
            self.featform = FeaturingFormat()
            mainArtists = []
            featuredArtists = []
            for artist in track_info['artists']:
                if artist['type'] == 'MAIN':
                    mainArtists.append(artist['name'])
                elif artist['type'] == 'FEATURED':
                    featuredArtists.append(artist['name'])
            if len(featuredArtists) > 0 and '(feat.' not in title:
                title += ' ' + self.featform.get_feature_format(
                    featuredArtists)
            tagger['artist'] = self.featform.get_artist_format(mainArtists)

        if album_info is not None:
            tagger['albumartist'] = album_info['artist']['name']
        tagger['tracknumber'] = str(track_info['trackNumber']).zfill(2)
        tagger['album'] = track_info['album']['title']
        if album_info is not None:
            # TODO: find a way to get numberOfTracks relative to the volume
            if track_type == 'm4a':
                tagger['tracknumber'] = str(track_info['trackNumber']).zfill(2) + '/' + str(
                    album_info['numberOfTracks'])
                tagger['discnumber'] = str(
                    track_info['volumeNumber']) + '/' + str(
                    album_info['numberOfVolumes'])
            if track_type == 'flac':
                tagger['discnumber'] = str(track_info['volumeNumber'])
                tagger['totaldiscs'] = str(album_info['numberOfVolumes'])
                tagger['tracknumber'] = str(track_info['trackNumber'])
                tagger['totaltracks'] = str(album_info['numberOfTracks'])
            else:
                tagger['discnumber'] = str(track_info['volumeNumber'])
            if album_info['releaseDate']:
                # TODO: less hacky way of getting the year?
                tagger['date'] = str(album_info['releaseDate'][:4])
            if album_info['upc'] and track_type == 'm4a':
                tagger['upc'] = album_info['upc'].encode()

        if track_info['version'] is not None and track_info['version'] != '':
            fmt = ' ({})'.format(track_info['version'])
            title += fmt

        tagger['title'] = title

        if track_info['copyright'] is not None:
            tagger['copyright'] = track_info['copyright']

        if track_info['isrc'] is not None:
            if track_type == 'm4a':
                tagger['isrc'] = track_info['isrc'].encode()
            elif track_type == 'flac':
                tagger['isrc'] = track_info['isrc']

        # Stupid library won't accept int so it is needed to cast it to a byte with hex value 01
        if track_info['explicit'] is not None:
            if track_type == 'm4a':
                tagger['explicit'] = b'\x01' if track_info['explicit'] else b'\x02'
            elif track_type == 'flac':
                tagger['ITUNESADVISORY'] = '1' if track_info['explicit'] else '2'

        # Set genre from Deezer
        if 'genre' in track_info:
            tagger['genre'] = track_info['genre']

        if 'replayGain' in track_info and 'peak' in track_info:
            if track_type == 'flac':
                tagger['REPLAYGAIN_TRACK_GAIN'] = str(track_info['replayGain'])
                tagger['REPLAYGAIN_TRACK_PEAK'] = str(track_info['peak'])

        if track_type is None:
            if track_info['audioModes'] == ['DOLBY_ATMOS']:
                tagger['quality'] = ' [Dolby Atmos]'
            elif track_info['audioModes'] == ['SONY_360RA']:
                tagger['quality'] = ' [360]'
            elif track_info['audioQuality'] == 'HI_RES':
                tagger['quality'] = ' [M]'
            else:
                tagger['quality'] = ''

            if 'explicit' in album_info:
                tagger['explicit'] = ' [E]' if album_info['explicit'] else ''

        return tagger

    def _meta_tag(self, tagger, track_info, album_info, track_type):
        self.tags(track_info, track_type, album_info, tagger)

    def tag_flac(self, file_path, track_info, album_info, lyrics, credits_dict=None, album_art_path=None):
        tagger = FLAC(file_path)

        self._meta_tag(tagger, track_info, album_info, 'flac')
        if self.fmtopts['embed_album_art'] and album_art_path is not None:
            pic = Picture()
            with open(album_art_path, 'rb') as f:
                pic.data = f.read()

            # Check if cover is smaller than 16MB
            if len(pic.data) < pic._MAX_SIZE:
                pic.type = PictureType.COVER_FRONT
                pic.mime = u'image/jpeg'
                tagger.add_picture(pic)
            else:
                print('\tCover file size is too large, only {0:.2f}MB are allowed.'.format(pic._MAX_SIZE / 1024 ** 2))
                print('\tSet "artwork_size" to a lower value in config/settings.py')

        # Set lyrics from Deezer
        if lyrics:
            tagger['lyrics'] = lyrics

        if credits_dict:
            for key, value in credits_dict.items():
                contributors = value.split(', ')
                for con in contributors:
                    tagger.tags.append((normalize_key(key), con))

        tagger.save(file_path)

    def tag_m4a(self, file_path, track_info, album_info, lyrics, credits_dict=None, album_art_path=None):
        tagger = EasyMP4(file_path)

        # Register ISRC, UPC, lyrics and explicit tags
        tagger.RegisterTextKey('isrc', '----:com.apple.itunes:ISRC')
        tagger.RegisterTextKey('upc', '----:com.apple.itunes:UPC')
        tagger.RegisterTextKey('explicit', 'rtng')
        tagger.RegisterTextKey('lyrics', '\xa9lyr')

        self._meta_tag(tagger, track_info, album_info, 'm4a')
        if self.fmtopts['embed_album_art'] and album_art_path is not None:
            pic = None
            with open(album_art_path, 'rb') as f:
                pic = MP4Cover(f.read())
            tagger.RegisterTextKey('covr', 'covr')
            tagger['covr'] = [pic]

        # Set lyrics from Deezer
        if lyrics:
            tagger['lyrics'] = lyrics

        if credits_dict:
            for key, value in credits_dict.items():
                contributors = value.split(', ')
                key = normalize_key(key)
                # Create a new freeform atom and set the contributors in bytes
                tagger.RegisterTextKey(key, '----:com.apple.itunes:' + key)
                tagger[key] = [con.encode() for con in contributors]

        tagger.save(file_path)
