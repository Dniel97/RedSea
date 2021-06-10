import os
import re
import shutil
import unicodedata

import ffmpeg
import requests
from mutagen.easymp4 import EasyMP4
from mutagen.mp4 import MP4Cover
from mutagen.mp4 import MP4Tags

# Needed for Windows tagging support
MP4Tags._padding = 0


def normalize_key(s):
    # Remove accents from a given string
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def parse_master_playlist(masterurl: str):
    content = str(requests.get(masterurl, verify=False).content)
    pattern = re.compile(r"(?<=RESOLUTION=)[0-9]+x[0-9]+")
    resolution_list = pattern.findall(content)
    pattern = re.compile(r"(?<=http).+?(?=\\n)")
    plist = pattern.findall(content)
    playlists = [{'height': int(resolution_list[i].split('x')[1]),
                  'url': "http" + plist[i]} for i in range(len(plist))]

    return sorted(playlists, key=lambda k: k['height'], reverse=True)


def parse_playlist(url: str):
    content = requests.get(url, verify=False).content
    pattern = re.compile(r"(?<=http).+?(?=\\n)")
    plist = pattern.findall(str(content))
    urllist = []
    for item in plist:
        urllist.append("http" + item)

    return urllist


def download_file(urllist: list, part: int, filename: str):
    if os.path.isfile(filename):
        # print('\tFile {} already exists, skipping.'.format(filename))
        return None

    r = requests.get(urllist[part], stream=True, verify=False)
    try:
        total = int(r.headers['content-length'])
    except KeyError:
        return False

    with open(filename, 'wb') as f:
        cc = 0
        for chunk in r.iter_content(chunk_size=1024):
            cc += 1024
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    f.close()


def print_video_info(track_info: dict):
    line = '\tTitle: {0}\n\tArtist: {1}\n\tType: {2}\n\tResolution: {3}'.format(track_info['title'],
                                                                                track_info['artist']['name'],
                                                                                track_info['type'],
                                                                                track_info['resolution'])
    try:
        print(line)
    except UnicodeEncodeError:
        line = line.encode('ascii', 'replace').decode('ascii')
        print(line)
    print('\t----')


def download_video_artwork(image_id: str, where: str):
    url = 'https://resources.tidal.com/images/{0}/{1}x{2}.jpg'.format(
        image_id.replace('-', '/'), 1280, 720)

    r = requests.get(url, stream=True, verify=False)

    try:
        total = int(r.headers['content-length'])
    except KeyError:
        return False
    with open(where, 'wb') as f:
        cc = 0
        for chunk in r.iter_content(chunk_size=1024):
            cc += 1024
            print(
                "\tDownload progress: {0:.0f}%".format((cc / total) * 100),
                end='\r')
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
        print()
    return True


def tags(video_info: dict, tagger=None, ftype=None):
    if tagger is None:
        tagger = {'id': video_info['id'], 'quality': ' [' + video_info['quality'][4:] + ']'}

    tagger['title'] = video_info['title']
    tagger['artist'] = video_info['artist']['name']
    if ftype:
        tagger['tracknumber'] = str(video_info['trackNumber']).zfill(2) + '/' + str(video_info['volumeNumber'])
    else:
        tagger['tracknumber'] = str(video_info['trackNumber']).zfill(2)
        tagger['discnumber'] = str(video_info['volumeNumber'])

    if 'explicit' in video_info:
        if ftype:
            tagger['explicit'] = b'\x01' if video_info['explicit'] else b'\x02'
        else:
            tagger['explicit'] = ' [E]' if video_info['explicit'] else ''

    if video_info['releaseDate']:
        # TODO: less hacky way of getting the year?
        tagger['date'] = str(video_info['releaseDate'][:4])

    return tagger


def tag_video(file_path: str, track_info: dict, credits_dict: dict, album_art_path: str):
    tagger = EasyMP4(file_path)
    tagger.RegisterTextKey('explicit', 'rtng')

    # Add tags to the EasyMP4 tagger
    tags(track_info, tagger, ftype='mp4')

    pic = None
    with open(album_art_path, 'rb') as f:
        pic = MP4Cover(f.read())
    tagger.RegisterTextKey('covr', 'covr')
    tagger['covr'] = [pic]

    if credits_dict:
        for key, value in credits_dict.items():
            key = normalize_key(key)
            # Create a new freeform atom and set the contributors in bytes
            tagger.RegisterTextKey(key, '----:com.apple.itunes:' + key)
            tagger[key] = [bytes(con, encoding='utf-8') for con in value]

    tagger.save(file_path)


def download_stream(folder_path: str, file_name: str, url: str, resolution: int, video_info: dict, credits_dict: dict):
    tmp_folder = os.path.join(folder_path, 'tmp')
    playlists = parse_master_playlist(url)
    urllist = []

    for playlist in playlists:
        if resolution >= playlist['height']:
            video_info['resolution'] = playlist['height']
            urllist = parse_playlist(playlist['url'])
            break

    if len(urllist) <= 0:
        print('Error: list of URLs is empty!')
        return False

    print_video_info(video_info)

    if not os.path.isdir(tmp_folder):
        os.makedirs(tmp_folder)

    filelist_loc = os.path.join(tmp_folder, 'filelist.txt')

    if os.path.exists(filelist_loc):
        os.remove(filelist_loc)

    filename = ""
    for i in range(len(urllist)):
        try:
            filename = os.path.join(tmp_folder, str(i).zfill(3) + '.ts')
            download_file(urllist, i, filename)
            with open(filelist_loc, 'a') as f:
                f.write("file '" + str(i).zfill(3) + '.ts' + "'\n")
            percent = i / (len(urllist) - 1) * 100
            print("\tDownload progress: {0:.0f}%".format(percent), end='\r')
            # print(percent)
            
        # Delete partially downloaded file on keyboard interrupt
        except KeyboardInterrupt:
            if os.path.isfile(filename):
                print('\tDeleting partially downloaded file ' + str(filename))
                os.remove(filename)
            raise
        #   print("\tDownload progress: {0:.0f}%".format(percent), end='\r')
    print("\n\tDownload succeeded!")

    file_path = os.path.join(folder_path, file_name + '.mp4')

    (
        ffmpeg
            .input(filelist_loc, format='concat', safe=0)
            .output(file_path, vcodec='copy', acodec='copy', loglevel='warning')
            .overwrite_output()
            .run()
    )
    print('\tConcatenation succeeded!')
    shutil.rmtree(tmp_folder)

    print('\tDownloading album art ...')
    aa_location = os.path.join(folder_path, 'Cover.jpg')
    if not os.path.isfile(aa_location):
        if not download_video_artwork(video_info['imageId'], aa_location):
            aa_location = None

    print('\tTagging video file...')
    tag_video(file_path, video_info, credits_dict, aa_location)
