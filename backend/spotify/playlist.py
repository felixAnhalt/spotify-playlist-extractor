"""
Endpoints for fetching Spotify playlist tracks and their audio features, and clustering tracks by vibe.
"""

from fastapi import APIRouter, Request, HTTPException, status, Body
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import httpx
import asyncio
import json
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

def compute_reference_profile(tracks: list, feature_keys: list, feature_weights: dict) -> dict:
     """
     Computes weighted average audio features for a reference playlist.
     Uses feature weights to emphasize vibe-relevant features.
     """
     # First compute unweighted averages for each feature
     feature_values = {k: [] for k in feature_keys}
     
     for t in tracks:
         af = t.get("audio_features")
         if af is None:
             af = {}
         for k in feature_keys:
             feature_values[k].append(af.get(k, 0.0))
     
     # Compute mean for each feature
     avg_features = {}
     for k in feature_keys:
         if feature_values[k]:
             avg_features[k] = float(np.mean(feature_values[k]))
         else:
             avg_features[k] = 0.0
     
     # Apply weights to the averaged features
     weighted_avg = {}
     for k in feature_keys:
         weight = feature_weights.get(k, 1.0)
         weighted_avg[k] = avg_features[k] * weight
     
     return weighted_avg

def compute_fit_score(track_features: dict, avg_features: dict, feature_keys: list) -> float:
     """
     Computes how well a track fits the average profile (0-1 scale).
     Uses Euclidean distance in normalized feature space.
     """
     if not track_features:
         return 0.0
     
     distances = []
     for key in feature_keys:
         if key == "tempo":
             # Normalize tempo separately (typically 60-200 BPM)
             track_val = (track_features.get(key, 0) - 60) / 140 if track_features.get(key) else 0
             avg_val = (avg_features.get(key, 0) - 60) / 140 if avg_features.get(key) else 0
         else:
             # Other features already 0-1 scale
             track_val = track_features.get(key, 0)
             avg_val = avg_features.get(key, 0)
         
         distances.append(abs(float(track_val) - float(avg_val)))
     
     avg_distance = float(np.mean(distances))
     fit_score = max(0.0, 1.0 - avg_distance)  # Convert distance to similarity
     
     return fit_score

def fallback_algorithmic_selection(
     tracks_with_features: list,
     avg_features: dict,
     feature_keys: list,
     song_limit: int
) -> dict:
     """
     Fallback selection when LLM fails: picks songs with highest fit scores.
     Ensures diversity by limiting songs per artist.
     """
     # Compute fit scores for all tracks
     tracks_with_scores = []
     for t in tracks_with_features:
         score = compute_fit_score(t.get("audio_features") or {}, avg_features, feature_keys)
         # Safely extract artist name
         artists = t["track"].get("artists", [])
         artist_key = artists[0]["name"] if artists else "Unknown"
         tracks_with_scores.append({
             "track": t["track"],
             "audio_features": t.get("audio_features"),
             "fit_score": score,
             "artist": artist_key
         })
     
     # Sort by fit score (descending)
     tracks_with_scores.sort(key=lambda x: x["fit_score"], reverse=True)
     
     # Select top N with artist diversity constraint
     selected = []
     artist_counts: Dict[str, int] = {}
     max_per_artist = 3
     
     for t in tracks_with_scores:
         if len(selected) >= song_limit:
             break
         
         artist = t["artist"]
         current_count = artist_counts.get(artist, 0)
         if current_count < max_per_artist:
             selected.append({
                 "track": t["track"],
                 "audio_features": t["audio_features"],
                 "fit_score": round(t["fit_score"], 2)
             })
             artist_counts[artist] = current_count + 1
     
     return {
         "recommended_tracks": selected,
         "playlist_profile": avg_features,
         "llm_reasoning": "Algorithmic selection based on audio feature similarity (LLM unavailable)",
         "method": "algorithmic"
     }

async def select_songs_with_llm(
     tracks_with_features: list,
     new_playlist_name: str,
     avg_features: dict,
     feature_keys: list,
     song_limit: int
) -> dict:
     """
     Uses LLM to select the most fitting songs from a reference playlist
     for a new themed playlist.
     
     Considers:
     - Audio feature similarity to reference profile
     - Thematic fit with new playlist name
     - Artist/album diversity
     """
     # Limit tracks sent to LLM to avoid token overflow (max 80 tracks)
     tracks_subset = tracks_with_features[:80]
     
     # Prepare track summaries for LLM
     track_summaries = []
     for idx, t in enumerate(tracks_subset):
         af = t.get("audio_features") or {}
         # Safely extract artist name
         artists = t["track"].get("artists", [])
         artist_name = artists[0]["name"] if artists else "Unknown"
         # Safely extract album name
         album_obj = t["track"].get("album")
         album_name = album_obj.get("name", "Unknown") if isinstance(album_obj, dict) else "Unknown"
         track_summaries.append({
             "index": idx,
             "name": t["track"]["name"],
             "artist": artist_name,
             "album": album_name,
             "features": {k: round(af.get(k, 0), 2) for k in feature_keys}
         })
     
     # Build LLM prompt
     prompt = f"""You are an expert music curator creating the perfect playlist.

TASK: Select {song_limit} songs from the reference playlist that best fit the new playlist theme.

NEW PLAYLIST NAME: "{new_playlist_name}"

REFERENCE PLAYLIST AUDIO PROFILE (weighted averages):
{json.dumps({k: round(v, 2) for k, v in avg_features.items()}, indent=2)}

AVAILABLE TRACKS (max 50 shown):
{json.dumps(track_summaries[:50], indent=2)}

SELECTION CRITERIA:
1. Consider what "{new_playlist_name}" suggests (mood, activity, time of day, energy level)
2. Prioritize songs that match the reference playlist's sonic characteristics
3. Ensure diversity: max 2-3 songs per artist
4. Balance variety with coherence

RESPOND IN VALID JSON (no markdown):
{{
  "selected_indices": [0, 5, 12, ...],
  "reasoning": "Brief explanation of why these songs fit the theme"
}}

Select exactly {song_limit} songs (or fewer if insufficient matches)."""
     
     # Call OpenRouter API
     headers = {
         "Authorization": f"Bearer {OPENROUTER_API_KEY}",
         "Content-Type": "application/json"
     }
     
     payload = {
         "model": "xiaomi/mimo-v2-flash:free",
         "messages": [
             {
                 "role": "system",
                 "content": "You are a professional music curator. Always respond with valid JSON only."
             },
             {
                 "role": "user",
                 "content": prompt
             }
         ],
         "temperature": 0.75,
         "max_tokens": 800
     }
     
     async with httpx.AsyncClient(timeout=30.0) as client:
         try:
             resp = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
             
             if resp.status_code != 200:
                 print(f"LLM API error: {resp.status_code} - {resp.text}")
                 return fallback_algorithmic_selection(
                     tracks_with_features,
                     avg_features,
                     feature_keys,
                     song_limit
                 )
             
             result = resp.json()
         except Exception as e:
             print(f"LLM request failed: {str(e)}")
             return fallback_algorithmic_selection(
                 tracks_with_features,
                 avg_features,
                 feature_keys,
                 song_limit
             )
     
     # Parse LLM response (handle markdown code blocks)
     llm_content = result["choices"][0]["message"]["content"].strip()
     llm_content = llm_content.replace("```json", "").replace("```", "").strip()
     
     try:
         llm_output = json.loads(llm_content)
     except json.JSONDecodeError:
         print(f"Failed to parse LLM response: {llm_content}")
         return fallback_algorithmic_selection(
             tracks_with_features,
             avg_features,
             feature_keys,
             song_limit
         )
     
     # Build response with selected tracks
     selected_indices = llm_output.get("selected_indices", [])
     recommended_tracks = []
     
     for idx in selected_indices:
         if idx < len(tracks_with_features):
             track = tracks_with_features[idx]
             fit_score = compute_fit_score(
                 track.get("audio_features") or {},
                 avg_features,
                 feature_keys
             )
             
             recommended_tracks.append({
                 "track": track["track"],
                 "audio_features": track.get("audio_features"),
                 "fit_score": round(fit_score, 2)
             })
     
     return {
         "recommended_tracks": recommended_tracks,
         "playlist_profile": avg_features,
         "llm_reasoning": llm_output.get("reasoning", ""),
         "method": "llm"
     }

@router.post("/playlist/generate-from-reference")
async def generate_playlist_from_reference(request: Request):
     """
     Generates a curated playlist by analyzing a reference playlist's audio features
     and selecting the most fitting songs based on a new playlist name/theme.
     
     Uses LLM to intelligently select songs that match both:
     1. The reference playlist's sonic characteristics (audio features)
     2. The thematic context of the new playlist name
     
     Request body:
     {
         "state": "oauth_state_token",
         "reference_playlist_id": "37i9dQZF1DXcBWIGoYBM5M",
         "new_playlist_name": "Late Night Coding",
         "song_limit": 25  // optional, default 20
     }
     """
     body = await request.json()
     state = body.get("state")
     reference_playlist_id = body.get("reference_playlist_id")
     new_playlist_name = body.get("new_playlist_name")
     song_limit = body.get("song_limit", 20)
     
     # Validation
     if not all([state, reference_playlist_id, new_playlist_name]):
         raise HTTPException(status_code=400, detail="Missing required fields: state, reference_playlist_id, new_playlist_name")
     
     tokens = session_store.get_tokens(state)
     if not tokens or "access_token" not in tokens:
         raise HTTPException(status_code=401, detail="No valid access token")
     
     access_token = tokens["access_token"]
     playlist_id = extract_playlist_id(reference_playlist_id)
     
     try:
         # 1. Fetch reference playlist tracks + audio features
         tracks = await fetch_all_tracks(access_token, playlist_id)
         track_ids = [item["track"]["id"] for item in tracks if item.get("track") and item["track"].get("id")]
         
         if len(track_ids) < 10:
             raise HTTPException(status_code=400, detail="Reference playlist must have at least 10 tracks")
         
         audio_features = await fetch_audio_features(access_token, track_ids)
         
         tracks_with_features = []
         for item in tracks:
             track = item.get("track")
             if not track or not track.get("id"):
                 continue
             tracks_with_features.append({
                 "track": track,
                 "audio_features": audio_features.get(track["id"])
             })
         
         # 2. Analyze reference playlist audio profile
         feature_keys = [
             "danceability", "energy", "valence", "acousticness",
             "instrumentalness", "liveness", "speechiness", "tempo"
         ]
         
         feature_weights = {
             "valence": 1.5,
             "energy": 1.4,
             "danceability": 1.3,
             "acousticness": 1.2,
             "instrumentalness": 1.0,
             "tempo": 0.6,
             "speechiness": 0.8,
             "liveness": 0.7
         }
         
         avg_features = compute_reference_profile(tracks_with_features, feature_keys, feature_weights)
         
         # 3. Call LLM to select fitting songs
         recommendations = await select_songs_with_llm(
             tracks_with_features,
             new_playlist_name,
             avg_features,
             feature_keys,
             song_limit
         )
         
         return JSONResponse(recommendations)
     
     except HTTPException:
         raise
     except Exception as e:
         print(f"Error in generate_playlist_from_reference: {str(e)}")
         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

