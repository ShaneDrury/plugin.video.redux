import sys, xbmc, xbmcplugin, xbmcgui, xbmcaddon, json
from urllib import urlencode
from urllib2 import urlopen, HTTPError
from urlparse import parse_qs


API_URL = 'https://i.bbcredux.com'
formatMap = {'Original stream': 'ts',
             'Stripped stream': 'strip',
             'H264 large': 'h264_mp4_hi_v1.1',
             'H264 small': 'h264_mp4_lo_v1.0',
             'MP3': 'MP3_v1.0'}


def alert(message):
    xbmcgui.Dialog().ok('Error', message)


def login(username, password):
    try:
        data = json.loads(urlopen(url=API_URL + '/user/login?' + urlencode(
            {'username': username, 'password': password})).read())
        if data['success']: return data['token']
    except HTTPError:
        alert('Wrong username or password')
    sys.exit(-1)


def search_dialog():
    kb = xbmc.Keyboard('', 'Search for')
    kb.doModal()
    if not kb.isConfirmed(): return None;
    searchterm = kb.getText().strip()
    return searchterm


def main():
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = parse_qs(sys.argv[2][1:])
    mode = args.get('mode', None)

    addon = xbmcaddon.Addon()
    username = addon.getSetting('username')
    password = addon.getSetting('password')
    stream_format = addon.getSetting('format')

    if mode is None:
        token = login(username, password)
        try:
            data = json.loads(urlopen(API_URL + '/asset/search?' + urlencode(
                {'q': search_dialog(), 'titleonly': '1', 'token': token})).read())
        except HTTPError:
            alert('There was an error accessing Redux')
            sys.exit(-1)
        for item in data['results']['assets']:
            list_item = xbmcgui.ListItem(item['name'] + ' - ' + item['description'])
            d = {'key': item['key'],
                 'reference': item['reference'],
                 'token': token,
                 'mode': 'play'}
            xbmcplugin.addDirectoryItem(addon_handle,
                                        base_url + '?' + urlencode(d), list_item)
        xbmcplugin.endOfDirectory(addon_handle)

    elif mode[0] == 'play':
        reference = args.get('reference', None)[0]
        key = args.get('key', None)[0]
        xbmc.Player(xbmc.PLAYER_CORE_MPLAYER).play(
            API_URL + '/asset/media/' + reference + '/' + key + '/' + formatMap[
                stream_format] + '/file')

if __name__ == '__main__':
    main()
