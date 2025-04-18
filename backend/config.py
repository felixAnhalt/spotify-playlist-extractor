"""
Configuration for Spotify OAuth2 integration.
Edit these values with your Spotify app credentials.
"""

import os

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "your_spotify_client_id")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/auth/callback")
SPOTIFY_SCOPE = "user-read-private user-read-email"