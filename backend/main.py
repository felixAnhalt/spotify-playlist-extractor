from fastapi import FastAPI
from backend import auth

app = FastAPI(title="Spotify Playlist Organizer Backend")

# Include authentication routes
app.include_router(auth.router)