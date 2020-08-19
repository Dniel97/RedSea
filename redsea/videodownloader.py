import requests
import re
import os
import ffmpeg
import shutil
from mutagen.easymp4 import EasyMP4
from mutagen.mp4 import MP4Cover
from mutagen.mp4 import MP4Tags

# Needed for Windows tagging support
MP4Tags._padding = 0


def parse_master_playlist(masterurl):
    content = str(requests.get(masterurl).content)
    pattern = re.compile(r"(?<=RESOLUTION=).+?(?=\\n)")
    resolution_list = pattern.findall(content)
    pattern = re.compile(r"(?<=http).+?(?=\\n)")
    plist = pattern.findall(content)
    playlists = {}
    for i in range(len(plist)):
        playlists[resolution_list[i]] = "http" + plist[i]

    return playlists


def parse_playlist(url):
    content = requests.get(url).content
    pattern = re.compile(r"(?<=http).+?(?=\\n)")
    plist = pattern.findall(str(content))
    urllist = []
    for item in plist:
        urllist.append("http" + item)

    return urllist


def download_file(urllist, part, filename):
    if os.path.isfile(filename):
        # print('\tFile {} already exists, skipping.'.format(filename))
        return None

    r = requests.get(urllist[part], stream=True)
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


def print_video_info(track_info):
    line = '\tTitle: {0}\n\tArtist: {1}\n\tType: {2}\n\tResolution: {3}'.format(track_info['title'], track_info['artist']['name'],
                                                             track_info['type'], track_info['resolution'])
    try:
        print(line)
    except UnicodeEncodeError:
        line = line.encode('ascii', 'replace').decode('ascii')
        print(line)
    print('\t----')


def download_video_artwork(image_id, where):
    url = 'https://resources.tidal.com/images/{0}/{1}x{2}.jpg'.format(
        image_id.replace('-', '/'), 1280, 720)

    r = requests.get(url, stream=True)

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


def tag_video(file_path, track_info, album_art_path):
    tagger = EasyMP4(file_path)
    tagger.RegisterTextKey('explicit', 'rtng')

    tagger['title'] = track_info['title']
    tagger['artist'] = track_info['artist']['name']
    tagger['tracknumber'] = str(track_info['trackNumber']).zfill(2) + '/' + str(track_info['volumeNumber'])

    if track_info['explicit'] is not None:
        tagger['explicit'] = b'\x01' if track_info['explicit'] else b'\x02'

    pic = None
    with open(album_art_path, 'rb') as f:
        pic = MP4Cover(f.read())
    tagger.RegisterTextKey('covr', 'covr')
    tagger['covr'] = [pic]

    tagger.save(file_path)


def download_stream(folder_path, url, resolution, video_info):
    path = os.path.join(folder_path, video_info['artist']['name'] + ' - ' + video_info['title'])
    tmp_folder = os.path.join(path, 'tmp')
    playlists = parse_master_playlist(url)
    urllist = []

    for playlist in playlists:
        if resolution >= int(playlist.split('x')[1]):
            video_info['resolution'] = resolution
            urllist = parse_playlist(playlists[playlist])
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
                print('Deleting partially downloaded file ' + str(filename))
                os.remove(filename)
            raise
        #   print("\tDownload progress: {0:.0f}%".format(percent), end='\r')
    print("\n\tDownload succeeded!")

    file_path = os.path.join(path, video_info['title'] + '.mp4')

    (
        ffmpeg
        .input(filelist_loc, format='concat', safe=0)
        .output(file_path, vcodec='copy', acodec='copy', c='copy', loglevel='warning')
        .overwrite_output()
        .run()
    )
    print('\tConcatenation succeeded!')
    shutil.rmtree(tmp_folder)

    print('\tDownloading album art ...')
    aa_location = os.path.join(path, 'Cover.jpg')
    if not os.path.isfile(aa_location):
        if not download_video_artwork(video_info['imageId'], aa_location):
            aa_location = None

    print('\tTagging video file...')
    tag_video(file_path, video_info, aa_location)
