# Agent Guidelines - Spotify Playlist Extractor

## Commands
- **Frontend dev**: `cd frontend && npm run dev` | **build**: `npm run build` | **lint**: `npm run lint`
- **Backend dev**: `cd backend && ./start.sh` or `uvicorn main:app --reload`
- **Test backend**: `cd backend && pytest` | **single test**: `pytest tests/test_auth.py::test_login_redirect`
- **Test frontend**: No npm script configured. Run tests with `npx vitest` if needed.

## Code Style

### TypeScript/React
- **Imports**: (1) React, (2) third-party libs, (3) router, (4) local API/utils, (5) components, (6) context
- **Types**: Always use explicit interfaces for props/state. Union types for nullables (`string | null`). Avoid `any` except for untyped external data.
- **Naming**: PascalCase components/interfaces, camelCase functions/vars, UPPER_SNAKE_CASE constants
- **Components**: Presentational use props, containers use hooks/context. State → handlers → JSX.
- **Error handling**: `try-catch` with `err: any`, optional chaining (`?.`), user-facing alerts

### Python/FastAPI
- **Imports**: (1) stdlib, (2) FastAPI/third-party, (3) local relative imports
- **Types**: Use type hints on all functions. `Optional[T]` for nullables, `List[Dict[str, Any]]` for complex structures.
- **Naming**: snake_case functions/vars, UPPER_SNAKE_CASE constants, `_prefix` for private
- **Error handling**: `HTTPException` for API errors, print statements for debugging, early returns for validation
- **Endpoints**: Docstring → parse body → validate → retrieve session → business logic → JSONResponse

## Standards
- Max 20 lines per method (logic). Separate concerns. No speculative abstractions.
- Test with accessibility queries (`getByRole`, `getByLabelText`). Mock external dependencies.
- Use `async`/`await` consistently. FastAPI endpoints always `async def`.
