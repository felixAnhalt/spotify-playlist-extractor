from fastapi import APIRouter, Request, Response, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from urllib.parse import urlencode
import secrets
import base64
import hashlib
import os
import httpx

from config import config
from authentication import session_store

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
    print("Starting Spotify OAuth2 login flow")
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
    redirect_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    print(f"Redirecting to Spotify: {redirect_url}")
    body = { "redirect_url": redirect_url }
    print(f"Redirecting to Spotify: {body}")
    return JSONResponse(body)

@router.get("/auth/callback")
async def callback(request: Request, code: str = None, state: str = None, error: str = None):
    """
    Handles Spotify OAuth2 callback, exchanges code for tokens, and stores them in-memory.
    """
    print(f"Starting Spotify OAuth2 callback flow: code={code}, state={state}, error={error}")
    if error:
        print("OAuth2 callback error")
        return JSONResponse({"error": error}, status_code=status.HTTP_400_BAD_REQUEST)
    if not code or not state:
        print(f"Missing code or state: code={code}, state={state}")
        return JSONResponse({"error": "Missing code or state"}, status_code=status.HTTP_400_BAD_REQUEST)
    code_verifier = session_store.get_code_verifier(state)
    if not code_verifier:
        print(f"Invalid state: {code_verifier}")
        return JSONResponse({"error": "Invalid state"}, status_code=status.HTTP_400_BAD_REQUEST)
    # Exchange code for tokens
    data = {
        "client_id": config.SPOTIFY_CLIENT_ID,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.SPOTIFY_REDIRECT_URI,
        "code_verifier": code_verifier,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    print(f"Exchanging code for tokens: {data}")
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
    if resp.status_code != 200:
        return JSONResponse({"error": "Failed to fetch tokens"}, status_code=status.HTTP_400_BAD_REQUEST)
    tokens = resp.json()
    session_store.save_tokens(state, tokens)
    return JSONResponse({"message": "Authentication successful"})