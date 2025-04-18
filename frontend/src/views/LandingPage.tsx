// LandingPage.tsx
// Landing page with "Login with Spotify" button.
// Initiates OAuth flow by calling backend login endpoint.

import * as React from "react";
import {login} from "../api/backendConnector";

/**
 * Landing page component.
 * Renders a "Login with Spotify" button that starts the OAuth flow.
 */
function LandingPage(): React.ReactElement {
  /**
   * Handles login button click.
   * Calls backend /login endpoint and redirects to Spotify's auth page.
   */
  const handleLogin = async (): Promise<void> => {
    try {
      // Call backend login endpoint to get Spotify auth URL
      const response = await login();
      if (!response) throw new Error("Failed to initiate login");
      const { redirect_url } = response.data
      window.location.href = redirect_url;
    } catch (err: any) {
      alert("Login failed: " + (err?.message ?? "Unknown error"));
    }
  };

  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        marginTop: "10vh",
      }}
    >
      <h1>Spotify Playlist Organizer</h1>
      <button
        onClick={handleLogin}
        style={{
          background: "#1DB954",
          color: "#fff",
          border: "none",
          borderRadius: "24px",
          padding: "1em 2em",
          fontSize: "1.2em",
          cursor: "pointer",
          marginTop: "2em",
        }}
        aria-label="Login with Spotify"
      >
        Login with Spotify
      </button>
    </main>
  );
}

export default LandingPage;
