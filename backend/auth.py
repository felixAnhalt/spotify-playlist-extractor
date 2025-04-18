from fastapi import APIRouter, Request, Response, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from urllib.parse import urlencode
import secrets
import base64
import hashlib
import os

from . import config, session_store

router = APIRouter()

def generate_code_verifier() -> str:
    """
    Generates a secure code verifier for PKCE.
    """
    return base64.urlsafe_b64encode(os.urandom(64)).rstrip(b'=').decode('utf-8')

def generate_code_challenge(verifier: str) -> str:
    """
    Generates a code challenge from the code verifier using SHA256.
    """
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('utf-8')

@router.get("/auth/login")
async def login(request: Request):
    """
    Initiates Spotify OAuth2 Authorization Code Flow with PKCE.
    Redirects user to Spotify's authorization endpoint.
    """
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(16)
    session_store.save_state(state, code_verifier)
    params = {
        "client_id": config.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": config.SPOTIFY_REDIRECT_URI,
        "scope": config.SPOTIFY_SCOPE,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
    }
    url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    return RedirectResponse(url)

@router.get("/auth/callback")
async def callback(request: Request, code: str = None, state: str = None, error: str = None):
    """
    Handles Spotify OAuth2 callback, exchanges code for tokens, and stores them in-memory.
    """
    if error:
        return JSONResponse({"error": error}, status_code=status.HTTP_400_BAD_REQUEST)
    if not code or not state:
        return JSONResponse({"error": "Missing code or state"}, status_code=status.HTTP_400_BAD_REQUEST)
    code_verifier = session_store.get_code_verifier(state)
    if not code_verifier:
        return JSONResponse({"error": "Invalid state"}, status_code=status.HTTP_400_BAD_REQUEST)
    # Exchange code for tokens
    import httpx
    data = {
        "client_id": config.SPOTIFY_CLIENT_ID,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.SPOTIFY_REDIRECT_URI,
        "code_verifier": code_verifier,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
    if resp.status_code != 200:
        return JSONResponse({"error": "Failed to fetch tokens"}, status_code=status.HTTP_400_BAD_REQUEST)
    tokens = resp.json()
    session_store.save_tokens(state, tokens)
    return JSONResponse({"message": "Authentication successful"})