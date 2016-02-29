import json
import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from urllib import urlencode
from urllib2 import urlopen, HTTPError
from urlparse import parse_qsl

API_URL = 'https://i.bbcredux.com/{action}?{params}'
formatMap = {'Original stream': 'ts',
             'Stripped stream': 'strip',
             'H264 large': 'h264_mp4_hi_v1.1',
             'H264 small': 'h264_mp4_lo_v1.0',
             'MP3': 'MP3_v1.0'}


def alert(message):
    xbmcgui.Dialog().ok('Error', message)


def get_new_token():
    addon = xbmcaddon.Addon()
    settings = get_addon_settings()
    username = settings['username']
    password = settings['password']
    try:
        url = API_URL.format(
            action='/user/login',
            params=urlencode({'username': username, 'password': password})
        )
        data = json.loads(urlopen(url).read())
        if data['success']:
            token = data['token']
            addon.setSetting('token', token)
            return token
    except HTTPError:
        alert('Wrong username or password')
        sys.exit(-1)


def get_token():
    settings = get_addon_settings()
    settings_token = settings.get('token')
    if settings_token is not '':
        return settings_token
    else:
        return get_new_token()


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
        'mode': 'display_search_results'
    }
    arguments.update(extra_args)
    return arguments


def get_addon_settings():
    addon = xbmcaddon.Addon()
    return {
        'username': addon.getSetting('username'),
        'password': addon.getSetting('password'),
        'token': addon.getSetting('token'),
        'format': addon.getSetting('format'),
        'num_results': int(addon.getSetting('results_per_page'))
    }


def add_dir_item(handle, addon_url, item, folder=False, **data):
    xbmcplugin.addDirectoryItem(
        handle,
        addon_url + '?' + urlencode(data),
        item,
        isFolder=folder
    )


def search(query, offset, token, num_results=10):
    url = API_URL.format(
        action='asset/search',
        params=urlencode({
            'q': query,
            'titleonly': '1',
            'token': token,
            'offset': offset,
            'limit': num_results,
            'repeats': 0
        })
    )
    return json.loads(urlopen(url).read())


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


def should_display_next_results(response, offset, num_results=10):
    return response['total_returned'] + num_results * offset < response['total_found']


def play_video(args):
    settings = get_addon_settings()
    stream_format = settings['format']
    reference = args.get('reference')
    key = args.get('key')
    action = 'asset/media/{reference}/{key}/{stream_format}/file'.format(
        reference=reference,
        key=key,
        stream_format=formatMap[stream_format]
    )
    media_url = API_URL.format(action=action, params='')
    xbmc.Player(xbmc.PLAYER_CORE_MPLAYER).play(media_url)


def display_search_results(args):
    addon_handle = args['addon_handle']
    addon_url = args['addon_url']
    settings = get_addon_settings()
    results_per_page = settings['num_results']
    query = args.get('query')
    if query is None:
        query = search_dialog()
    if query is None:
        sys.exit(0)
    token = get_token()

    def search_callable():
        return search(query, args.get('offset'), token, results_per_page)
    try:
        response = search_callable()
    except HTTPError, e:
        if e.code == 403:
            token = get_new_token()
            response = search_callable()
        else:
            alert('There was an error accessing Redux')
            sys.exit(-1)
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
        if should_display_next_results(response, args['offset'], results_per_page):
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

mode_mapping = {
    'play': play_video,
    'display_search_results': display_search_results
}


def main():
    args = get_arguments()
    mode = args['mode']
    mode_mapping[mode](args)


if __name__ == '__main__':
    main()
