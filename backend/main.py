from fastapi import FastAPI
from authentication import auth
from spotify import playlist

app = FastAPI(title="Spotify Playlist Organizer Backend")

# Include authentication routes
app.include_router(auth.router)

app.include_router(playlist.router)
