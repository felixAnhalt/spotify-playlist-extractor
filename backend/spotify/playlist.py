"""
Endpoints for fetching Spotify playlist tracks and their audio features, and clustering tracks by vibe.
"""

from fastapi import APIRouter, Request, HTTPException, status, Body
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import httpx
import asyncio
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score
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
                continue
            pl_data = pl_resp.json()
            playlist_id = pl_data["id"]
            playlist_url = pl_data.get("external_urls", {}).get("spotify")
            # Add tracks in batches of 100
            for i in range(0, len(track_ids), 100):
                batch = track_ids[i:i+100]
                await client.post(
                    f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks",
                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                    json={"uris": [f"spotify:track:{tid}" for tid in batch]}
                )
            created.append({"name": name, "url": playlist_url})
    return JSONResponse({"created": created})

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
    X_normalized = scaler.fit_transform(features)
    
    # Apply feature weighting if provided
    if feature_weights is not None:
        weights = np.array([feature_weights.get(k, 1.0) for k in feature_keys])
        X_normalized = X_normalized * weights
    
    return X_normalized, scaler

def determine_optimal_clusters(X: np.ndarray, min_clusters: int = 2, max_clusters: int = 12) -> int:
    """
    Determines the optimal number of clusters using silhouette score and elbow method.
    Balances cluster quality with reasonable cluster sizes.
    Returns the optimal number of clusters.
    """
    n_samples = len(X)
    
    # Adjust max_clusters based on dataset size
    # Rule: at least 5 tracks per cluster on average, max 15 clusters
    max_clusters = min(max_clusters, max(2, n_samples // 5), 15)
    min_clusters = min(min_clusters, max_clusters)
    
    if max_clusters <= min_clusters:
        return min_clusters
    
    silhouette_scores = []
    inertias = []
    
    for k in range(min_clusters, max_clusters + 1):
        kmeans = KMeans(n_clusters=k, n_init='auto', random_state=42, max_iter=300)
        labels = kmeans.fit_predict(X)
        
        # Calculate silhouette score (higher is better, range -1 to 1)
        sil_score = silhouette_score(X, labels)
        silhouette_scores.append(sil_score)
        inertias.append(kmeans.inertia_)
    
    # Find optimal k using silhouette score with elbow detection
    # Prefer higher silhouette scores but penalize too many clusters
    silhouette_scores = np.array(silhouette_scores)
    
    # Normalize inertias for elbow detection
    inertias = np.array(inertias)
    normalized_inertias = (inertias - inertias.min()) / (inertias.max() - inertias.min() + 1e-10)
    
    # Combined score: prioritize silhouette, but consider elbow
    # Higher silhouette = better separation, lower inertia drop = diminishing returns
    combined_scores = silhouette_scores - 0.3 * normalized_inertias
    
    optimal_k = int(min_clusters + np.argmax(combined_scores))
    
    print(f"Cluster optimization: tested {min_clusters}-{max_clusters}, optimal={optimal_k}")
    print(f"Silhouette scores: {silhouette_scores}")
    
    return optimal_k

def balance_clusters(X: np.ndarray, labels: np.ndarray, min_size: int = 3) -> np.ndarray:
    """
    Rebalances clusters by reassigning tracks from oversized clusters to undersized ones.
    Ensures each cluster has at least min_size tracks.
    Returns adjusted cluster labels.
    """
    labels = labels.copy()
    unique_labels = np.unique(labels)
    
    # Count cluster sizes
    cluster_sizes = {label: np.sum(labels == label) for label in unique_labels}
    
    # Find undersized clusters
    undersized = [label for label, size in cluster_sizes.items() if size < min_size]
    
    if not undersized:
        return labels
    
    # Calculate cluster centroids
    centroids = {}
    for label in unique_labels:
        mask = labels == label
        centroids[label] = np.mean(X[mask], axis=0)
    
    # Reassign tracks from smallest clusters to nearest larger clusters
    for under_label in undersized:
        under_mask = labels == under_label
        under_indices = np.where(under_mask)[0]
        
        for idx in under_indices:
            track_features = X[idx]
            
            # Find nearest cluster that isn't undersized
            distances = {}
            for label in unique_labels:
                if label != under_label and cluster_sizes.get(label, 0) >= min_size:
                    dist = np.linalg.norm(track_features - centroids[label])
                    distances[label] = dist
            
            if distances:
                nearest_label = min(distances.keys(), key=lambda k: distances[k])
                labels[idx] = nearest_label
                cluster_sizes[under_label] -= 1
                cluster_sizes[nearest_label] += 1
    
    return labels

def cluster_tracks_adaptive(tracks: list, feature_keys: list, feature_weights: Optional[Dict[str, float]] = None, 
                            n_clusters: Optional[int] = None, min_cluster_size: int = 3) -> tuple:
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
    n_clusters: Optional[int] = Body(None, embed=True),
    min_cluster_size: int = Body(3, embed=True)
):
    """
    Accepts a JSON body with 'tracks' (list of track dicts with audio_features), 
    optional 'n_clusters' (auto-determined if None), and 'min_cluster_size' (default 3).
    
    Returns a list of cluster assignments for each track and the actual number of clusters created.
    
    The clustering algorithm automatically:
    - Determines optimal cluster count if not specified
    - Weights features appropriately (vibe features > technical features)
    - Ensures balanced cluster sizes
    - Removes outliers to separate clusters
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
    
    if len(tracks) < 6:
        # Too few tracks to meaningfully cluster
        return JSONResponse({
            "cluster_ids": [0] * len(tracks),
            "n_clusters": 1,
            "message": "Too few tracks to cluster meaningfully"
        })
    
    cluster_ids, actual_n_clusters = cluster_tracks_adaptive(
        tracks, 
        feature_keys, 
        feature_weights=feature_weights,
        n_clusters=n_clusters,
        min_cluster_size=min_cluster_size
    )
    
    return JSONResponse({
        "cluster_ids": cluster_ids,
        "n_clusters": actual_n_clusters
    })


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
        "Given the following average audio features and a few representative tracks, "
        "generate a short, creative, and descriptive 'vibe' name for this music cluster (this'll be the new playlists' name). Make them very descriptive and giving people an 'aha, yes that makes sense' moment when hearing the playlist name.\n"
        "Do not use the word 'cluster' or numbers. Keep it under 5 words.\n"
        f"Audio features: {cluster_features}\n"
        f"Representative tracks: {track_names}\n"
        "Name:"
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
