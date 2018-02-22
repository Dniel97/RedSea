def _format(featuredArtists, andStr):
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


def get_artist_format(mainArtists):
    return _format(mainArtists, '&')


def get_feature_format(featuredArtists):
    return '(feat. {})'.format(_format(featuredArtists, 'and'))
