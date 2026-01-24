"""
Endpoints for fetching Spotify playlist tracks and their audio features, and clustering tracks by vibe.
"""

from fastapi import APIRouter, Request, HTTPException, status, Body
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import httpx
import asyncio
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score
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

async def fetch_liked_tracks(access_token: str) -> List[Dict[str, Any]]:
    """
    Fetches ALL user's liked songs from Spotify /me/tracks endpoint with pagination.
    Returns a list of track objects (each item has a 'track' key with the track data).
    """
    liked_items = []
    url = f"{SPOTIFY_API_BASE}/me/tracks"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"limit": 50, "offset": 0}

    async with httpx.AsyncClient() as client:
        while url:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch liked tracks")
            data = resp.json()
            liked_items.extend(data.get("items", []))
            url = data.get("next")
            params = None  # Only needed for the first request

    return liked_items

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

@router.post("/playlist/liked-tracks")
async def get_user_liked_tracks(request: Request):
    """
    Fetches ALL user's liked songs with audio features.
    Accepts JSON body with 'state' (required).
    Returns same format as /playlist/tracks endpoint for compatibility with clustering pipeline.
    """
    try:
        body = await request.json()
        print(f"Request body received: {body}")
    except Exception as e:
        print(f"Error parsing request body: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")

    state = body.get("state")
    print(f"State value: {state}")

    if not state:
        print("State is missing or empty")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing state")

    tokens = session_store.get_tokens(state)
    if not tokens or "access_token" not in tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No valid access token for state")

    access_token = tokens["access_token"]

    # Fetch ALL liked tracks
    print("Fetching all liked tracks...")
    liked_items = await fetch_liked_tracks(access_token)
    print(f"Fetched {len(liked_items)} liked items")

    # Extract track IDs
    track_ids = [item["track"]["id"] for item in liked_items if item.get("track") and item["track"].get("id")]
    print(f"Extracted {len(track_ids)} track IDs")

    # Fetch audio features
    audio_features = await fetch_audio_features(access_token, track_ids)
    print(f"Fetched audio features for {len(audio_features)} tracks")

    # Build result in same format as /playlist/tracks
    result = []
    for item in liked_items:
        track = item.get("track")
        if not track or not track.get("id"):
            continue
        track_id = track["id"]
        result.append({
            "track": track,
            "audio_features": audio_features.get(track_id)
         })

    return JSONResponse({"tracks": result})

def normalize_audio_features(tracks: list, feature_keys: list, feature_weights: Optional[Dict[str, float]] = None) -> tuple:
    """
    Normalizes the specified audio features for all tracks using StandardScaler.
    Applies optional feature weighting to emphasize certain features.
    Returns a tuple of (normalized features array, scaler).
    """
    features = []
    for t in tracks:
        af = t.get("audio_features") or {}
        features.append([af.get(k, 0.0) for k in feature_keys])

    scaler = StandardScaler()
    return scaler.fit_transform(features)

def determine_optimal_clusters(tracks: list, feature_keys: list, min_clusters: int = 3, max_clusters: int = 15) -> int:
    """
    Determines the optimal number of clusters using a hybrid approach:
    1. Elbow method with inertia (within-cluster sum of squares)
    2. Davies-Bouldin score (lower is better - ratio of within to between cluster distances)
    3. Size-based heuristics for reasonable bounds

    Args:
        tracks: List of track objects with audio_features
        feature_keys: List of audio feature keys to use for clustering
        min_clusters: Minimum number of clusters to test (default: 3)
        max_clusters: Maximum number of clusters to test (default: 15)

    Returns:
        Optimal number of clusters
    """
    X = normalize_audio_features(tracks, feature_keys)
    n_samples = len(X)

    # Edge cases
    if n_samples < 2:
        return 1
    if n_samples < min_clusters:
        return max(2, min(n_samples, 3))

    # Heuristic: playlist size influences cluster range
    # Small playlists (< 20): 2-4 clusters
    # Medium playlists (20-50): 3-6 clusters
    # Large playlists (50-150): 5-10 clusters
    # Very large playlists (150-400): 8-15 clusters
    # Massive playlists (400+): 12-25 clusters
    if n_samples < 20:
        min_clusters, max_clusters = 2, 4
    elif n_samples < 50:
        min_clusters, max_clusters = 3, 6
    elif n_samples < 150:
        min_clusters, max_clusters = 5, 10
    elif n_samples < 400:
        min_clusters, max_clusters = 8, 15
    else:
        # For massive playlists, aim for ~30-50 tracks per cluster
        min_clusters = max(12, n_samples // 50)
        max_clusters = min(25, n_samples // 25)

    print(f"Playlist size: {n_samples} tracks. Testing {min_clusters}-{max_clusters} clusters")

    inertias = []
    db_scores = []
    k_range = range(min_clusters, max_clusters + 1)

    # Test different cluster counts
    for k in k_range:
        try:
            kmeans = KMeans(n_clusters=k, n_init='auto', random_state=42)
            labels = kmeans.fit_predict(X)

            # Calculate metrics
            inertia = kmeans.inertia_
            db_score = davies_bouldin_score(X, labels)

            inertias.append(inertia)
            db_scores.append(db_score)

            print(f"k={k}: inertia={inertia:.2f}, davies_bouldin={db_score:.3f}")
        except Exception as e:
            print(f"Error testing k={k}: {e}")
            inertias.append(float('inf'))
            db_scores.append(float('inf'))

    # Find elbow point using rate of change
    best_k = min_clusters
    if len(inertias) > 2:
        # Calculate rate of decrease in inertia
        deltas = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
        # Calculate second derivative (rate of change of rate of change)
        second_deltas = [deltas[i] - deltas[i+1] for i in range(len(deltas)-1)]

        # Find elbow: where improvement rate drops significantly
        # Combined with Davies-Bouldin score (lower is better)
        scores = []
        for i in range(len(second_deltas)):
            k = min_clusters + i + 1
            idx = i + 1
            # Normalize metrics (lower is better for both)
            # Weight: 60% elbow sharpness, 40% cluster quality
            elbow_score = second_deltas[i] if second_deltas[i] > 0 else 0
            db_normalized = 1.0 / (1.0 + db_scores[idx]) if db_scores[idx] != float('inf') else 0
            combined_score = 0.6 * elbow_score + 0.4 * db_normalized
            scores.append((k, combined_score))
            print(f"k={k}: combined_score={combined_score:.3f} (elbow={elbow_score:.3f}, db_norm={db_normalized:.3f})")

        if scores:
            best_k = max(scores, key=lambda x: x[1])[0]

    print(f"Optimal number of clusters: {best_k}")
    return best_k

def cluster_tracks_kmeans(tracks: list, feature_keys: list, n_clusters: int = 4) -> list:
    """
    Clusters tracks using adaptive KMeans with optimal cluster count determination.

    Args:
        tracks: List of track dicts with audio_features
        feature_keys: List of audio feature keys to use for clustering
        feature_weights: Optional dict of feature_key -> weight (higher = more important)
        n_clusters: Optional fixed number of clusters (if None, will determine automatically)
        min_cluster_size: Minimum tracks per cluster

    Returns:
        Tuple of (cluster_ids list, n_clusters used)
    """
    X, scaler = normalize_audio_features(tracks, feature_keys, feature_weights)

    # Determine optimal cluster count if not specified
    if n_clusters is None:
        n_clusters = determine_optimal_clusters(X, min_clusters=3, max_clusters=10)

    # Ensure n_clusters doesn't exceed track count
    n_clusters = min(n_clusters, len(tracks))

    # Perform clustering
    kmeans = KMeans(n_clusters=n_clusters, n_init='auto', random_state=42, max_iter=300)
    labels = kmeans.fit_predict(X)

    # Balance clusters to ensure minimum size
    labels = balance_clusters(X, labels, min_size=min_cluster_size)

    # Remove empty clusters and renumber
    unique_labels = np.unique(labels)
    label_mapping = {old: new for new, old in enumerate(unique_labels)}
    labels = np.array([label_mapping[label] for label in labels])

    actual_n_clusters = len(unique_labels)

    print(f"Clustering complete: {actual_n_clusters} clusters created")
    cluster_sizes = [np.sum(labels == i) for i in range(actual_n_clusters)]
    print(f"Cluster sizes: {cluster_sizes}")

    return labels.tolist(), actual_n_clusters

@router.post("/playlist/cluster")
async def cluster_playlist_tracks(
    tracks: list = Body(..., embed=True),
    n_clusters: int = Body(None, embed=True)
):
    """
    Accepts a JSON body with 'tracks' (list of track dicts with audio_features) and optional 'n_clusters'.
    If n_clusters is not provided, it will be determined automatically using silhouette score analysis.
    Returns a list of cluster assignments for each track and the number of clusters used.
    """
    # Choose features relevant for "vibe" clustering with appropriate weights
    feature_keys = [
        "danceability", "energy", "valence", "acousticness",
        "instrumentalness", "liveness", "speechiness", "tempo"
    ]

    # Feature weights: emphasize mood/vibe features, de-emphasize technical ones
    feature_weights = {
        "valence": 1.5,        # Happiness/positivity - very important for vibe
        "energy": 1.4,         # Intensity - very important for vibe
        "danceability": 1.3,   # Groove - important for vibe
        "acousticness": 1.2,   # Organic vs electronic - important distinction
        "instrumentalness": 1.0,  # Vocals vs instrumental
        "tempo": 0.6,          # Speed - less important (normalize first)
        "speechiness": 0.8,    # Spoken word content
        "liveness": 0.7        # Live recording feel
    }

    if not tracks or not isinstance(tracks, list):
        raise HTTPException(status_code=400, detail="Missing or invalid 'tracks' list")

    # Determine optimal n_clusters if not provided
    if n_clusters is None:
        print("Auto-determining optimal number of clusters...")
        n_clusters = determine_optimal_clusters(tracks, feature_keys)
        print(f"Using {n_clusters} clusters")
    else:
        print(f"Using user-specified {n_clusters} clusters")

    cluster_ids = cluster_tracks_kmeans(tracks, feature_keys, n_clusters)
    return JSONResponse({"cluster_ids": cluster_ids, "n_clusters": n_clusters})


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
        "- Avoid generic terms like 'music', 'songs', 'playlist', 'neon', or 'cluster',\n"
        "- Examples for the top 20 playlist names with categories:\n"
        "Deep House Summer\n"
        "Dance, Deep House, Party\n"

        "Lo-fi Girl – beats to relax/study to\n"
        "Lo-fi, Chill, Study\n"

        "Dance Fruits – Dance Music to Workout / Party\n"
        "Dance, Workout, Party\n"

        "Car Music (Future House Cloud)\n"
        "Driving, Electronic, House\n"

        "Deep House – workout / game / party\n"
        "Deep House, Workout, Gaming\n"

        "Chillout – We Are Diamond\n"
        "Chillout, Lounge, Electronic\n"

        "Chill Beats – Relax & Groove\n"
        "Chill, Lo-fi, Downtempo\n"

        "Trap Nation\n"
        "Trap, Electronic, Bass\n"

        "CAR MUSIC – Bass Boosted EDM Remix\n"
        "EDM, Bass Boost, Driving\n"

        "Bass Boosted Car\n"
        "Bass Boost, EDM, Driving\n"

        "WORKOUT MUSIC – High Energy Gym Songs\n"
        "Workout, Fitness, High Energy\n"

        "Workout Motivation\n"
        "Workout, Motivation\n"

        "Billboard Hot 100 (User-curated)\n"
        "Pop, Charts, Hits\n"

        "Chill House\n"
        "Chill, House\n"

        "RUNNING Music Hits\n"
        "Running, Cardio, Fitness\n"

        "Gaming Music Playlist\n"
        "Gaming, Electronic\n"

        "GYM PHONK – Aggressive Workout Phonk\n"
        "Phonk, Workout, Aggressive\n"

        "Chill Vibes\n"
        "Chill, Mood, Vibes\n"
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
