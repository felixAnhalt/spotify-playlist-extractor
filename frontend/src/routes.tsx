// routes.tsx
// Defines the application's routes using React Router v7 and TypeScript.

import { createBrowserRouter } from "react-router";
import LandingPage from "./views/LandingPage";
import OAuthCallback from "./views/OAuthCallback";
import LoggedIn from "./views/LoggedIn";
import PlaylistEditorContainer from "./views/PlaylistEditorContainer";

/**
 * AppRoutes component.
 * Provides the routing structure for the app.
 */
const generateAppRoutes = () => {
  return createBrowserRouter([
    {
      path: "/",
      element: <LandingPage />,
    },
    {
      path: "/callback",
      element: <OAuthCallback />,
    },
    {
      path: "/logged-in",
      element: <LoggedIn />,
    },
    {
      path: "/organize",
      element: <PlaylistEditorContainer />,
    },
    {
      path: "/auth/callback",
        element: <OAuthCallback />,
    }
  ]);
};

export default generateAppRoutes;
