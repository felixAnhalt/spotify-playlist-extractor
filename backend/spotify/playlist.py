"""
Endpoints for fetching Spotify playlist tracks and their audio features, and clustering tracks by vibe.
"""

from fastapi import APIRouter, Request, HTTPException, status, Body
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import httpx
import asyncio
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from collections import defaultdict
import numpy as np

from authentication import session_store
from config.config import OPENROUTER_API_KEY, OPENROUTER_API_URL, RECCOBEATS_API_BASE

router = APIRouter()

SPOTIFY_API_BASE = "https://api.spotify.com/v1"

def extract_playlist_id(playlist_id_or_url: str) -> str:
    """
    Extracts the playlist ID from a Spotify playlist URL or returns the ID if already provided.
    """
    if "spotify.com/playlist/" in playlist_id_or_url:
        return playlist_id_or_url.split("playlist/")[1].split("?")[0]
    return playlist_id_or_url

async def fetch_all_tracks(access_token: str, playlist_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all tracks from a Spotify playlist, handling pagination.
    Returns a list of track objects.
    """
    tracks = []
    url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"limit": 100, "offset": 0}
    async with httpx.AsyncClient() as client:
        while url:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch playlist tracks")
            data = resp.json()
            tracks.extend(data.get("items", []))
            url = data.get("next")
            params = None  # Only needed for the first request
    return tracks

async def fetch_audio_features(access_token: str, track_ids: List[str]) -> Dict[str, Any]:
    """
    Fetches audio features for a list of track IDs using Reccobeats API.
    Batches requests (50 tracks per request) to be respectful of rate limits.
    Returns a dict mapping track ID to audio features.
    Note: access_token parameter kept for backward compatibility but not used.
    """
    features = {}
    batch_size = 40  # Conservative batch size to avoid overwhelming the API
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(0, len(track_ids), batch_size):
            batch = track_ids[i:i+batch_size]
            ids_param = ",".join(batch)
            url = f"{RECCOBEATS_API_BASE}/audio-features"

            # Retry logic for rate limiting
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    resp = await client.get(url, params={"ids": ids_param})

                    if resp.status_code == 429:  # Rate limited
                        retry_after = int(resp.headers.get("Retry-After", 5))
                        print(f"Rate limited. Waiting {retry_after} seconds before retry {attempt+1}/{max_retries}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            raise HTTPException(status_code=429, detail="Rate limit exceeded after retries")

                    if resp.status_code != 200:
                        print(f"Reccobeats API error: {resp.status_code} - {resp.text}")
                        raise HTTPException(
                            status_code=resp.status_code,
                            detail=f"Failed to fetch audio features from Reccobeats: {resp.text}"
                        )

                    data = resp.json()
                    # Reccobeats returns {"content": [...]} not {"audio_features": [...]}
                    # Each item has an internal UUID "id" but the Spotify ID is in the "href" URL
                    for af in data.get("content", []):
                        if af and af.get("href"):
                            # Extract Spotify track ID from href
                            # href format: "https://open.spotify.com/track/{spotify_id}"
                            href = af["href"]
                            if "/track/" in href:
                                spotify_id = href.split("/track/")[1].split("?")[0]
                                features[spotify_id] = af
                    break  # Success, exit retry loop

                except httpx.TimeoutException:
                    print(f"Timeout on attempt {attempt+1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    else:
                        raise HTTPException(status_code=504, detail="Timeout fetching audio features")

    return features

@router.post("/playlist/tracks")
async def get_playlist_tracks(request: Request):
    """
    Accepts a JSON body with 'playlist_id_or_url' and 'state'.
    Fetches all tracks and their audio features for the given playlist.
    Returns JSON with track metadata and audio features.
    """
    body = await request.json()
    playlist_id_or_url = body.get("playlist_id_or_url")
    state = body.get("state")
    if not playlist_id_or_url or not state:
        print(f"Missing playlist_id_or_url or state: {playlist_id_or_url}, {state}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing playlist_id_or_url or state")
    tokens = session_store.get_tokens(state)
    if not tokens or "access_token" not in tokens:
        print(f"No valid access token for state: {state}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No valid access token for state")
    access_token = tokens["access_token"]
    playlist_id = extract_playlist_id(playlist_id_or_url)
    print(f"Fetching tracks for playlist: {playlist_id} {access_token}")
    tracks = await fetch_all_tracks(access_token, playlist_id)
    print(f"Fetched tracks for playlist: {len(tracks)}")
    #tracks mapped to id, track name, [artist names]
    track_collection = [{
        "id": item["track"]["id"],
        "name": item["track"]["name"],
        "artists": [artist["name"] for artist in item["track"]["artists"]]
    } for item in tracks if item.get("track") and item["track"].get("id")]
    print(f"Fetched tracks for playlist: {track_collection}")
    track_ids = [item["track"]["id"] for item in tracks if item.get("track") and item["track"].get("id")]
    print(f"Fetched track ids for playlist: {len(track_ids)}")
    audio_features = await fetch_audio_features(access_token, track_ids)
    print(f"Fetched audio features for playlist: {len(audio_features)}")
    result = []
    for item in tracks:
        track = item.get("track")
        if not track or not track.get("id"):
            continue
        track_id = track["id"]
        result.append({
            "track": track,
            "audio_features": audio_features.get(track_id)
        })
    return JSONResponse({"tracks": result})

@router.post("/playlist/create")
async def create_playlists(request: Request):
    """
    Creates new playlists in the user's Spotify account with user-specified names, descriptions, and tracks.
    Accepts JSON: {
        "playlists": [
            {"name": str, "description": str, "tracks": [str, ...]}
        ],
        "state": str,
        "public": bool (optional)
    }
    Returns: JSON with confirmation and links to created playlists.
    """
    body = await request.json()
    playlists = body.get("playlists")
    state = body.get("state")
    public = body.get("public", False)
    if not playlists or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing playlists or state")
    tokens = session_store.get_tokens(state)
    if not tokens or "access_token" not in tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No valid access token for state")
    access_token = tokens["access_token"]

    created = []
    async with httpx.AsyncClient() as client:
        # Get user ID
        user_resp = await client.get(f"{SPOTIFY_API_BASE}/me", headers={"Authorization": f"Bearer {access_token}"})
        if user_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to fetch user profile")
        user_id = user_resp.json()["id"]

        for pl in playlists:
            name = pl.get("name")
            description = pl.get("description", "")
            track_ids = pl.get("tracks", [])
            if not name or not isinstance(track_ids, list):
                continue
            # Create playlist
            pl_resp = await client.post(
                f"{SPOTIFY_API_BASE}/users/{user_id}/playlists",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"name": name, "description": description, "public": public}
            )
            if pl_resp.status_code != 201:
                print(f"Failed to create playlist '{name}': {pl_resp.status_code} - {pl_resp.text}")
                continue
            pl_data = pl_resp.json()
            playlist_id = pl_data["id"]
            playlist_url = pl_data.get("external_urls", {}).get("spotify")
            # Add tracks in batches of 100
            for i in range(0, len(track_ids), 100):
                batch = track_ids[i:i+100]
                tracks_resp = await client.post(
                    f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks",
                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                    json={"uris": [f"spotify:track:{tid}" for tid in batch]}
                )
                if tracks_resp.status_code not in [200, 201]:
                    print(f"Failed to add tracks to playlist '{name}': {tracks_resp.status_code} - {tracks_resp.text}")
            created.append({"name": name, "url": playlist_url})
    return JSONResponse({"created": created})

def normalize_audio_features(tracks: list, feature_keys: list) -> list:
    """
    Normalizes the specified audio features for all tracks using StandardScaler.
    Returns a list of normalized feature vectors.
    """
    features = []
    for t in tracks:
        af = t.get("audio_features") or {}
        features.append([af.get(k, 0.0) for k in feature_keys])
    scaler = StandardScaler()
    return scaler.fit_transform(features)

def cluster_tracks_kmeans(tracks: list, feature_keys: list, n_clusters: int = 4) -> list:
    """
    Clusters tracks using KMeans on the specified audio features.
    Returns a list of cluster IDs corresponding to the input tracks.
    """
    X = normalize_audio_features(tracks, feature_keys)
    kmeans = KMeans(n_clusters=n_clusters, n_init='auto', random_state=42)
    return kmeans.fit_predict(X).tolist()

@router.post("/playlist/cluster")
async def cluster_playlist_tracks(
    tracks: list = Body(..., embed=True),
    n_clusters: int = Body(4, embed=True)
):
    """
    Accepts a JSON body with 'tracks' (list of track dicts with audio_features) and optional 'n_clusters'.
    Returns a list of cluster assignments for each track.
    """
    # Choose features relevant for "vibe" clustering
    feature_keys = [
        "danceability", "energy", "valence", "acousticness",
        "instrumentalness", "liveness", "speechiness", "tempo"
    ]
    if not tracks or not isinstance(tracks, list):
        raise HTTPException(status_code=400, detail="Missing or invalid 'tracks' list")
    cluster_ids = cluster_tracks_kmeans(tracks, feature_keys, n_clusters)
    return JSONResponse({"cluster_ids": cluster_ids})


@router.post("/playlist/cluster-names")
async def get_cluster_names(
    tracks: list = Body(..., embed=True),
    cluster_ids: list = Body(..., embed=True)
):
    """
    Accepts a JSON body with 'tracks' (list of track dicts with audio_features) and 'cluster_ids' (list of ints).
    Returns a list of descriptive vibe names for each cluster.
    """
    feature_keys = [
        "danceability", "energy", "valence", "acousticness",
        "instrumentalness", "liveness", "speechiness", "tempo"
    ]
    if not tracks or not isinstance(tracks, list) or not cluster_ids or not isinstance(cluster_ids, list):
        raise HTTPException(status_code=400, detail="Missing or invalid 'tracks' or 'cluster_ids' list")
    cluster_info = compute_cluster_averages(tracks, feature_keys, cluster_ids)
    names = {}
    for cid, info in cluster_info.items():
        name = await get_cluster_vibe_name(info["features"], info["tracks"])
        names[cid] = name
    return JSONResponse({"cluster_names": names})

async def get_cluster_vibe_name(cluster_features: dict, representative_tracks: list) -> str:
    """
    Calls Gemini LLM via OpenRouter API to generate a short, descriptive vibe name for a cluster.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment.")

    # Extract track names - handle both nested track objects and flat dicts
    track_names = []
    for t in representative_tracks:
        if isinstance(t, dict):
            if "track" in t and isinstance(t["track"], dict):
                track_names.append(t["track"].get("name", "Unknown"))
            else:
                track_names.append(t.get("name", "Unknown"))

    prompt = (
        "You are an expert music curator. Given the average audio features and representative tracks below, "
        "create a catchy, evocative playlist name that perfectly captures the mood, vibe, and atmosphere.\n\n"
        "Guidelines:\n"
        "- Think about what type of person would listen to this, when they'd listen, and how it makes them feel\n"
        "- Use emotional, sensory, or situational words (e.g., 'late night drives', 'focus flow', 'sunset chill')\n"
        "- Avoid generic terms like 'music', 'songs', 'playlist', or 'cluster'\n"
        "- No numbers - use words to distinguish if needed\n"
        "- Keep it under 6 words, ideally 2-4 words\n"
        "- Make it memorable and Spotify-worthy\n\n"
        f"Audio Features: {cluster_features}\n"
        f"Tracks: {', '.join(track_names)}\n\n"
        "Return ONLY the playlist name, nothing else:"
    )
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "xiaomi/mimo-v2-flash:free",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0.8
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(OPENROUTER_API_URL, headers=headers, json=data)
        if resp.status_code != 200:
            print(f"LLM API error: {resp.status_code} - {resp.text}")
            raise HTTPException(status_code=500, detail="Failed to get cluster name from LLM")
        result = resp.json()
        return result["choices"][0]["message"]["content"].strip()


def compute_cluster_averages(tracks: list, feature_keys: list, cluster_ids: list) -> dict:
    """
    Computes average audio features and selects representative tracks for each cluster.
    Returns a dict: cluster_id -> {"features": avg_features, "tracks": [track, ...]}
    """
    clusters = defaultdict(list)
    for idx, cid in enumerate(cluster_ids):
        clusters[cid].append(tracks[idx])
    result = {}
    for cid, tlist in clusters.items():
        feats = []
        for t in tlist:
            af = t.get("audio_features")
            if af is None:
                # Handle missing audio features with zeros
                feats.append([0.0 for _ in feature_keys])
            else:
                feats.append([af.get(k, 0.0) for k in feature_keys])
        avg = dict(zip(feature_keys, np.mean(feats, axis=0)))
        reps = tlist[:3]  # first 3 as representatives
        result[cid] = {"features": avg, "tracks": reps}
    return result
