"""
High-level tests for Spotify OAuth2 PKCE flow endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_login_redirect():
    """
    Test that /auth/login returns a JSON response with Spotify authorization URL.
    """
    response = client.get("/auth/login")
    assert response.status_code == 200
    data = response.json()
    assert "redirect_url" in data
    assert "accounts.spotify.com/authorize" in data["redirect_url"]

def test_callback_missing_params():
    """
    Test /auth/callback with missing code/state returns error.
    """
    response = client.get("/auth/callback")
    assert response.status_code == 400
    assert "error" in response.json()