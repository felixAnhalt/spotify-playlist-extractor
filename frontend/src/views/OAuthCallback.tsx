// OAuthCallback.tsx
// Handles the OAuth callback from Spotify and redirects to the organize page.

import * as React from "react";
import { useNavigate, useLocation } from "react-router";
import { callback } from "../api/backendConnector";
import { useOAuthState } from "../auth/OAuthStateContext";
import Container from "../components/Container";

/**
 * OAuthCallback component.
 * Handles the OAuth callback, verifies authentication, and redirects to organize page.
 */
function OAuthCallback(): React.ReactElement {
  const navigate = useNavigate();
  const location = useLocation();
  const { setState } = useOAuthState();
  const hasRun = React.useRef(false);

  React.useEffect(() => {
    /**
     * Handles the OAuth callback by notifying the backend and redirecting.
     */
    async function handleCallback(): Promise<void> {
      if (hasRun.current) return;
      hasRun.current = true;

      try {
        // Notify backend with query params (e.g., code, state)
        const search = location.search;
        const state = new URLSearchParams(search).get("state");
        if (state) {
          setState(state);
          localStorage.setItem("spotify_oauth_state", state);
        }
        const response = await callback(search);
        if (!response) throw new Error("OAuth callback failed");
        // On success, redirect to organize page
        navigate("/organize");
      } catch (err: any) {
        alert("OAuth callback error: " + (err?.message ?? "Unknown error"));
      }
    }
    handleCallback();
  }, [location.search, navigate, setState]);

  return (
    <main className="min-h-screen bg-gradient-to-br from-primary-50 via-accent-50 to-secondary-50 flex items-center justify-center">
      <Container>
        <div className="flex flex-col items-center text-center gap-8 bg-primary-100 p-12 rounded-xl border-primary-700 shadow-cartoon border-cartoon-3">
          <div className="text-8xl animate-bounce" style={{ animationDuration: '1s' }}>🎵</div>
          <h2 className="text-4xl font-black text-primary-900 m-0 font-mono-bold text-shadow-cartoon-sm letter-spacing-cartoon-lg">
            LOGGING IN...
          </h2>
          <p className="text-xl text-primary-800 m-0 font-medium">
            Please wait while we connect to Spotify! 🎶
          </p>
          <div className="flex gap-2 mt-4">
            <div className="w-3 h-3 bg-accent-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-3 h-3 bg-secondary-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-3 h-3 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
        </div>
      </Container>
    </main>
  );
}

export default OAuthCallback;
