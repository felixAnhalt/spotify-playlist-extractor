"""
In-memory session and token store for Spotify OAuth2 PKCE flow.
"""

from typing import Dict, Optional

# Stores state -> code_verifier mapping
_state_verifier: Dict[str, str] = {}

# Stores state -> tokens mapping
_state_tokens: Dict[str, dict] = {}

def save_state(state: str, code_verifier: str) -> None:
    """
    Save the state and code_verifier for a login attempt.
    """
    _state_verifier[state] = code_verifier

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

def get_tokens(state: str) -> Optional[dict]:
    """
    Retrieve tokens for a given state.
    """
    return _state_tokens.get(state)