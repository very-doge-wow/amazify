# Client info for Spotify
import os

SPOTIFY_CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
SPOTIFY_CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']

# Client info for Amazon Music
AMAZON_TOKEN = os.environ['AMAZON_TOKEN']
AMAZON_X_API_KEY = os.environ['AMAZON_X_API_KEY']

# Spotify API endpoints and configs
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_BASE_ENDPOINT = 'https://api.spotify.com/v1'
SPOTIFY_SEARCH_ENDPOINT = f'{SPOTIFY_BASE_ENDPOINT}/search'
SPOTIFY_ME_ENDPOINT = f'{SPOTIFY_BASE_ENDPOINT}/me'
SPOTIFY_REDIRECT_URL = 'http://127.0.0.1:5000/callback'
SPOTIFY_STATE_KEY = 'spotify_auth_state'
SPOTIFY_API_SCOPES = [
    'user-read-private',
    'user-read-email',
    'playlist-modify-private',
    'playlist-modify-public',
]

# Amazon API endpoints
AMAZON_BASE_ENDPOINT = 'https://api.music.amazon.dev/v1'
AMAZON_TOKEN_URL = 'https://api.amazon.com/auth/o2/token'
AMAZON_ME_ENDPOINT = f'{AMAZON_BASE_ENDPOINT}/me'

# storage for progress
PROGRESS = 0
# storage for failed migration of songs
FAILED_TRACKS = ""
# stores source tracks and their destination tracks
TRACK_TRANSLATION = []
# stores target playlist url after creation
DESTINATION_PLAYLIST_URL = ""
