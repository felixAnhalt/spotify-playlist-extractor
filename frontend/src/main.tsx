// main.tsx
// Entry point for the React app using TypeScript and React Router v7.

import React from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

/**
 * Renders the root React application with routing.
 */
createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
