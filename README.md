# Spotify Playlist Extractor

"My playlist is too big and I wanna listen to music based on vibe" - this tool solves that.

## Overview

A full-stack application that helps users extract and manage subsets of their Spotify playlists based on vibes and preferences. Built with React/TypeScript frontend and FastAPI/Python backend.

## Architecture

```
spotify-playlist-extractor/
├── backend/          # FastAPI service (Python)
│   ├── authentication/   # OAuth & session management
│   ├── spotify/         # Spotify API integration
│   └── config/          # Configuration management
├── frontend/         # React SPA (TypeScript)
│   └── src/
│       ├── views/       # Page components
│       ├── auth/        # OAuth state management
│       └── api/         # Backend connector
```

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Spotify Developer Account (for API credentials)

### Backend Setup
```bash
cd backend
cp .env.example .env
# Edit .env with your Spotify credentials
pip install -r requirements.txt
./start.sh
```
Backend runs on `http://localhost:8000`

### Frontend Setup
```bash
cd frontend
pnpm install
pnpm run dev
```
Frontend runs on `http://localhost:5173`

## Development

See detailed documentation:
- [Backend README](./backend/README.md) - API endpoints, testing, architecture
- [Frontend README](./frontend/README.md) - Components, state management, build process

## Project Standards

- **Code Style**: Follow AGENTS.md guidelines for Python (snake_case, type hints) and TypeScript (PascalCase components, explicit types)
- **Testing**: Backend uses pytest, frontend uses Vitest
- **Max Method Length**: 20 lines of logic
- **Error Handling**: HTTPException for API errors, try-catch with user-facing alerts in frontend

## Testing

```bash
# Backend tests
cd backend && pytest

# Frontend tests (if configured)
cd frontend && npx vitest
```

## Scripts

**Backend**
- `./start.sh` - Start dev server
- `pytest` - Run tests
- `uvicorn main:app --reload` - Alternative dev server

**Frontend**
- `pnpm run dev` - Start dev server
- `pnpm run build` - Production build
- `pnpm run lint` - Run ESLint

## License

See [LICENSE](./LICENSE)
