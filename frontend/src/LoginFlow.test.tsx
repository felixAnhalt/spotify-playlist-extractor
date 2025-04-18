/**
 * @file LoginFlow.test.tsx
 * High-level tests for the Spotify login flow and routing.
 */

import * as React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import LandingPage from "./views/LandingPage";
import OAuthCallback from "./views/OAuthCallback";
import LoggedIn from "./views/LoggedIn";

// Mock window.location
const originalLocation = window.location;
beforeAll(() => {
  // @ts-ignore
  delete window.location;
  // @ts-ignore
  window.location = { href: "" };
});
afterAll(() => {
  window.location = originalLocation;
});

describe("Login Flow", () => {
  it('renders "Login with Spotify" button and triggers backend call', async () => {
    // Mock fetch for /api/login
    global.fetch = jest.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({ redirect_url: "https://spotify.com/auth" }),
    });

    render(
      <MemoryRouter initialEntries={["/"]}>
        <LandingPage />
      </MemoryRouter>
    );

    const button = screen.getByRole("button", { name: /login with spotify/i });
    expect(button).toBeInTheDocument();

    fireEvent.click(button);

    await waitFor(() =>
      expect(window.location.href).toBe("https://spotify.com/auth")
    );
  });

  it("routes /callback to OAuthCallback and triggers backend call", async () => {
    // Mock fetch for /api/callback
    global.fetch = jest.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    // Mock history.replace
    const replaceMock = jest.fn();
    jest.spyOn(require("react-router"), "useHistory").mockReturnValue({
      replace: replaceMock,
    });
    jest.spyOn(require("react-router"), "useLocation").mockReturnValue({
      search: "?code=abc&state=xyz",
    });

    render(
      <MemoryRouter initialEntries={["/callback"]}>
        <Routes>
          <Route path="/callback" element={<OAuthCallback />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/callback?code=abc&state=xyz",
        expect.objectContaining({ method: "GET" })
      )
    );
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/logged-in"));
  });

  it("routes /logged-in to LoggedIn confirmation", () => {
    render(
      <MemoryRouter initialEntries={["/logged-in"]}>
        <Routes>
          <Route path="/logged-in" element={<LoggedIn />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText(/logged in/i)).toBeInTheDocument();
    expect(
      screen.getByText(/successfully authenticated with spotify/i)
    ).toBeInTheDocument();
  });
});
