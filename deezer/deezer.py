#!/usr/bin/env python3
import time

import requests
import re
import json

USER_AGENT_HEADER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                    "Chrome/79.0.3945.130 Safari/537.36"


class Deezer:
    def __init__(self, language='en'):
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        self.api_url = "http://www.deezer.com/ajax/gw-light.php"
        self.legacy_api_url = "https://api.deezer.com/"
        self.http_headers = {
            "User-Agent": USER_AGENT_HEADER,
            "Accept-Language": language
        }
        self.session = requests.Session()
        self.session.post("https://www.deezer.com/", headers=self.http_headers, verify=False)

    def get_token(self):
        token_data = self.gw_api_call('deezer.getUserData')
        return token_data["results"]["checkForm"]

    def gw_api_call(self, method, args=None):
        if args is None:
            args = {}
        try:
            result = self.session.post(
                self.api_url,
                params={
                    'api_version': "1.0",
                    'api_token': 'null' if method == 'deezer.getUserData' else self.get_token(),
                    'input': '3',
                    'method': method
                },
                timeout=30,
                json=args,
                headers=self.http_headers,
                verify=False
            )
            result_json = result.json()
        except:
            time.sleep(2)
            return self.gw_api_call(method, args)
        if len(result_json['error']):
            raise APIError(json.dumps(result_json['error']))
        return result.json()

    def api_call(self, method, args=None):
        if args is None:
            args = {}
        try:
            result = self.session.get(
                self.legacy_api_url + method,
                params=args,
                headers=self.http_headers,
                timeout=30,
                verify=False
            )
            result_json = result.json()
        except:
            time.sleep(2)
            return self.api_call(method, args)
        if 'error' in result_json.keys():
            if 'code' in result_json['error'] and result_json['error']['code'] == 4:
                time.sleep(5)
                return self.api_call(method, args)
            raise APIError(json.dumps(result_json['error']))
        return result_json

    def get_track_gw(self, sng_id):
        if int(sng_id) < 0:
            body = self.gw_api_call('song.getData', {'sng_id': sng_id})
        else:
            body = self.gw_api_call('deezer.pageTrack', {'sng_id': sng_id})
            if 'LYRICS' in body['results']:
                body['results']['DATA']['LYRICS'] = body['results']['LYRICS']
            body['results'] = body['results']['DATA']
        return body['results']

    def get_tracks_gw(self, ids):
        tracks_array = []
        body = self.gw_api_call('song.getListData', {'sng_ids': ids})
        errors = 0
        for i in range(len(ids)):
            if ids[i] != 0:
                tracks_array.append(body['results']['data'][i - errors])
            else:
                errors += 1
                tracks_array.append({
                    'SNG_ID': 0,
                    'SNG_TITLE': '',
                    'DURATION': 0,
                    'MD5_ORIGIN': 0,
                    'MEDIA_VERSION': 0,
                    'FILESIZE': 0,
                    'ALB_TITLE': "",
                    'ALB_PICTURE': "",
                    'ART_ID': 0,
                    'ART_NAME': ""
                })
        return tracks_array

    def get_album_gw(self, alb_id):
        return self.gw_api_call('album.getData', {'alb_id': alb_id})['results']

    def get_album_tracks_gw(self, alb_id):
        tracks_array = []
        body = self.gw_api_call('song.getListByAlbum', {'alb_id': alb_id, 'nb': -1})
        for track in body['results']['data']:
            _track = track
            _track['position'] = body['results']['data'].index(track)
            tracks_array.append(_track)
        return tracks_array

    def get_artist_gw(self, art_id):
        return self.gw_api_call('deezer.pageArtist', {'art_id': art_id})

    def search_gw(self, term, type, start, nb=20):
        return \
            self.gw_api_call('search.music',
                             {"query": clean_search_query(term), "filter": "ALL", "output": type, "start": start, "nb": nb})[
                'results']

    def get_lyrics_gw(self, sng_id):
        return self.gw_api_call('song.getLyrics', {'sng_id': sng_id})["results"]

    def get_track(self, sng_id):
        return self.api_call('track/' + str(sng_id))

    def get_track_by_ISRC(self, isrc):
        return self.api_call('track/isrc:' + isrc)

    def get_album(self, album_id):
        return self.api_call('album/' + str(album_id))

    def get_album_by_UPC(self, upc):
        return self.api_call('album/upc:' + str(upc))

    def get_album_tracks(self, album_id):
        return self.api_call('album/' + str(album_id) + '/tracks', {'limit': -1})

    def get_artist(self, artist_id):
        return self.api_call('artist/' + str(artist_id))

    def get_artist_albums(self, artist_id):
        return self.api_call('artist/' + str(artist_id) + '/albums', {'limit': -1})

    def search(self, term, search_type, limit=30, index=0):
        return self.api_call('search/' + search_type, {'q': clean_search_query(term), 'limit': limit, 'index': index})

    def get_track_from_metadata(self, artist, track, album):
        artist = artist.replace("–", "-").replace("’", "'")
        track = track.replace("–", "-").replace("’", "'")
        album = album.replace("–", "-").replace("’", "'")

        resp = self.search(f'artist:"{artist}" track:"{track}" album:"{album}"', "track", 1)
        if len(resp['data']) > 0:
            return resp['data'][0]['id']
        resp = self.search(f'artist:"{artist}" track:"{track}"', "track", 1)
        if len(resp['data']) > 0:
            return resp['data'][0]['id']
        if "(" in track and ")" in track and track.find("(") < track.find(")"):
            resp = self.search(f'artist:"{artist}" track:"{track[:track.find("(")]}"', "track", 1)
            if len(resp['data']) > 0:
                return resp['data'][0]['id']
        elif " - " in track:
            resp = self.search(f'artist:"{artist}" track:"{track[:track.find(" - ")]}"', "track", 1)
            if len(resp['data']) > 0:
                return resp['data'][0]['id']
        else:
            return 0
        return 0


def clean_search_query(term):
    term = str(term)
    term = re.sub(r' feat[\.]? ', " ", term)
    term = re.sub(r' ft[\.]? ', " ", term)
    term = re.sub(r'\(feat[\.]? ', " ", term)
    term = re.sub(r'\(ft[\.]? ', " ", term)
    term = term.replace('&', " ").replace('–', "-").replace('—', "-")
    return term


class APIError(Exception):
    pass
