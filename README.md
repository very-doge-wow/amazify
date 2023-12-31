# amazify

Migrate your playlists from Amazon Music to Spotify.

## Setup and Startup

### Spotify Authentication

First you need to navigate to [developer.spotify.com](https://developer.spotify.com/dashboard) and
create a new app. Use the following as callback URL:

```
http://127.0.0.1:5000/auth/spotify
```

### Amazon Authentication

Currently, the Amazon Music API won't let us create applications ourselves without
them needing to be approved by Amazon. Since we only want to perform a one-time
migration, we can obtain an OAuth token via Amazon's own API reference, hence elemininating
the need for us to be able to create our own application.

Navigate to [dashboard.music.amazon.dev](https://dashboard.music.amazon.dev/console/api/get-playlist/)
and press the button `Get Token` in order to retrieve a valid token.
Login using your Amazon Music profile's credentials when prompted.
Copy the resulting token and set it as environment variable as described in the next step.
Make sure to also copy the `x-api-key` value as provided in the example `curl`
command given on Amazon's website as well.

### Required Environment Variables
Next set some environment variables. Get the client id and client
secret from the spotify app you have just created.

```shell
export FLASK_APP=app.py
export SPOTIFY_CLIENT_ID=XXX
export SPOTIFY_CLIENT_SECRET=XXX
export AMAZON_TOKEN=XXX
export AMAZON_X_API_KEY=XXX
export SECRET_KEY=fakekey
```

### Installation of Dependencies

Install the dependencies using pipenv:

```shell
pipenv install
```

### Actual Startup
Next you can start the flask server like this:

```shell
pipenv run python -m flask run
```
