"""
High-level tests for Spotify OAuth2 PKCE flow endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_login_redirect():
    """
    Test that /auth/login redirects to Spotify authorization endpoint.
    """
    response = client.get("/auth/login", allow_redirects=False)
    assert response.status_code == 307 or response.status_code == 302
    assert "accounts.spotify.com/authorize" in response.headers["location"]

def test_callback_missing_params():
    """
    Test /auth/callback with missing code/state returns error.
    """
    response = client.get("/auth/callback")
    assert response.status_code == 400
    assert "error" in response.json()