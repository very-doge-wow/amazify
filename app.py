import base64
import threading
import time

from flask import abort, Flask, redirect, render_template, request, session, url_for, make_response
import json
import logging
import requests

import settings
from util import get_paginated_track_list, generate_random_string, query_artist_spotify, create_spotify_playlist, add_tracks_to_spotify_playlist
from settings import *

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

# Startup
app = Flask(__name__)
app.secret_key = "fakekey"


@app.route('/auth/spotify')
def auth_spotify():
    state = generate_random_string(16)
    scope = '%20'.join(SPOTIFY_API_SCOPES)
    response = make_response(redirect(
        f'{SPOTIFY_AUTH_URL}?' +
        f'response_type=code&client_id={SPOTIFY_CLIENT_ID}&scope={scope}&redirect_uri={SPOTIFY_REDIRECT_URL}&state={state}'
    ))
    response.set_cookie(SPOTIFY_STATE_KEY, state)
    return response


@app.route('/callback')
def callback():
    code = request.args.get('code')
    state = request.args.get('state')
    stored_state = request.cookies.get(SPOTIFY_STATE_KEY)

    if state is None or state != stored_state:
        return redirect('/#' + 'error=state_mismatch')

    response = make_response(redirect('/#'))
    response.delete_cookie(SPOTIFY_STATE_KEY)

    auth_options = {
        'url': SPOTIFY_TOKEN_URL,
        'data': {
            'code': code,
            'redirect_uri': SPOTIFY_REDIRECT_URL,
            'grant_type': 'authorization_code'
        },
        'headers': {
            'content-type': 'application/x-www-form-urlencoded',
            'Authorization': 'Basic ' + base64.b64encode(f'{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}'.encode()).decode()
        }
    }

    token_response = requests.post(**auth_options)
    token_data = token_response.json()

    session['spotify_access_token'] = token_data['access_token']
    session['spotify_refresh_token'] = token_data['refresh_token']

    return response


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['GET', 'POST'])
def search_spotify():
    """Simple search for an artist."""
    if request.method == 'POST':
        artist = request.form.get('artist')
        if artist:
            res = query_artist_spotify(artist=artist)
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


@app.route('/amazon/migrate', methods=['POST'])
def migrate_playlist():
    original_playlist_id = request.form.get('submitValue')
    settings.PROGRESS = 0

    # get the playlist from amazon API (including tracks)
    original_playlist = get_paginated_track_list(playlist={}, playlist_id=original_playlist_id, cursor=None)

    # we only need artist and name of the tracks
    tracks = []
    for edge in original_playlist['tracks']['edges']:
        track = {
            'artist': edge['node']['artists'][0]['name'],
            'title': edge['node']['title'],
        }
        tracks.append(track)

    # create new playlist at spotify if not exists
    new_playlist_id = create_spotify_playlist(name=original_playlist['title'])

    # ToDo: Make this call asynch to template returns!
    thread = threading.Thread(target=add_tracks_to_spotify_playlist, name="migration", args=[session['spotify_access_token'], new_playlist_id, tracks])
    thread.start()

    return render_template(template_name_or_list='migrate.html', content=original_playlist)


@app.route('/api/progress', methods=['GET'])
def api_progress():
    return {'progress': settings.PROGRESS}
