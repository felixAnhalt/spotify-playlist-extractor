// LoggedIn.tsx
// Displays a simple confirmation after successful Spotify login.

import * as React from "react";

/**
 * LoggedIn component.
 * Shows a confirmation message after successful authentication.
 */
function LoggedIn(): React.ReactElement {
  return (
    <main className="min-h-screen bg-gradient-to-br from-primary-50 via-accent-50 to-secondary-50 flex items-center justify-center">
      <div className="bg-primary-100 p-12 rounded-xl border-primary-700 text-center max-w-md shadow-cartoon border-cartoon-3">
        <div className="text-8xl mb-6 animate-bounce animate-bounce-slow">🎉</div>
        <h1 className="text-5xl font-black text-primary-900 mb-4 font-mono-bold text-shadow-cartoon letter-spacing-cartoon-lg">
          LOGGED IN!
        </h1>
        <p className="text-xl text-primary-800 font-medium">
          You have successfully authenticated with Spotify! 🎵
        </p>
      </div>
    </main>
  );
}

export default LoggedIn;
