import sys, xbmc, xbmcplugin, xbmcgui, xbmcaddon, json
from urllib import urlencode
from urllib2 import urlopen, HTTPError
from urlparse import parse_qsl

API_URL = 'https://i.bbcredux.com'
formatMap = {'Original stream': 'ts',
             'Stripped stream': 'strip',
             'H264 large': 'h264_mp4_hi_v1.1',
             'H264 small': 'h264_mp4_lo_v1.0',
             'MP3': 'MP3_v1.0'}


def alert(message):
    xbmcgui.Dialog().ok('Error', message)


def get_token(username, password):
    try:
        data = json.loads(urlopen(url=API_URL + '/user/login?' + urlencode(
            {'username': username, 'password': password})).read())
        if data['success']:
            return data['token']
    except HTTPError:
        alert('Wrong username or password')
        sys.exit(-1)


def search_dialog():
    kb = xbmc.Keyboard('', 'Search for')
    kb.doModal()
    if not kb.isConfirmed():
        return None
    searchterm = kb.getText().strip()
    return searchterm


def get_arguments():
    extra_args = dict(parse_qsl(sys.argv[2][1:]))
    offset = extra_args.get('offset')
    if offset:
        extra_args['offset'] = int(offset)
    else:
        extra_args['offset'] = 0
    arguments = {
        'addon_url': sys.argv[0],
        'addon_handle': int(sys.argv[1]),
    }
    arguments.update(extra_args)
    return arguments


def get_addon_settings():
    addon = xbmcaddon.Addon()
    return {
        'username': addon.getSetting('username'),
        'password': addon.getSetting('password'),
        'format': addon.getSetting('format')
    }


def add_dir_item(handle, addon_url, item, folder=False, **data):
    xbmcplugin.addDirectoryItem(
        handle,
        addon_url + '?' + urlencode(data),
        item,
        isFolder=folder
    )


def search(query, offset, token):
    try:
        data = json.loads(urlopen(API_URL + '/asset/search?' + urlencode(
            {
                'q': query,
                'titleonly': '1',
                'token': token,
                'offset': offset
            }
        )).read())
    except HTTPError:
        alert('There was an error accessing Redux')
        sys.exit(-1)
    return data


def parse_results(results):
    return [
        {
            'name': item['name'],
            'description': item['description'],
            'key': item['key'],
            'reference': item['reference'],
        }
        for item in results['assets']
    ]


def should_display_next_results(response, offset):
    return response['total_returned'] + 10 * offset < response['total_found']


def play_video(args):
    settings = get_addon_settings()
    stream_format = settings['format']
    reference = args.get('reference')
    key = args.get('key')
    xbmc.Player(xbmc.PLAYER_CORE_MPLAYER).play(
        API_URL + '/asset/media/' + reference + '/' + key + '/' + formatMap[
            stream_format] + '/file')


def display_search_results(args):
    addon_handle = args['addon_handle']
    addon_url = args['addon_url']
    settings = get_addon_settings()
    token = args.get(
        'token',
        get_token(settings['username'], settings['password'])
    )

    query = args.get('query')
    if query is None:
        query = search_dialog()
    if query is None:
        sys.exit(0)

    response = search(query, args.get('offset'), token)
    results = response.get('results')
    if results:
        for item in parse_results(results):
            title = "{name} - {description}".format(
                name=item['name'],
                description=item['description']
            )
            list_item = xbmcgui.ListItem(title)
            add_dir_item(
                addon_handle, addon_url, list_item, folder=True,
                key=item['key'],
                reference=item['reference'],
                token=token,
                mode='play'
            )
        if should_display_next_results(response, args['offset']):
            next_page = xbmcgui.ListItem('Next Page')
            add_dir_item(
                addon_handle,
                addon_url,
                next_page,
                folder=True,
                offset=args['offset'] + 1,
                query=query,
                token=token
            )
    xbmcplugin.endOfDirectory(addon_handle)


def main():
    args = get_arguments()
    if args.get('mode') == 'play':
        play_video(args)
    else:
        display_search_results(args)


if __name__ == '__main__':
    main()
