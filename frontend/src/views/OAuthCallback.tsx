// OAuthCallback.tsx
// Handles the OAuth callback from Spotify and redirects to the logged-in confirmation.

import * as React from "react";
import {useNavigate, useLocation} from "react-router";
import {callback} from "../api/backendConnector";


/**
 * OAuthCallback component.
 * Handles the OAuth callback, verifies authentication, and redirects to confirmation.
 */
function OAuthCallback(): React.ReactElement {
  const navigate = useNavigate();
  const location = useLocation();

  React.useEffect(() => {
    /**
     * Handles the OAuth callback by notifying the backend and redirecting.
     */
    async function handleCallback(): Promise<void> {
      try {
        // Notify backend with query params (e.g., code, state)
        const search = location.search;
        const response = await callback(search);
        if (!response) throw new Error("OAuth callback failed");
        // On success, redirect to logged-in confirmation
        navigate("/logged-in");
      } catch (err: any) {
        alert("OAuth callback error: " + (err?.message ?? "Unknown error"));
      }
    }
    handleCallback();
  }, [location.search, navigate]);

  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        marginTop: "10vh",
      }}
    >
      <h2>Logging you in with Spotify...</h2>
    </main>
  );
}

export default OAuthCallback;
