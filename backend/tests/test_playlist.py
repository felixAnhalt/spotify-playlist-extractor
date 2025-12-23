"""
High-level tests for playlist endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_playlist_tracks_missing_params():
    """
    Test /playlist/tracks with missing params returns error.
    """
    response = client.post("/playlist/tracks", json={})
    assert response.status_code == 400
    assert "detail" in response.json()

def test_playlist_tracks_unauthorized():
    """
    Test /playlist/tracks with invalid state returns unauthorized.
    """
    response = client.post("/playlist/tracks", json={"playlist_id_or_url": "fakeid", "state": "invalid"})
    assert response.status_code == 401


def test_playlist_cluster_basic():
    """
    Test /playlist/cluster returns cluster assignments for valid input.
    """
    tracks = [
        {"audio_features": {"danceability": 0.5, "energy": 0.7, "valence": 0.6, "acousticness": 0.1, "instrumentalness": 0.0, "liveness": 0.2, "speechiness": 0.05, "tempo": 120}},
        {"audio_features": {"danceability": 0.8, "energy": 0.9, "valence": 0.7, "acousticness": 0.05, "instrumentalness": 0.0, "liveness": 0.1, "speechiness": 0.04, "tempo": 130}},
        {"audio_features": {"danceability": 0.2, "energy": 0.3, "valence": 0.2, "acousticness": 0.8, "instrumentalness": 0.1, "liveness": 0.3, "speechiness": 0.06, "tempo": 90}},
        {"audio_features": {"danceability": 0.3, "energy": 0.4, "valence": 0.3, "acousticness": 0.7, "instrumentalness": 0.2, "liveness": 0.4, "speechiness": 0.07, "tempo": 100}}
    ]
    response = client.post("/playlist/cluster", json={"tracks": tracks, "n_clusters": 2})
    assert response.status_code == 200
    data = response.json()
    assert "cluster_ids" in data
    assert len(data["cluster_ids"]) == len(tracks)



def test_playlist_cluster_missing_tracks():
    """
    Test /playlist/cluster with missing tracks returns error.
    """
    response = client.post("/playlist/cluster", json={})
    assert response.status_code == 422
    assert "detail" in response.json()

def test_create_playlists_flow(monkeypatch):
    """
    High-level test for /playlist/create endpoint: creates playlists and adds tracks.
    """
    # Patch Spotify API calls to avoid real HTTP requests
    class DummyResp:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
        def json(self):
            return self._json

    async def dummy_get(url, headers=None):
        if url.endswith("/me"):
            return DummyResp(200, {"id": "user123"})
        return DummyResp(404, {})
    async def dummy_post(url, headers=None, json=None):
        if "users/user123/playlists" in url:
            return DummyResp(201, {"id": "plid1", "external_urls": {"spotify": "https://open.spotify.com/playlist/plid1"}})
        if "playlists/plid1/tracks" in url:
            return DummyResp(201, {})
        return DummyResp(404, {})

    import spotify.playlist as playlist_mod
    monkeypatch.setattr(playlist_mod.httpx.AsyncClient, "get", staticmethod(dummy_get))
    monkeypatch.setattr(playlist_mod.httpx.AsyncClient, "post", staticmethod(dummy_post))

    # Patch session_store to provide a fake token
    monkeypatch.setattr(playlist_mod.session_store, "get_tokens", lambda state: {"access_token": "FAKE_TOKEN"})

    client = TestClient(app)
    payload = {
        "playlists": [
            {"name": "Test Playlist", "description": "desc", "tracks": ["t1", "t2"]}
        ],
        "state": "dummy_state",
        "public": True
    }
    resp = client.post("/playlist/create", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "created" in data
    assert data["created"][0]["name"] == "Test Playlist"
    assert data["created"][0]["url"].startswith("https://open.spotify.com/playlist/")


def test_playlist_cluster_names(monkeypatch):
    """
    Test /playlist/cluster-names returns names for valid input.
    """
    tracks = [
        {"name": "Track A", "audio_features": {"danceability": 0.5, "energy": 0.7, "valence": 0.6, "acousticness": 0.1, "instrumentalness": 0.0, "liveness": 0.2, "speechiness": 0.05, "tempo": 120}},
        {"name": "Track B", "audio_features": {"danceability": 0.8, "energy": 0.9, "valence": 0.7, "acousticness": 0.05, "instrumentalness": 0.0, "liveness": 0.1, "speechiness": 0.04, "tempo": 130}},
        {"name": "Track C", "audio_features": {"danceability": 0.2, "energy": 0.3, "valence": 0.2, "acousticness": 0.8, "instrumentalness": 0.1, "liveness": 0.3, "speechiness": 0.06, "tempo": 90}},
        {"name": "Track D", "audio_features": {"danceability": 0.3, "energy": 0.4, "valence": 0.3, "acousticness": 0.7, "instrumentalness": 0.2, "liveness": 0.4, "speechiness": 0.07, "tempo": 100}}
    ]
    cluster_ids = [0, 0, 1, 1]
    # Patch LLM call to avoid real API
    async def fake_get_cluster_vibe_name(features, reps):
        return "Test Vibe"
    import spotify.playlist as playlist_mod
    monkeypatch.setattr(playlist_mod, "get_cluster_vibe_name", fake_get_cluster_vibe_name)
    response = client.post("/playlist/cluster-names", json={"tracks": tracks, "cluster_ids": cluster_ids})
    assert response.status_code == 200
    data = response.json()
    assert "cluster_names" in data
    assert set(data["cluster_names"].values()) == {"Test Vibe"}


def test_playlist_cluster_names_missing():
    """
    Test /playlist/cluster-names with missing params returns error.
    """
    response = client.post("/playlist/cluster-names", json={})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_fetch_audio_features_reccobeats_schema(monkeypatch):
    """
    Test that fetch_audio_features correctly parses ReccoBeats API response schema.
    ReccoBeats returns {"content": [...]} not {"audio_features": [...]}.
    """
    import spotify.playlist as playlist_mod
    
    # Mock ReccoBeats response with correct schema
    reccobeats_response = {
        "content": [
            {
                "id": "track1",
                "href": "https://open.spotify.com/track/track1",
                "isrc": "USRC12345678",
                "acousticness": 0.123,
                "danceability": 0.456,
                "energy": 0.789,
                "instrumentalness": 0.012,
                "key": 5,
                "liveness": 0.234,
                "loudness": -5.5,
                "mode": 1,
                "speechiness": 0.067,
                "tempo": 120.5,
                "valence": 0.678
            },
            {
                "id": "track2",
                "href": "https://open.spotify.com/track/track2",
                "isrc": "USRC87654321",
                "acousticness": 0.321,
                "danceability": 0.654,
                "energy": 0.987,
                "instrumentalness": 0.210,
                "key": 7,
                "liveness": 0.432,
                "loudness": -6.2,
                "mode": 0,
                "speechiness": 0.089,
                "tempo": 128.3,
                "valence": 0.876
            }
        ]
    }
    
    class DummyResp:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
            self.headers = {}
        def json(self):
            return self._json
    
    async def dummy_get(url, params=None, headers=None):
        return DummyResp(200, reccobeats_response)
    
    class DummyClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, params=None):
            return await dummy_get(url, params)
    
    monkeypatch.setattr(playlist_mod.httpx, "AsyncClient", lambda timeout=None: DummyClient())
    
    import asyncio
    features = asyncio.run(playlist_mod.fetch_audio_features("fake_token", ["track1", "track2"]))
    
    # Verify features were extracted correctly
    assert "track1" in features
    assert "track2" in features
    assert features["track1"]["acousticness"] == 0.123
    assert features["track1"]["danceability"] == 0.456
    assert features["track2"]["tempo"] == 128.3
    assert features["track2"]["valence"] == 0.876


def test_compute_cluster_averages_handles_none_features():
    """
    Test that compute_cluster_averages handles tracks with None audio_features gracefully.
    """
    import spotify.playlist as playlist_mod
    
    tracks = [
        {"name": "Track A", "audio_features": {"danceability": 0.5, "energy": 0.7}},
        {"name": "Track B", "audio_features": None},  # Missing features
        {"name": "Track C", "audio_features": {"danceability": 0.8, "energy": 0.9}},
    ]
    cluster_ids = [0, 0, 1]
    feature_keys = ["danceability", "energy"]
    
    # Should not raise AttributeError
    result = playlist_mod.compute_cluster_averages(tracks, feature_keys, cluster_ids)
    
    assert 0 in result
    assert 1 in result
    # Cluster 0 has Track A (valid) and Track B (None) - should average with 0.0 for missing
    assert result[0]["features"]["danceability"] == pytest.approx(0.25, abs=0.01)  # (0.5 + 0.0) / 2
    assert result[0]["features"]["energy"] == pytest.approx(0.35, abs=0.01)  # (0.7 + 0.0) / 2
    # Cluster 1 has Track C
    assert result[1]["features"]["danceability"] == pytest.approx(0.8, abs=0.01)
    assert result[1]["features"]["energy"] == pytest.approx(0.9, abs=0.01)
