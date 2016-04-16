
import urllib.parse

import requests

class DASH(object):
    def __init__(self, dash_playlist_url):
        path = dash_playlist_url[:dash_playlist_url.rindex('/')] + '/'
        self.base_url = path
        self.dash_playlist = requests.get(dash_playlist_url).text
    
    def parse_available_streams(self):
        lines = self.dash_playlist.split('\n')
        opts = []
        for line in lines:
            if line.startswith('#EXT-X-STREAM-INF:'):
                pd = line[line.index(':') + 1:].split(',')
                opt = {}
                for p in pd:
                    k, v = p.split('=')
                    opt[k] = v
                opts.append(opt)
            elif len(opts) > 0 and '__URL' not in opts[-1:][0]:
                opt = opts[-1:][0]
                opt['__URL'] = line
        return opts
    
    def get_media(self, playlist):
        pl = requests.get(self.base_url + playlist).text
        lines = pl.split('\n')
        return [line for line in lines if line.strip().endswith('.ts')]