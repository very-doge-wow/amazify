import time

from flask import abort, Flask, redirect, render_template, request, session, url_for
import json
import logging
import os
import requests

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

# Client info for Spotify
SPOTIFY_CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
SPOTIFY_CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']

# Client info for Amazon Music
AMAZON_TOKEN = os.environ['AMAZON_TOKEN']
AMAZON_X_API_KEY = os.environ['AMAZON_X_API_KEY']

# Spotify API endpoints
SPOTIFY_BASE_ENDPOINT = 'https://api.spotify.com/v1'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_SEARCH_ENDPOINT = f'{SPOTIFY_BASE_ENDPOINT}/search'
SPOTIFY_ME_ENDPOINT = f'{SPOTIFY_BASE_ENDPOINT}/me'

# Amazon API endpoints
AMAZON_BASE_ENDPOINT = 'https://api.music.amazon.dev/v1'
AMAZON_TOKEN_URL = 'https://api.amazon.com/auth/o2/token'
AMAZON_ME_ENDPOINT = f'{AMAZON_BASE_ENDPOINT}/me/'

# Startup
app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/auth/spotify')
def auth_spotify():
    """Get user authorization and set access token."""
    # Request authorization from user
    payload = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'grant_type': 'client_credentials',
    }

    res = requests.post(SPOTIFY_TOKEN_URL, auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET), data=payload)
    res_data = res.json()

    access_token = res_data.get('access_token')

    if not access_token or res.status_code != 200:
        app.logger.error(
            'Failed to get access token: %s, %s',
            res_data.get('error'),
            res_data.get('error_description'),
        )
        abort(400)
    else:
        session['spotify_access_token'] = access_token
        return redirect(url_for('index'))


def _query_artist_spotify(artist=None):
    """Make request for data on `artist`."""

    if artist is None:
        return artist

    payload = {'q': artist, 'type': 'artist', 'limit': '50'}
    headers = {
        'Authorization': f"Bearer {session.get('spotify_access_token')}",
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    return requests.get(SPOTIFY_SEARCH_ENDPOINT, params=payload, headers=headers)


@app.route('/search', methods=['GET', 'POST'])
def search_spotify():
    """Simple example search for an artist."""

    if request.method == 'POST':

        artist = request.form.get('artist')

        if artist:
            res = _query_artist_spotify(artist)
            res_data = res.json()

            if res_data.get('error') or res.status_code != 200:
                app.logger.error(
                    'Failed to get results for %s: %s, %s',
                    artist,
                    res_data.get('error'),
                    res_data.get('error_description'),
                )
                abort(400)
            else:
                return json.dumps(res_data)

        else:
            app.logger.error('No artist value provided.')
            abort(400)

    else:
        return render_template('search.html')


@app.route('/amazon/playlists', methods=['GET'])
def playlists_amazon():
    """Simple example search for playlists."""

    # first get user_id
    if not session.get('amazon_user'):
        headers = {
            "Authorization": f"Bearer {AMAZON_TOKEN}",
            "x-api-key": AMAZON_X_API_KEY,
            "Content-Type": "application/json",
        }

        response = requests.get(AMAZON_ME_ENDPOINT, headers=headers)
        session['amazon_user'] = json.loads(response.text).get('data').get('user').get('id')

    # avoid rate-limiting
    time.sleep(1)

    url = f"{AMAZON_BASE_ENDPOINT}/users/{session['amazon_user']}/playlists"
    headers = {
        "Authorization": f"Bearer {AMAZON_TOKEN}",
        "x-api-key": AMAZON_X_API_KEY,
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    edges = json.loads(response.text)['data']['user']['playlists']['edges']
    lists = []
    for e in edges:
        list_entry = {
            'id': e['node']['id'],
            'trackCount': e['node']['trackCount'],
            'visibility': e['node']['visibility'],
            'duration': e['node']['duration'],
            'url': e['node']['url'],
            'title': e['node']['title'],
            'image': e['node']['images'][0],
        }
        lists.append(list_entry)
    return render_template(template_name_or_list='playlists.html', content=lists)


def _get_paginated_track_list(playlist: dict, playlist_id: str, cursor: str = None):
    # get the playlist from amazon API (including tracks)
    url = f"{AMAZON_BASE_ENDPOINT}/playlists/{playlist_id}/tracks"
    if cursor:
        url += f"?cursor={cursor}"
    headers = {
        "Authorization": f"Bearer {AMAZON_TOKEN}",
        "x-api-key": AMAZON_X_API_KEY,
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    edges = json.loads(response.text)['data']['playlist']['tracks']['edges']
    if not playlist:
        playlist = json.loads(response.text)['data']['playlist']
    else:
        playlist['tracks']['edges'] += edges

    if len(edges) == 50:
        # pagination
        cursor = edges[len(edges) - 1]['cursor']
        # avoid rate-limiting
        time.sleep(0.5)
        playlist = _get_paginated_track_list(playlist=playlist, playlist_id=playlist_id, cursor=cursor)

    return playlist


def _create_spotify_playlist(name: str):
    """Creates a spotify playlist with the given name if it doesn't exist yet."""
    # get current user's id
    headers = {
        'Authorization': f"Bearer {session.get('spotify_access_token')}",
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    resp = requests.get(SPOTIFY_ME_ENDPOINT, headers=headers)
    data = json.loads(resp.text)
    print(data)


@app.route('/amazon/migrate', methods=['POST'])
def migrate_playlist():
    playlist_id = request.form.get('submitValue')
    session['progress'] = 0
    # get the playlist from amazon API (including tracks)
    original_playlist = _get_paginated_track_list(playlist={}, playlist_id=playlist_id, cursor=None)
    # create new playlist at spotify if not exists
    _create_spotify_playlist(name=original_playlist['title'])
    return render_template(template_name_or_list='migrate.html', content=original_playlist)


@app.route('/api/progress', methods=['GET'])
def api_progress():
    progress = session.get('progress')
    if not progress:
        progress = 0
    return {'progress': progress}
