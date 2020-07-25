from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4Cover
from mutagen.mp4 import MP4Tags
from mutagen.id3 import PictureType

# Needed for Windows tagging support
MP4Tags._padding = 0


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

    def tags(self, track_info, track_type, album_info=None, tagger={}):
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
                tagger['tracknumber'] = str(track_info['trackNumber']).zfill(2) + '/' + str(album_info['numberOfTracks'])
            if track_type == 'flac':
                tagger['discnumber'] = str(track_info['volumeNumber'])
                tagger['totaldiscs'] = str(album_info['numberOfVolumes'])
            else:
                tagger['discnumber'] = str(
                    track_info['volumeNumber']) + '/' + str(
                    album_info['numberOfVolumes'])
            if album_info['releaseDate']:
                # TODO: less hacky way of getting the year?
                tagger['date'] = str(album_info['releaseDate'][:4])
            if album_info['upc']:
                tagger['upc'] = bytes(album_info['upc'], encoding="ascii")

        if track_info['version'] is not None and track_info['version'] != '':
            fmt = ' ({})'.format(track_info['version'])
            title += fmt
        tagger['title'] = title
        if track_info['copyright'] is not None:
            tagger['copyright'] = track_info['copyright']
        if track_info['isrc'] is not None:
            tagger['isrc'] = bytes(track_info['isrc'], encoding="ascii")
        # Stupid library won't accept int so it is needed to cast it to a byte with hex value 01
        if track_info['explicit'] is not None:
            if track_info['explicit'] is True:
                tagger['explicit'] = b'\x01'
            else:
                tagger['explicit'] = b'\x02'
        return tagger

    def _meta_tag(self, tagger, track_info, album_info, track_type):
        self.tags(track_info, track_type, album_info, tagger)

    def tag_flac(self, file_path, track_info, album_info, album_art_path=None):
        tagger = FLAC(file_path)

        self._meta_tag(tagger, track_info, album_info, 'flac')
        if self.fmtopts['embed_album_art'] and album_art_path is not None:
            pic = Picture()
            with open(album_art_path, 'rb') as f:
                pic.data = f.read()

            pic.type = PictureType.COVER_FRONT
            pic.mime = u"image/jpeg"
            # TODO: detect this automatically?
            pic.width = 1280
            pic.height = 1280
            pic.depth = 24
            tagger.add_picture(pic)
        tagger.save(file_path)

    def tag_m4a(self, file_path, track_info, album_info, album_art_path=None):
            tagger = EasyMP4(file_path)

            # Register ISRC, UPC and explicit tags
            tagger.RegisterTextKey('isrc', '----:com.apple.itunes:ISRC')
            tagger.RegisterTextKey('upc', '----:com.apple.itunes:UPC')
            tagger.RegisterTextKey('explicit', 'rtng')

            self._meta_tag(tagger, track_info, album_info, 'm4a')
            if self.fmtopts['embed_album_art'] and album_art_path is not None:
                pic = None
                with open(album_art_path, 'rb') as f:
                    pic = MP4Cover(f.read())
                tagger.RegisterTextKey('covr', 'covr')
                tagger['covr'] = [pic]
            tagger.save(file_path)
