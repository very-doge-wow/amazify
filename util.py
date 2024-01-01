import json
import logging
import random
import string
import time
import urllib

import requests
from flask import session

import settings
from settings import *


def generate_random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def query_artist_spotify(artist=None):
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


def get_paginated_track_list(playlist: dict, playlist_id: str, cursor: str = None):
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
        playlist = get_paginated_track_list(playlist=playlist, playlist_id=playlist_id, cursor=cursor)

    return playlist


def create_spotify_playlist(name: str):
    """Creates a spotify playlist with the given name if it doesn't exist yet."""
    # get current user's id
    headers = {
        'Authorization': f"Bearer {session.get('spotify_access_token')}",
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    resp = requests.get(SPOTIFY_ME_ENDPOINT, headers=headers)
    user_id = json.loads(resp.text)['id']
    
    endpoint = f"{SPOTIFY_BASE_ENDPOINT}/users/{user_id}/playlists"
    headers = {
        "Authorization": f"Bearer {session['spotify_access_token']}",
        "Content-Type": "application/json",
    }

    data = {
        "name": name,
        "description": "Playlist migrated using Amazify",
        "public": False
    }

    response = requests.post(endpoint, headers=headers, json=data)
    if response.status_code != 201:
        logging.error("could not create new playlist in spotify")
        logging.error(response.text)

    playlist_id = json.loads(response.text)['id']
    return playlist_id


def add_tracks_to_spotify_playlist(spotify_access_token: str, playlist_id: str, tracks: list[dict]):
    count = 0
    for track in tracks:
        # first get track id
        logging.debug(f"Searching for track: {track['artist']} - {track['title']}")
        url = f'{SPOTIFY_BASE_ENDPOINT}/search'
        params = {
            'q': f'remaster%20track:{track["title"]}%20artist:{track["artist"]}',
            'type': 'track',
            'limit': 2,
        }
        headers = {
            'Authorization': f'Bearer {spotify_access_token}'
        }
        response = requests.get(url, params=params, headers=headers)
        results = json.loads(response.text)['tracks']['items']
        # sort results by popularity and use most popular
        result = sorted(results, key=lambda d: d['popularity'])[0]
        spotify_track_id = result['id']
        # might return inaccurate results if track is not actually present in spotify
        logging.debug(f'Found track on spotify: {result["artists"][0]["name"]} - {result["name"]}')

        # add track to playlist
        url = f'{SPOTIFY_BASE_ENDPOINT}/playlists/{playlist_id}/tracks'
        headers = {
            'Authorization': f'Bearer {spotify_access_token}',
            'Content-Type': 'application/json',
        }
        data = {
            'uris': [
                f'spotify:track:{spotify_track_id}'
            ],
            'position': 0
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 201:
            logging.error("couldn't add track {track['artist'] - track['title']} to playlist")
            logging.error(response.text)

        # update progress
        count += 1
        settings.PROGRESS = (count / len(tracks)) * 100
        logging.debug(f"length of tracks: {len(tracks)}")
        logging.debug(f"track count: {count}")
        logging.debug(f"progress: {settings.PROGRESS}")
