# Backend - Spotify Playlist Extractor

FastAPI-based backend service handling Spotify OAuth, playlist management, and AI-powered playlist analysis.

## Architecture

```
backend/
├── authentication/
│   ├── auth.py           # OAuth flows & endpoints
│   └── session_store.py  # In-memory session management
├── spotify/
│   └── playlist.py       # Spotify API integration
├── config/
│   └── config.py         # Environment configuration
├── tests/                # Pytest test suite
├── main.py               # FastAPI app entry point
└── requirements.txt      # Python dependencies
```

## Setup

### 1. Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
OPENROUTER_API_KEY="your_openrouter_key"
OPENROUTER_API_URL="https://openrouter.ai/api/v1/chat/completions"
SPOTIFY_CLIENT_ID="your_spotify_client_id"
SPOTIFY_REDIRECT_URI="http://localhost:5173/auth/callback"
SPOTIFY_SCOPE="user-read-private user-read-email"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `httpx` - Async HTTP client for Spotify API
- `scikit-learn` - ML for playlist analysis
- `python-dotenv` - Environment management
- `pytest` - Testing framework
- `numpy` - Numerical operations

### 3. Start Development Server

```bash
./start.sh
```

Or directly:
```bash
uvicorn main:app --reload
```

Server runs on `http://localhost:8000`

## API Endpoints

### Authentication
- `GET /auth/login` - Initiate Spotify OAuth flow
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/logout` - Clear session

### Playlist Management
- `GET /playlists` - Fetch user playlists
- `POST /playlists/extract` - Extract subset based on criteria
- `GET /playlists/{id}` - Get playlist details

### Health
- `GET /health` - Service health check

## Testing

Run all tests:
```bash
pytest
```

Run specific test file:
```bash
pytest tests/test_auth.py
```

Run specific test:
```bash
pytest tests/test_auth.py::test_login_redirect
```

With coverage:
```bash
pytest --cov=. --cov-report=html
```

## Code Style

### Imports
1. Standard library
2. FastAPI/third-party
3. Local relative imports

### Type Hints
Always use type hints on all functions:
```python
from typing import Optional, List, Dict, Any

async def get_playlist(user_id: str, playlist_id: str) -> Optional[Dict[str, Any]]:
    pass
```

### Naming Conventions
- `snake_case` - Functions and variables
- `UPPER_SNAKE_CASE` - Constants
- `_prefix` - Private functions

### Error Handling
```python
from fastapi import HTTPException

if not user_session:
    raise HTTPException(status_code=401, detail="Not authenticated")
```

### Endpoint Structure
```python
@app.post("/endpoint")
async def endpoint_handler(request: RequestModel) -> JSONResponse:
    """Docstring describing endpoint"""
    # Parse body
    data = await request.json()
    
    # Validate
    if not data.get("required_field"):
        raise HTTPException(status_code=400, detail="Missing field")
    
    # Retrieve session
    session = session_store.get(session_id)
    
    # Business logic
    result = await process_data(data)
    
    # Return response
    return JSONResponse({"status": "success", "data": result})
```

## Session Management

In-memory session store (see `authentication/session_store.py`):
- Sessions stored with UUID keys
- Contains access tokens, refresh tokens, user info
- Auto-cleanup on logout

## Spotify API Integration

See `spotify/playlist.py` for:
- OAuth token exchange
- Playlist fetching
- Track analysis
- API error handling

## Configuration

`config/config.py` loads environment variables:
```python
from config.config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_REDIRECT_URI,
    OPENROUTER_API_KEY
)
```

## Common Tasks

### Add New Endpoint
1. Define route in `main.py` or create new module
2. Add type hints for request/response
3. Implement validation and error handling
4. Write tests in `tests/`

### Debug OAuth Flow
```bash
# Check session contents
print(f"Session: {session_store.get(session_id)}")

# Test redirect URI matches Spotify app settings
# Verify SPOTIFY_CLIENT_ID is correct
```

### Update Dependencies
```bash
pip freeze > requirements.txt
```

## Troubleshooting

**Port already in use:**
```bash
lsof -ti:8000 | xargs kill -9
```

**Import errors:**
```bash
# Run from backend/ directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**OAuth callback fails:**
- Verify `SPOTIFY_REDIRECT_URI` matches Spotify app settings exactly
- Check frontend is running on correct port (5173)
- Ensure `SPOTIFY_CLIENT_ID` is valid

## Performance

- Uses `async`/`await` throughout for concurrency
- Session store is in-memory (consider Redis for production)
- HTTP client connection pooling via `httpx`

## Security

- OAuth tokens stored server-side only
- Session IDs are UUIDs
- No sensitive data in client responses
- CORS configured for frontend origin only
