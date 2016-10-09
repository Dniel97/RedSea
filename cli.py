import argparse
import collections

# https://stackoverflow.com/a/18394648/975018
def rec_update(orig_dict, new_dict):
    for key, val in new_dict.items():
        if isinstance(val, collections.Mapping):
            tmp = rec_update(orig_dict.get(key, { }), val)
            orig_dict[key] = tmp
        elif isinstance(val, list):
            orig_dict[key] = (orig_dict[key] + val)
        else:
            orig_dict[key] = new_dict[key]
    return orig_dict

def get_args():
    #
    # argparse setup
    #
    parser = argparse.ArgumentParser(description='A music downloader for Tidal.')

    parser.add_argument('-o', 
        default='rs_config.json',
        metavar='filename', 
        help='The path to a config file. If not supplied, uses `rs_config.json\' in the current directory.')

    parser.add_argument('-p',
        metavar='option',
        action='append',
        help='Any options specified here in `key=value\' form will override the config file -- e.g. `tidal.quality=LOW\' to force the quality to low. This can be used multiple times.')

    parser.add_argument('media', nargs='+', help='The media to download. See readme for media download format.')

    return parser.parse_args()

def parse_media_option(mo):
    opts = []
    for m in mo:
        ci = m.index(':')
        hi = m.find('#')
        hi = len(m) if hi == -1 else hi
        o = {
            'type': m[:ci],
            'id': m[ci + 1:hi],
            'index': m[hi + 1:]
        }
        opts.append(o)
    return opts

def parse_config_overrides(l):
    if not len(l):
        return

    kstr = {}
    for i in l:
        key, value = i.split('=')
        if '.' not in key:
            kstr[key] = value
        else:
            keys = key.split('.')
            keys.reverse()
            current = kstr
            while len(keys) > 0:
                skey = keys.pop()
                if skey not in current:
                    if len(keys) == 0:
                        current[skey] = value
                    else:
                        current[skey] = {}
                        current = current[skey]
                else:
                    current = current[skey]
    return kstr




