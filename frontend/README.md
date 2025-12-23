# Frontend - Spotify Playlist Extractor

React + TypeScript SPA for managing and extracting Spotify playlists based on vibes.

## Architecture

```
frontend/
├── src/
│   ├── views/                    # Page components
│   │   ├── LandingPage.tsx       # Entry point / login
│   │   ├── OAuthCallback.tsx     # OAuth redirect handler
│   │   ├── LoggedIn.tsx          # Main authenticated view
│   │   ├── PlaylistEditor.tsx    # Playlist manipulation UI
│   │   └── PlaylistEditorContainer.tsx
│   ├── auth/
│   │   └── OAuthStateContext.tsx # Authentication state management
│   ├── api/
│   │   └── backendConnector.ts   # Backend API client
│   ├── App.tsx                   # Root component
│   ├── routes.tsx                # React Router config
│   └── main.tsx                  # Entry point
├── public/                       # Static assets
├── index.html                    # HTML template
├── vite.config.js                # Vite configuration
└── package.json
```

## Setup

### 1. Install Dependencies

```bash
pnpm install
```

**Key Dependencies:**
- `react` 19.1.0 - UI library
- `react-router-dom` 7.5.1 - Client-side routing
- `axios` 1.8.4 - HTTP client
- `@hello-pangea/dnd` 18.0.1 - Drag-and-drop for playlists
- `vite` 6.3.1 - Build tool & dev server

### 2. Start Development Server

```bash
pnpm run dev
```

Runs on `http://localhost:5173`

## Scripts

```bash
pnpm run dev       # Start dev server with HMR
pnpm run build     # Production build to dist/
pnpm run lint      # Run ESLint
pnpm run preview   # Preview production build
```

## Project Structure

### Views (Pages)
- **LandingPage** - Unauthenticated landing with login CTA
- **OAuthCallback** - Handles Spotify OAuth redirect, extracts session
- **LoggedIn** - Main dashboard after authentication
- **PlaylistEditor** - Interactive playlist editing with drag-and-drop
- **PlaylistEditorContainer** - Container component managing editor state

### Context
- **OAuthStateContext** - Global authentication state provider

### API Layer
- **backendConnector.ts** - Axios-based API client for backend communication

### Routing
Defined in `routes.tsx`:
```tsx
/                    → LandingPage
/auth/callback       → OAuthCallback
/logged-in           → LoggedIn
/playlist-editor     → PlaylistEditorContainer
```

## Code Style

### Import Order
1. React imports
2. Third-party libraries
3. React Router
4. Local API/utils
5. Components
6. Context/hooks

Example:
```tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { backendApi } from '../api/backendConnector';
import PlaylistEditor from './PlaylistEditor';
import { useOAuthState } from '../auth/OAuthStateContext';
```

### Type Definitions
Always use explicit interfaces:
```tsx
interface PlaylistEditorProps {
  playlists: Playlist[];
  onSave: (playlist: Playlist) => void;
  currentUser: string | null;
}

interface Playlist {
  id: string;
  name: string;
  tracks: Track[];
}
```

### Naming Conventions
- `PascalCase` - Components, interfaces, types
- `camelCase` - Functions, variables, props
- `UPPER_SNAKE_CASE` - Constants

### Component Structure
```tsx
interface ComponentProps {
  propName: string;
}

export const Component: React.FC<ComponentProps> = ({ propName }) => {
  // State declarations
  const [state, setState] = useState<string>('');
  
  // Hooks
  const navigate = useNavigate();
  
  // Effects
  useEffect(() => {
    // Effect logic
  }, []);
  
  // Handlers
  const handleClick = () => {
    // Handler logic
  };
  
  // JSX
  return (
    <div>
      {/* Render */}
    </div>
  );
};
```

### Error Handling
```tsx
try {
  const response = await backendApi.get('/endpoint');
  setData(response.data);
} catch (err: any) {
  console.error('Failed to fetch:', err);
  alert(err?.response?.data?.detail || 'An error occurred');
}
```

Use optional chaining:
```tsx
const userName = user?.profile?.name ?? 'Guest';
```

## State Management

### Context Pattern
Authentication uses React Context (see `auth/OAuthStateContext.tsx`):
```tsx
import { useOAuthState } from '../auth/OAuthStateContext';

const { sessionId, setSessionId } = useOAuthState();
```

### Local State
Components use `useState` for local UI state:
```tsx
const [playlists, setPlaylists] = useState<Playlist[]>([]);
```

## API Integration

Backend connector at `api/backendConnector.ts`:
```tsx
import { backendApi } from '../api/backendConnector';

// GET request
const response = await backendApi.get('/playlists');

// POST request
const response = await backendApi.post('/playlists/extract', {
  playlistId: 'abc123',
  criteria: { vibe: 'chill' }
});
```

Base URL configured in connector: `http://localhost:8000`

## Testing

Run tests with Vitest:
```bash
npx vitest
```

Test files: `*.test.tsx`

Uses Testing Library:
```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('renders playlist editor', () => {
  render(<PlaylistEditor playlists={[]} onSave={() => {}} />);
  expect(screen.getByRole('heading')).toBeInTheDocument();
});
```

### Accessibility Testing
Prefer accessibility queries:
```tsx
screen.getByRole('button', { name: /save/i })
screen.getByLabelText('Playlist name')
screen.getByText('Loading...')
```

## Drag and Drop

Uses `@hello-pangea/dnd` for playlist reordering:
```tsx
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';

<DragDropContext onDragEnd={handleDragEnd}>
  <Droppable droppableId="tracks">
    {(provided) => (
      <div {...provided.droppableProps} ref={provided.innerRef}>
        {tracks.map((track, index) => (
          <Draggable key={track.id} draggableId={track.id} index={index}>
            {/* Track component */}
          </Draggable>
        ))}
      </div>
    )}
  </Droppable>
</DragDropContext>
```

## Vite Configuration

Hot Module Replacement (HMR) enabled via `@vitejs/plugin-react`.

### Build Output
```bash
pnpm run build  # Creates dist/ folder
```

### Preview Production Build
```bash
pnpm run preview  # Serves dist/ locally
```

## Environment Variables

Create `.env` for environment-specific config:
```env
VITE_API_BASE_URL=http://localhost:8000
```

Access in code:
```tsx
const apiUrl = import.meta.env.VITE_API_BASE_URL;
```

## Common Tasks

### Add New Page
1. Create component in `src/views/`
2. Add route in `routes.tsx`
3. Update navigation in relevant components

### Add API Endpoint
1. Add method to `backendConnector.ts`
2. Call from component with proper error handling
3. Update types/interfaces

### Style Components
CSS modules or inline styles (currently using `App.css`, `index.css`)

## Troubleshooting

**Port 5173 in use:**
```bash
lsof -ti:5173 | xargs kill -9
```

**TypeScript errors:**
```bash
npx tsc --noEmit  # Type check without building
```

**OAuth callback fails:**
- Check backend is running on port 8000
- Verify Spotify app redirect URI is `http://localhost:5173/auth/callback`
- Inspect browser console for errors

**Build fails:**
```bash
rm -rf node_modules package-lock.json
pnpm install
```

## Performance

- Vite provides fast HMR via native ESM
- React 19 uses automatic batching
- Use `React.memo()` for expensive components
- Lazy load routes with `React.lazy()`

## Browser Support

Modern browsers supporting ES modules:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
