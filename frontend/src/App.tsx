// App.tsx
// Root component for the Spotify Playlist Organizer app.

import React from "react";
import { RouterProvider } from "react-router"

import generateAppRoutes from "./routes";

/**
 * App component.
 * Provides a layout and renders the current route.
 */
function App() {
  return (
    <div>
        <RouterProvider router={generateAppRoutes()} />
    </div>
  );
}

export default App;
