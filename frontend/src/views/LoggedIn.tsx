// LoggedIn.tsx
// Displays a simple confirmation after successful Spotify login.

import * as React from "react";

/**
 * LoggedIn component.
 * Shows a confirmation message after successful authentication.
 */
function LoggedIn(): React.ReactElement {
  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        marginTop: "10vh",
      }}
    >
      <h1>Logged in!</h1>
      <p>You have successfully authenticated with Spotify.</p>
    </main>
  );
}

export default LoggedIn;
