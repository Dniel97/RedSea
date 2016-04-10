import tempfile

header_format = '#EXTINF:{duration},{artist[name]} - {title}\n'

def temp_path():
    _, path = tempfile.mkstemp(suffix='.m3u8', text=True)
    return path

def write_tracks(tracks, path):
    contents = '#EXTM3U\n'
    for t in tracks:
        contents += header_format.format(**t)
        contents += t['stream_url'] + '\n\n'
    with open(path, 'r+') as f:
        f.write(contents)