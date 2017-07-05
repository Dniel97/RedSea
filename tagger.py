from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4Cover
from mutagen.easymp4 import EasyMP4
from mutagen.id3 import PictureType

import FeaturingFormat

class Tagger(object):

    def __init__(self, format_options):
        self.fmtopts = format_options

    def tags(self, track_info, album_info=None, tagger={}):
        title = track_info['title']
        if len(track_info['artists']) == 1:
            tagger['artist'] = track_info['artist']['name']
        else:
            mainArtists = []
            featuredArtists = []
            for artist in track_info['artists']:
                if artist['type'] == 'MAIN':
                    mainArtists.append(artist['name'])
                elif artist['type'] == 'FEATURED':
                    featuredArtists.append(artist['name'])
            if (len(featuredArtists) > 0 and '(feat.' not in title):
                title += ' ' + FeaturingFormat.get_feature_format(featuredArtists)
            tagger['artist'] = FeaturingFormat.get_artist_format(mainArtists)

        tagger['album'] = track_info['album']['title']
        tagger['tracknumber'] = str(track_info['trackNumber'])
        if album_info is not None:
	        # TODO: find a way to get numberOfTracks relative to the volume
	        # + '/' + str(track_info['album_info']['numberOfTracks'])
	        tagger['discnumber'] = str(track_info['volumeNumber']) + '/' + str(album_info['numberOfVolumes'])

	        # TODO: less hacky way of getting the year?
	        tagger['date'] = str(album_info['releaseDate'][:4])

        if track_info['version'] is not None and track_info['version'] != '':
            fmt = ' ({})'.format(track_info['version'])
            title += fmt
        tagger['title'] = title
        return tagger
        
    def _meta_tag(self, tagger, track_info, album_info):               
        self.tags(track_info, album_info, tagger)
        
    def tag_flac(self, file_path, track_info, album_info, album_art_path=None):
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

    def tag_m4a(self, file_path, track_info, album_info, album_art_path=None):
        tagger = EasyMP4(file_path)

        self._meta_tag(tagger, track_info, album_info)
        if self.fmtopts['embed_album_art'] and album_art_path is not None:
    	    pic = None
    	    with open(album_art_path, 'rb') as f:
    	        pic = MP4Cover(f.read())
    	    tagger.RegisterTextKey('covr', 'covr')
    	    tagger['covr'] = [pic]
        tagger.save(file_path)
