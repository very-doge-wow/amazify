import json
import random
import string
import time

import requests
from flask import session


def generate_random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def query_artist_spotify(spotify_search_endpoint: str, artist=None):
    """Make request for data on `artist`."""

    if artist is None:
        return artist

    payload = {'q': artist, 'type': 'artist', 'limit': '50'}
    headers = {
        'Authorization': f"Bearer {session.get('spotify_access_token')}",
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    return requests.get(spotify_search_endpoint, params=payload, headers=headers)


def get_paginated_track_list(amazon_base_endpoint: str, amazon_token: str, amazon_x_api_key: str, playlist: dict, playlist_id: str, cursor: str = None):
    # get the playlist from amazon API (including tracks)
    url = f"{amazon_base_endpoint}/playlists/{playlist_id}/tracks"
    if cursor:
        url += f"?cursor={cursor}"
    headers = {
        "Authorization": f"Bearer {amazon_token}",
        "x-api-key": amazon_x_api_key,
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
        playlist = get_paginated_track_list(playlist=playlist, playlist_id=playlist_id, cursor=cursor)

    return playlist


def create_spotify_playlist(spotify_me_endpoint: str, name: str):
    """Creates a spotify playlist with the given name if it doesn't exist yet."""
    # get current user's id
    headers = {
        'Authorization': f"Bearer {session.get('spotify_access_token')}",
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    resp = requests.get(spotify_me_endpoint, headers=headers)
    data = json.loads(resp.text)
    print(data)
