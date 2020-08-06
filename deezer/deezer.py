#!/usr/bin/env python3
import binascii
import time

import requests
from Cryptodome.Cipher import Blowfish, AES
from Cryptodome.Hash import MD5
from Cryptodome.Util.Padding import pad
import re
import json

USER_AGENT_HEADER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                    "Chrome/79.0.3945.130 Safari/537.36"


class Deezer:
    def __init__(self):
        self.api_url = "http://www.deezer.com/ajax/gw-light.php"
        self.legacy_api_url = "https://api.deezer.com/"
        self.http_headers = {
            "User-Agent": USER_AGENT_HEADER
        }
        self.album_pictures_host = "https://e-cdns-images.dzcdn.net/images/cover/"
        self.artist_pictures_host = "https://e-cdns-images.dzcdn.net/images/artist/"
        self.email = ""
        self.user = {}
        self.family = False
        self.childs = []
        self.selectedAccount = 0
        self.session = requests.Session()
        self.logged_in = False
        self.session.post("https://www.deezer.com/", headers=self.http_headers)
        self.guest_sid = self.session.cookies.get('sid')

    def get_token(self):
        token_data = self.gw_api_call('deezer.getUserData')
        return token_data["results"]["checkForm"]

    def get_track_filesizes(self, sng_id):
        try:
            site = requests.post(
                "https://api.deezer.com/1.0/gateway.php",
                params={
                    'api_key': "4VCYIJUCDLOUELGD1V8WBVYBNVDYOXEWSLLZDONGBBDFVXTZJRXPR29JRLQFO6ZE",
                    'sid': self.guest_sid,
                    'input': '3',
                    'output': '3',
                    'method': 'song_getData'
                },
                timeout=30,
                json={'sng_id': sng_id},
                headers=self.http_headers
            )
        except:
            time.sleep(2)
            return self.get_track_filesizes(sng_id)
        response = site.json()["results"]
        filesizes = {}
        for key, value in response.items():
            if key.startswith("FILESIZE_"):
                filesizes[key] = value
        return filesizes

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
                headers=self.http_headers
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
                timeout=30
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

    def login(self, email, password, re_captcha_token, child=0):
        check_form_login = self.gw_api_call("deezer.getUserData")
        login = self.session.post(
            "https://www.deezer.com/ajax/action.php",
            data={
                'type': 'login',
                'mail': email,
                'password': password,
                'checkFormLogin': check_form_login['results']['checkFormLogin'],
                'reCaptchaToken': re_captcha_token
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', **self.http_headers}
        )
        if 'success' not in login.text:
            self.logged_in = False
            return False
        user_data = self.gw_api_call("deezer.getUserData")
        self.family = user_data["results"]["USER"]["MULTI_ACCOUNT"]["ENABLED"]
        if self.family:
            self.childs = self.get_child_accounts_gw()
            if len(self.childs)-1 >= child:
                self.user = {
                    'id': self.childs[child]["USER_ID"],
                    'name': self.childs[child]["BLOG_NAME"],
                    'picture': self.childs[child]["USER_PICTURE"] if "USER_PICTURE" in self.childs[child] else ""
                }
                self.selectedAccount = child
            else:
                self.user = {
                    'id': user_data["results"]["USER"]["USER_ID"],
                    'name': user_data["results"]["USER"]["BLOG_NAME"],
                    'picture': user_data["results"]["USER"]["USER_PICTURE"] if "USER_PICTURE" in user_data["results"][
                        "USER"] else ""
                }
                self.selectedAccount = 0
        else:
            self.user = {
                'id': user_data["results"]["USER"]["USER_ID"],
                'name': user_data["results"]["USER"]["BLOG_NAME"],
                'picture': user_data["results"]["USER"]["USER_PICTURE"] if "USER_PICTURE" in user_data["results"][
                    "USER"] else ""
            }
        self.email = email
        self.logged_in = True
        return True

    def login_via_arl(self, arl, child=0):
        arl = arl.strip()
        cookie_obj = requests.cookies.create_cookie(
            domain='.deezer.com',
            name='arl',
            value=arl,
            path="/",
            rest={'HttpOnly': True}
        )
        self.session.cookies.set_cookie(cookie_obj)
        self.session.cookies.clear(".deezer.com", "/", "sid")
        user_data = self.gw_api_call("deezer.getUserData")
        if user_data["results"]["USER"]["USER_ID"] == 0:
            self.logged_in = False
            return 0
        self.family = user_data["results"]["USER"]["MULTI_ACCOUNT"]["ENABLED"]
        if self.family:
            self.childs = self.get_child_accounts_gw()
            if len(self.childs)-1 >= child:
                self.user = {
                    'id': self.childs[child]["USER_ID"],
                    'name': self.childs[child]["BLOG_NAME"],
                    'picture': self.childs[child]["USER_PICTURE"] if "USER_PICTURE" in self.childs[child] else ""
                }
                self.selectedAccount = child
            else:
                self.user = {
                    'id': user_data["results"]["USER"]["USER_ID"],
                    'name': user_data["results"]["USER"]["BLOG_NAME"],
                    'picture': user_data["results"]["USER"]["USER_PICTURE"] if "USER_PICTURE" in user_data["results"][
                        "USER"] else ""
                }
                self.selectedAccount = 0
        else:
            self.user = {
                'id': user_data["results"]["USER"]["USER_ID"],
                'name': user_data["results"]["USER"]["BLOG_NAME"],
                'picture': user_data["results"]["USER"]["USER_PICTURE"] if "USER_PICTURE" in user_data["results"][
                    "USER"] else ""
            }
        self.logged_in = True
        return 1

    def change_account(self, child):
        if len(self.childs)-1 >= child:
            self.user = {
                'id': self.childs[child]["USER_ID"],
                'name': self.childs[child]["BLOG_NAME"],
                'picture': self.childs[child]["USER_PICTURE"] if "USER_PICTURE" in self.childs[child] else ""
            }
            self.selectedAccount = child
        return (self.user, self.selectedAccount)

    def get_child_accounts_gw(self):
        return self.gw_api_call('deezer.getChildAccounts')['results']

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

    def get_playlist_gw(self, playlist_id):
        return self.gw_api_call('deezer.pagePlaylist', {'playlist_id': playlist_id, 'lang': 'en'})

    def get_playlist_tracks_gw(self, playlist_id):
        tracks_array = []
        body = self.gw_api_call('playlist.getSongs', {'playlist_id': playlist_id, 'nb': -1})
        for track in body['results']['data']:
            track['position'] = body['results']['data'].index(track)
            tracks_array.append(track)
        return tracks_array

    def get_artist_toptracks_gw(self, art_id):
        tracks_array = []
        body = self.gw_api_call('artist.getTopTrack', {'art_id': art_id, 'nb': 100})
        for track in body['results']['data']:
            track['position'] = body['results']['data'].index(track)
            tracks_array.append(track)
        return tracks_array

    def get_artist_discography_gw(self, art_id, nb=10):
        start = 0
        releases = []
        RELEASE_TYPE = ["single", "album", "compile", "ep"]
        result = {'all': []}
        while True:
            response = self.gw_api_call('album.getDiscography', {'art_id': art_id, "discography_mode":"all", 'nb': nb, 'nb_songs': 0, 'start': start})
            releases += response['results']['data']
            start += nb
            if start > response['results']['total']:
                break
        for release in releases:
            obj = {
                'id': release['ALB_ID'],
                'title': release['ALB_TITLE'],
                'link': f"https://www.deezer.com/album/{release['ALB_ID']}",
                'cover': f"https://api.deezer.com/album/{release['ALB_ID']}/image",
                'cover_small': f"https://cdns-images.dzcdn.net/images/cover/{release['ALB_PICTURE']}/56x56-000000-80-0-0.jpg",
                'cover_medium': f"https://cdns-images.dzcdn.net/images/cover/{release['ALB_PICTURE']}/250x250-000000-80-0-0.jpg",
                'cover_big': f"https://cdns-images.dzcdn.net/images/cover/{release['ALB_PICTURE']}/500x500-000000-80-0-0.jpg",
                'cover_xl': f"https://cdns-images.dzcdn.net/images/cover/{release['ALB_PICTURE']}/1000x1000-000000-80-0-0.jpg",
                'genre_id': release['GENRE_ID'],
                'fans': release['RANK'],
                'release_date': release['PHYSICAL_RELEASE_DATE'],
                'record_type': RELEASE_TYPE[int(release['TYPE'])],
                'tracklist': f"https://api.deezer.com/album/{release['ALB_ID']}/tracks",
                'explicit_lyrics': int(release['EXPLICIT_LYRICS']) > 0,
                'type': release['__TYPE__'],
                'nb_song': release['NUMBER_TRACK'],
                'nb_disk': release['NUMBER_DISK']
            }
            if (release['ART_ID'] == art_id or release['ART_ID'] != art_id and release['ROLE_ID'] == 0) and release['ARTISTS_ALBUMS_IS_OFFICIAL']:
                if not obj['record_type'] in result:
                    result[obj['record_type']] = []
                result[obj['record_type']].append(obj)
                result['all'].append(obj)
            else:
                if release['ROLE_ID'] == 5:
                    if not 'featured' in result:
                        result['featured'] = []
                    result['featured'].append(obj)
                elif release['ROLE_ID'] == 0:
                    if not 'more' in result:
                        result['more'] = []
                    result['more'].append(obj)
        return result

    def search_main_gw(self, term):
        term = term
        results = self.gw_api_call('deezer.pageSearch',
                                   {"query": clean_search_query(term), "start": 0, "nb": 10, "suggest": True, "artist_suggest": True,
                                    "top_tracks": True})['results']
        order = []
        for x in results['ORDER']:
            if x in ['TOP_RESULT', 'TRACK', 'ALBUM', 'ARTIST', 'PLAYLIST']:
                order.append(x)
        if 'TOP_RESULT' in results and len(results['TOP_RESULT']):
            orig_top_result = results['TOP_RESULT'][0]
            top_result = {}
            top_result['type'] = orig_top_result['__TYPE__']
            if top_result['type'] == 'artist':
                top_result['id'] = orig_top_result['ART_ID']
                top_result['picture'] = 'https://e-cdns-images.dzcdn.net/images/artist/' + orig_top_result['ART_PICTURE']
                top_result['title'] = orig_top_result['ART_NAME']
                top_result['nb_fan'] = orig_top_result['NB_FAN']
            elif top_result['type'] == 'album':
                top_result['id'] = orig_top_result['ALB_ID']
                top_result['picture'] = 'https://e-cdns-images.dzcdn.net/images/cover/' + orig_top_result['ALB_PICTURE']
                top_result['title'] = orig_top_result['ALB_TITLE']
                top_result['artist'] = orig_top_result['ART_NAME']
                top_result['nb_song'] = orig_top_result['NUMBER_TRACK']
            elif top_result['type'] == 'playlist':
                top_result['id'] = orig_top_result['PLAYLIST_ID']
                top_result['picture'] = 'https://e-cdns-images.dzcdn.net/images/' + orig_top_result['PICTURE_TYPE'] + '/' + orig_top_result['PLAYLIST_PICTURE']
                top_result['title'] = orig_top_result['TITLE']
                top_result['artist'] = orig_top_result['PARENT_USERNAME']
                top_result['nb_song'] = orig_top_result['NB_SONG']
            else:
                top_result['id'] = "0"
                top_result['picture'] = 'https://e-cdns-images.dzcdn.net/images/cover'
            top_result['picture'] += '/156x156-000000-80-0-0.jpg'
            top_result['link'] = 'https://deezer.com/'+top_result['type']+'/'+str(top_result['id'])
            results['TOP_RESULT'][0] = top_result
        results['ORDER'] = order
        return results

    def search_gw(self, term, type, start, nb=20):
        return \
            self.gw_api_call('search.music',
                             {"query": clean_search_query(term), "filter": "ALL", "output": type, "start": start, "nb": nb})[
                'results']

    def get_lyrics_gw(self, sng_id):
        return self.gw_api_call('song.getLyrics', {'sng_id': sng_id})["results"]

    def get_user_playlists_gw(self, user_id):
        data = self.gw_api_call('deezer.pageProfile', {'user_id': user_id, 'tab': 'playlists', 'nb': -1})['results']['TAB']['playlists']['data']
        result = []
        for playlist in data:
            item = {
                'id': playlist['PLAYLIST_ID'],
                'title': playlist['TITLE'],
                'nb_tracks': playlist['NB_SONG'],
                'link': 'https://www.deezer.com/playlist/'+str(playlist['PLAYLIST_ID']),
                'picture': 'https://api.deezer.com/playlist/'+str(playlist['PLAYLIST_ID'])+'/image',
                'picture_small': 'https://e-cdns-images.dzcdn.net/images/'+playlist['PICTURE_TYPE']+'/'+playlist['PLAYLIST_PICTURE']+'/56x56-000000-80-0-0.jpg',
                'picture_medium': 'https://e-cdns-images.dzcdn.net/images/'+playlist['PICTURE_TYPE']+'/'+playlist['PLAYLIST_PICTURE']+'/250x250-000000-80-0-0.jpg',
                'picture_big': 'https://e-cdns-images.dzcdn.net/images/'+playlist['PICTURE_TYPE']+'/'+playlist['PLAYLIST_PICTURE']+'/500x500-000000-80-0-0.jpg',
                'picture_xl': 'https://e-cdns-images.dzcdn.net/images/'+playlist['PICTURE_TYPE']+'/'+playlist['PLAYLIST_PICTURE']+'/1000x1000-000000-80-0-0.jpg',
                'tracklist': 'https://api.deezer.com/playlist/'+str(playlist['PLAYLIST_ID'])+'/tracks',
                'creator': {
                    'id': playlist['PARENT_USER_ID'],
                    'name': playlist['PARENT_USERNAME'] if 'PARENT_USERNAME' in playlist else self.user['name']
                },
                'type': 'playlist'
            }
            result.append(item)
        return result

    def get_user_albums_gw(self, user_id):
        data = self.gw_api_call('deezer.pageProfile', {'user_id': user_id, 'tab': 'albums', 'nb': -1})['results']['TAB']['albums']['data']
        result = []
        for album in data:
            item = {
                'id': album['ALB_ID'],
                'title': album['ALB_TITLE'],
                'link': 'https://www.deezer.com/album/'+str(album['ALB_ID']),
                'cover': 'https://api.deezer.com/album/'+str(album['ALB_ID'])+'/image',
                'cover_small': 'https://e-cdns-images.dzcdn.net/images/cover/'+album['ALB_PICTURE']+'/56x56-000000-80-0-0.jpg',
                'cover_medium': 'https://e-cdns-images.dzcdn.net/images/cover/'+album['ALB_PICTURE']+'/250x250-000000-80-0-0.jpg',
                'cover_big': 'https://e-cdns-images.dzcdn.net/images/cover/'+album['ALB_PICTURE']+'/500x500-000000-80-0-0.jpg',
                'cover_xl': 'https://e-cdns-images.dzcdn.net/images/cover/'+album['ALB_PICTURE']+'/1000x1000-000000-80-0-0.jpg',
                'tracklist': 'https://api.deezer.com/album/'+str(album['ALB_ID'])+'/tracks',
                'explicit_lyrics': album['EXPLICIT_ALBUM_CONTENT']['EXPLICIT_LYRICS_STATUS'] > 0,
                'artist': {
                    'id': album['ART_ID'],
                    'name': album['ART_NAME'],
                    'picture': 'https://api.deezer.com/artist/'+str(album['ART_ID'])+'image',
                    'tracklist': 'https://api.deezer.com/artist/'+str(album['ART_ID'])+'/top?limit=50'
                },
                'type': 'album'
            }
            result.append(item)
        return result

    def get_user_artists_gw(self, user_id):
        data = self.gw_api_call('deezer.pageProfile', {'user_id': user_id, 'tab': 'artists', 'nb': -1})['results']['TAB']['artists']['data']
        result = []
        for artist in data:
            item = {
                'id': artist['ART_ID'],
                'name': artist['ART_NAME'],
                'link': 'https://www.deezer.com/artist/'+str(artist['ART_ID']),
                'picture': 'https://api.deezer.com/artist/'+str(artist['ART_ID'])+'/image',
                'picture_small': 'https://e-cdns-images.dzcdn.net/images/artist/'+str(artist['ART_ID'])+'/56x56-000000-80-0-0.jpg',
                'picture_medium': 'https://e-cdns-images.dzcdn.net/images/artist/'+str(artist['ART_ID'])+'/250x250-000000-80-0-0.jpg',
                'picture_big': 'https://e-cdns-images.dzcdn.net/images/artist/'+str(artist['ART_ID'])+'/500x500-000000-80-0-0.jpg',
                'picture_xl': 'https://e-cdns-images.dzcdn.net/images/artist/'+str(artist['ART_ID'])+'/1000x1000-000000-80-0-0.jpg',
                'nb_fan': artist['NB_FAN'],
                'tracklist': 'https://api.deezer.com/artist/'+str(artist['ART_ID'])+'/top?limit=50',
                'type': 'artist'
            }
            result.append(item)
        return result

    def get_user_tracks_gw(self, user_id):
        data = self.gw_api_call('deezer.pageProfile', {'user_id': user_id, 'tab': 'loved', 'nb': -1})['results']['TAB']['loved']['data']
        result = []
        for track in data:
            item = {
                'id': track['SNG_ID'],
				'title': track['SNG_TITLE'],
				'link': 'https://www.deezer.com/track/'+str(track['SNG_ID']),
				'duration': track['DURATION'],
				'rank': track['RANK_SNG'],
				'explicit_lyrics': int(track['EXPLICIT_LYRICS']) > 0,
				'explicit_content_lyrics': track['EXPLICIT_TRACK_CONTENT']['EXPLICIT_COVER_STATUS'],
				'explicit_content_cover': track['EXPLICIT_TRACK_CONTENT']['EXPLICIT_LYRICS_STATUS'],
				'time_add': track['DATE_ADD'],
				'album': {
						'id': track['ALB_ID'],
						'title': track['ALB_TITLE'],
						'cover': 'https://api.deezer.com/album/'+str(track['ALB_ID'])+'/image',
						'cover_small': 'https://e-cdns-images.dzcdn.net/images/cover/'+str(track['ALB_PICTURE'])+'/56x56-000000-80-0-0.jpg',
						'cover_medium': 'https://e-cdns-images.dzcdn.net/images/cover/'+str(track['ALB_PICTURE'])+'/250x250-000000-80-0-0.jpg',
						'cover_big': 'https://e-cdns-images.dzcdn.net/images/cover/'+str(track['ALB_PICTURE'])+'/500x500-000000-80-0-0.jpg',
						'cover_xl': 'https://e-cdns-images.dzcdn.net/images/cover/'+str(track['ALB_PICTURE'])+'/1000x1000-000000-80-0-0.jpg',
						'tracklist': 'https://api.deezer.com/album/'+str(track['ALB_ID'])+'/tracks',
						'type': 'album'
				},
				'artist': {
						'id': track['ART_ID'],
						'name': track['ART_NAME'],
						'picture': 'https://api.deezer.com/artist/'+str(track['ART_ID'])+'/image',
						'picture_small': 'https://e-cdns-images.dzcdn.net/images/artist/'+str(track['ART_PICTURE'])+'/56x56-000000-80-0-0.jpg',
						'picture_medium': 'https://e-cdns-images.dzcdn.net/images/artist/'+str(track['ART_PICTURE'])+'/250x250-000000-80-0-0.jpg',
						'picture_big': 'https://e-cdns-images.dzcdn.net/images/artist/'+str(track['ART_PICTURE'])+'/500x500-000000-80-0-0.jpg',
						'picture_xl': 'https://e-cdns-images.dzcdn.net/images/artist/'+str(track['ART_PICTURE'])+'/1000x1000-000000-80-0-0.jpg',
						'tracklist': 'https://api.deezer.com/artist/'+str(track['ART_ID'])+'/top?limit=50',
						'type': 'artist'
				},
				'type': 'track'
            }
            result.append(item)
        return result

    def get_user_playlists(self, user_id):
        return self.api_call('user/' + str(user_id) + '/playlists', {'limit': -1})

    def get_user_albums(self, user_id):
        return self.api_call('user/' + str(user_id) + '/albums', {'limit': -1})

    def get_user_artists(self, user_id):
        return self.api_call('user/' + str(user_id) + '/artists', {'limit': -1})

    def get_user_tracks(self, user_id):
        return self.api_call('user/' + str(user_id) + '/tracks', {'limit': -1})

    def get_track(self, sng_id):
        return self.api_call('track/' + str(sng_id))

    def get_track_by_ISRC(self, isrc):
        return self.api_call('track/isrc:' + isrc)

    def get_charts_countries(self):
        temp = self.get_user_playlists('637006841')['data']
        result = sorted(temp, key=lambda k: k['title'])
        if not result[0]['title'].startswith('Top'):
            result = result[1:]
        return result

    def get_charts(self, limit=30):
        return self.api_call('chart', {'limit': limit})

    def get_playlist(self, playlist_id):
        return self.api_call('playlist/' + str(playlist_id))

    def get_playlist_tracks(self, playlist_id):
        return self.api_call('playlist/' + str(playlist_id) + '/tracks', {'limit': -1})

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

    def decrypt_track(self, track_id, input, output):
        response = open(input, 'rb')
        outfile = open(output, 'wb')
        blowfish_key = str.encode(self._get_blowfish_key(str(track_id)))
        i = 0
        while True:
            chunk = response.read(2048)
            if not chunk:
                break
            if (i % 3) == 0 and len(chunk) == 2048:
                chunk = Blowfish.new(blowfish_key, Blowfish.MODE_CBC, b"\x00\x01\x02\x03\x04\x05\x06\x07").decrypt(
                    chunk)
            outfile.write(chunk)
            i += 1

    def stream_track(self, track_id, url, stream):
        try:
            request = requests.get(url, headers=self.http_headers, stream=True, timeout=30)
        except:
            time.sleep(2)
            return self.stream_track(track_id, url, stream)
        request.raise_for_status()
        blowfish_key = str.encode(self._get_blowfish_key(str(track_id)))
        i = 0
        for chunk in request.iter_content(2048):
            if (i % 3) == 0 and len(chunk) == 2048:
                chunk = Blowfish.new(blowfish_key, Blowfish.MODE_CBC, b"\x00\x01\x02\x03\x04\x05\x06\x07").decrypt(
                    chunk)
            stream.write(chunk)
            i += 1

    def _md5(self, data):
        h = MD5.new()
        h.update(str.encode(data) if isinstance(data, str) else data)
        return h.hexdigest()

    def _get_blowfish_key(self, trackId):
        SECRET = 'g4el58wc' + '0zvf9na1'
        idMd5 = self._md5(trackId)
        bfKey = ""
        for i in range(16):
            bfKey += chr(ord(idMd5[i]) ^ ord(idMd5[i + 16]) ^ ord(SECRET[i]))
        return bfKey

    def get_track_stream_url(self, sng_id, md5, media_version, format):
        urlPart = b'\xa4'.join(
            [str.encode(md5), str.encode(str(format)), str.encode(str(sng_id)), str.encode(str(media_version))])
        md5val = self._md5(urlPart)
        step2 = str.encode(md5val) + b'\xa4' + urlPart + b'\xa4'
        step2 = pad(step2, 16)
        urlPart = binascii.hexlify(AES.new(b'jo6aey6haid2Teih', AES.MODE_ECB).encrypt(step2))
        return "https://e-cdns-proxy-" + md5[0] + ".dzcdn.net/mobile/1/" + urlPart.decode("utf-8")

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
