# SpotifyPlaylistShuffleHelper

## Description and Usage

This script provides a workaround for Spotify's insufficient shuffle function. To use it, first specify a source playlist to be monitored and a target playlist. 

The script will then check every 20 seconds (adjustable) which song from which playlist is currently playing. If the song is from the source playlist, it will be added to the target playlist and removed from the source playlist. 

This ensures that the song won't be played again during the shuffle of the playlist. This method allows older songs in a large playlist to be played through the shuffle function.

## Installation

1. Log in to [developer.spotify.com](https://developer.spotify.com).
2. Create a new project.
3. Edit the settings to add Redirect URIs to `http://<your-docker-ip>:8888/callback`.
4. Download `docker-compose.yaml`.
5. Map the volumes.
6. Set `CLIENT_ID` and `CLIENT_SECRET` from the Spotify project, and also change your Callback URL.
7. Define your `PLAYLIST_PAIRS` with the playlist ids e.g.:

   ```
   PLAYLIST_PAIRS: '[{"source_playlist_id": "2u6YwYORaQRWptbXc1VsZB", "target_playlist_id": "37i9dQZF1DZ06evO49hLQA"}, {"source_playlist_id": "37i9dQZF1DZ06evO49hLQA", "target_playlist_id": "2u6YwYORaQRWptbXc1VsZB"}]'
   ```
   You can add as many pairs as you wish in this format.

8. Run docker-compose up.
9. Visit `http://<your-docker-ip>:8888/` and authorize Spotify. If everything went well, the script will start working.