import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, redirect
import logging
import time
import threading

app = Flask(__name__)

# Configuring logging
log_directory = './logs'
log_file_path = os.path.join(log_directory, 'SpotifyPlaylistShuffleHelper.log')

if not os.path.exists(log_directory):
    os.makedirs(log_directory)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_file_path), logging.StreamHandler()])

logging.info("╭────────────────────────────────────────╮")
logging.info("│                                        │")
logging.info("│           Script starting...           │")
logging.info("│                                        │")
logging.info("╰────────────────────────────────────────╯")

# Spotify API credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# Source and target playlist pairs
PLAYLIST_PAIRS = os.getenv("PLAYLIST_PAIRS")
if PLAYLIST_PAIRS:
    PLAYLIST_PAIRS = eval(PLAYLIST_PAIRS)
else:
    logging.error("PLAYLIST_PAIRS environment variable is not set or empty.")
    raise ValueError("PLAYLIST_PAIRS environment variable is not set or empty.")

# Cache playlist names and tracks
playlist_names_cache = {}
playlist_tracks_cache = {}

# Initialize Spotify API authentication
data_directory = './data'
cache_file_path = os.path.join(data_directory, '.spotify_cache')

if not os.path.exists(data_directory):
    os.makedirs(data_directory)

scope = "user-library-read playlist-modify-public playlist-modify-private user-read-playback-state user-read-recently-played"
sp_oauth = SpotifyOAuth(client_id=CLIENT_ID,
                        client_secret=CLIENT_SECRET,
                        redirect_uri=REDIRECT_URI,
                        scope=scope,
                        cache_path=cache_file_path)

# Global Spotify client variable
sp = None

@app.route('/')
def index():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    global sp
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code, as_dict=False)
    if token_info:
        sp = spotipy.Spotify(auth=token_info)
        return "Spotify authentication successful! You can close this window."
    else:
        return "Spotify authentication failed."

def get_playlist_name(playlist_id):
    if playlist_id in playlist_names_cache:
        return playlist_names_cache[playlist_id]
    try:
        playlist = sp.playlist(playlist_id)
        playlist_name = playlist['name']
        playlist_names_cache[playlist_id] = playlist_name
        return playlist_name
    except Exception as e:
        logging.error(f"Error retrieving playlist name for {playlist_id}: {e}")
    return None

def cache_playlist_tracks(playlist_id):
    try:
        offset = 0
        tracks = []
        while True:
            playlist_tracks = sp.playlist_tracks(playlist_id, offset=offset)
            tracks.extend([item['track']['id'] for item in playlist_tracks['items']])
            if not playlist_tracks['next']:
                break
            offset += len(playlist_tracks['items'])
        playlist_tracks_cache[playlist_id] = tracks
    except Exception as e:
        logging.error(f"Error caching tracks for playlist {playlist_id}: {e}")

def get_current_track():
    try:
        current_track = sp.current_playback()
        if current_track and current_track['item']:
            return current_track['item']['id'], current_track['item']['name']
    except spotipy.SpotifyException as e:
        if e.http_status == 401:  # Unauthorized, token expired
            logging.info("Access token expired. Refreshing token...")
            #sp_oauth.refresh_access_token(sp_oauth.get_cached_token()['refresh_token'])
            authenticate_spotify()
            logging.info("Token refreshed successfully.")
            # Retry getting the current track
            return get_current_track()
        elif e.http_status == 429:  # API rate limit reached
            retry_after = int(e.headers.get('Retry-After', 60))  # Default to 60 seconds if Retry-After header is not provided
            logging.warning(f"API rate limit reached. Waiting for {retry_after} seconds cooldown...")
            time.sleep(retry_after)
            # Retry getting the current track
            return get_current_track()
        else:
            logging.error(f"Error retrieving current track: {e}")
    except Exception as e:
        logging.error(f"Error retrieving current track: {e}")
    return None, None


def check_and_move_track(track_id, track_name, source_playlist_id, target_playlist_id):
    try:
        # Check if the track is being played in the source playlist and if it's active
        current_playback = sp.current_playback()
        if current_playback and current_playback['context'] and current_playback['context']['uri'] == f"spotify:playlist:{source_playlist_id}" and current_playback['is_playing']:
            # Retrieve cached tracks of the source playlist
            source_tracks = playlist_tracks_cache.get(source_playlist_id, [])
            source_playlist_name = get_playlist_name(source_playlist_id)
            target_playlist_name = get_playlist_name(target_playlist_id)
            if track_id not in source_tracks:
                logging.info(f"'{track_name}' not found in cache of playlist '{source_playlist_name}'. Updating cache.")
                cache_playlist_tracks(source_playlist_id)
                source_tracks = playlist_tracks_cache.get(source_playlist_id, [])
            
            if track_id in source_tracks:
                logging.info(f"Moving '{track_name}' from playlist '{source_playlist_name}' to playlist '{target_playlist_name}'.")
                sp.playlist_add_items(target_playlist_id, [track_id])
                sp.playlist_remove_all_occurrences_of_items(source_playlist_id, [track_id])
                # Update cache
                playlist_tracks_cache[source_playlist_id].remove(track_id)
                return True
            else:
                logging.info(f"'{track_name}' is not in the source playlist '{source_playlist_name}' after updating the cache.")
                return False
    except Exception as e:
        logging.error(f"Error moving track: {e}")
    return False

def authenticate_spotify():
    global sp
    try:
        sp_oauth.refresh_access_token(sp_oauth.get_cached_token()['refresh_token']) # Get new Token
    except Exception as e:
        logging.error(f"Error refresh cached token: {e}")

    token_info = sp_oauth.get_cached_token()
    if token_info:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        logging.info("Spotify authenticated with cached token.")
    else:
        logging.info("Spotify token not found in cache, using web authentication.")
        # Start Flask app for web authentication in a separate thread
        threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8888)).start()
        logging.info("Waiting for Spotify authentication...")

def main():
    logging.info("Starting SpotifyPlaylistShuffleHelper...")
    last_track_id = None
    moved = False
    # Cache tracks of all source playlists
    for playlist_pair in PLAYLIST_PAIRS:
        cache_playlist_tracks(playlist_pair["source_playlist_id"])
    while True:
        try:
            current_track_id, current_track_name = get_current_track()
            if current_track_id and (current_track_id != last_track_id or not moved):
                moved = False
                for playlist_pair in PLAYLIST_PAIRS:
                    source_playlist_id = playlist_pair["source_playlist_id"]
                    target_playlist_id = playlist_pair["target_playlist_id"]
                    if check_and_move_track(current_track_id, current_track_name, source_playlist_id, target_playlist_id):
                        moved = True
                if not moved:
                    logging.info(f"No action taken for track '{current_track_name}' (ID: {current_track_id}).")
                last_track_id = current_track_id
            time.sleep(int(os.getenv('SLEEP_TIME', 20)))  # Wait time between checks
        except Exception as e:
            logging.error(f"Error in main process: {e}")
            time.sleep(60)  # Wait time before retry

if __name__ == '__main__':
    # Attempt to authenticate Spotify
    authenticate_spotify()

    # Wait until Spotify client is initialized
    while sp is None:
        time.sleep(1)

    # Run the main function once Spotify is authenticated
    main()
