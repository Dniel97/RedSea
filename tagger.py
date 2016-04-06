from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4Cover
from mutagen.easymp4 import EasyMP4
from mutagen.id3 import PictureType

class Tagger(object):

    def __init__(self, format_options):
        self.fmtopts = format_options

    def _meta_tag(self, tagger, track_info, album_info):
        tagger['title'] = track_info['title']
        tagger['artist'] = track_info['artist']['name']

        tagger['album'] = track_info['album']['title']
        # TODO: find a way to get numberOfTracks relative to the volume
        tagger['tracknumber'] = str(track_info['trackNumber'])# + '/' + str(track_info['album_info']['numberOfTracks'])
        tagger['discnumber'] = str(track_info['volumeNumber']) + '/' + str(album_info['numberOfVolumes'])

        # TODO: less hacky way of getting the year?
        tagger['date'] = str(album_info['releaseDate'][:4])

        if track_info['version'] is not None:
            fmt = ' ({})'.format(track_info['version'])
            tagger['title'][0] += fmt

    def tag_flac(self, file_path, track_info, album_info=None, album_art_path=None):
        tagger = FLAC(file_path)

        self._meta_tag(tagger, track_info, album_info)
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

    def tag_m4a(self, file_path, track_info, album_info=None, album_art_path=None):
        tagger = EasyMP4(file_path)

        self._meta_tag(tagger, track_info, album_info)
        if self.fmtopts['embed_album_art'] and album_art_path is not None:
    	    pic = None
    	    with open(album_art_path, 'rb') as f:
    	        pic = MP4Cover(f.read())
    	    tagger.RegisterTextKey('covr', 'covr')
    	    tagger['covr'] = [pic]
        tagger.save(file_path)