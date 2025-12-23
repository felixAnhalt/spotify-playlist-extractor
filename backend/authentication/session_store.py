"""
Persistent session and token store for Spotify OAuth2 PKCE flow.
Persists to disk only in local development.
"""

from typing import Dict, Optional
import json
import os
from pathlib import Path
from config import config

# Storage file path
_storage_dir = Path(__file__).parent.parent / ".session_data"
_storage_file = _storage_dir / "sessions.json"

# Stores state -> code_verifier mapping
_state_verifier: Dict[str, str] = {}

# Stores state -> tokens mapping
_state_tokens: Dict[str, dict] = {}

def _load_from_disk() -> None:
    """
    Load session data from disk on startup (local dev only).
    """
    if not config.IS_LOCAL:
        return
    
    global _state_verifier, _state_tokens
    if _storage_file.exists():
        try:
            with open(_storage_file, 'r') as f:
                data = json.load(f)
                _state_verifier = data.get('state_verifier', {})
                _state_tokens = data.get('state_tokens', {})
        except (json.JSONDecodeError, IOError):
            pass

def _save_to_disk() -> None:
    """
    Save session data to disk (local dev only).
    """
    if not config.IS_LOCAL:
        return
    
    _storage_dir.mkdir(exist_ok=True)
    data = {
        'state_verifier': _state_verifier,
        'state_tokens': _state_tokens
    }
    with open(_storage_file, 'w') as f:
        json.dump(data, f, indent=2)

# Load existing sessions on module import
_load_from_disk()

def save_state(state: str, code_verifier: str) -> None:
    """
    Save the state and code_verifier for a login attempt.
    """
    _state_verifier[state] = code_verifier
    _save_to_disk()

def get_code_verifier(state: str) -> Optional[str]:
    """
    Retrieve the code_verifier for a given state.
    """
    return _state_verifier.get(state)

def save_tokens(state: str, tokens: dict) -> None:
    """
    Save tokens for a given state.
    """
    _state_tokens[state] = tokens
    _save_to_disk()

def get_tokens(state: str) -> Optional[dict]:
    """
    Retrieve tokens for a given state.
    """
    return _state_tokens.get(state)