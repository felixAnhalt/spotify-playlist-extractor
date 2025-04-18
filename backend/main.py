from fastapi import FastAPI
from authentication import auth
from spotify import playlist
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Spotify Playlist Organizer Backend")

# Allow requests from your frontend (e.g., localhost:3000)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Add other frontend URLs as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,              # Allow specific origins
    allow_credentials=True,
    allow_methods=["*"],                # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],                # Allow all headers (Authorization, etc.)
)

# Include authentication routes
app.include_router(auth.router)

app.include_router(playlist.router)
