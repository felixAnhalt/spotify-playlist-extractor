// LandingPage.tsx
// Landing page with "Login with Spotify" button.
// Initiates OAuth flow by calling backend login endpoint.

import * as React from "react";
import { login } from "../api/backendConnector";
import Container from "../components/Container";
import Button from "../components/Button";
import Card from "../components/Card";
import FeatureCard from "../components/FeatureCard";

/**
 * Landing page component.
 * Renders a beautiful landing page with project explanation and login button.
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
      const { redirect_url } = response.data;
      window.location.href = redirect_url;
    } catch (err: any) {
      alert("Login failed: " + (err?.message ?? "Unknown error"));
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-primary-50 via-accent-50 to-secondary-50 relative">
      <Container>
        {/* Hero Section */}
        <section className="flex flex-col items-center pt-16 pb-12 text-center">
          <div className="text-8xl mb-6 animate-bounce animate-bounce-slow">🎵</div>
          <h1 className="text-6xl font-black mb-6 text-primary-900 font-mono-bold text-shadow-cartoon letter-spacing-cartoon-lg leading-tight">
            SPOTIFY PLAYLIST<br/>ORGANIZER
          </h1>
          <p className="text-xl text-primary-800 max-w-2xl mb-10 leading-relaxed font-medium bg-primary-100 p-6 rounded-lg border-primary-700 font-mono shadow-cartoon-sm border-cartoon-3">
            Transform your massive super playlists into organized collections<br/>
            based on vibe, mood, and energy!
          </p>
          <Button
            onClick={handleLogin}
            variant="spotify"
            size="large"
            ariaLabel="Login with Spotify"
          >
            🎵 LOGIN WITH SPOTIFY
          </Button>
        </section>

        {/* How It Works Section */}
        <section className="pt-12 pb-12">
          <h2 className="text-center text-5xl font-black mb-12 text-primary-900 font-mono-bold text-shadow-cartoon letter-spacing-cartoon-lg">
            HOW IT WORKS
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard
              icon="📂"
              title="CONNECT YOUR PLAYLISTS"
              description="Link your Spotify account and select your massive super playlist with hundreds of songs!"
            />
            <FeatureCard
              icon="🎯"
              title="AI-POWERED CLUSTERING"
              description="Our algorithm analyzes each track's vibe, mood, energy, and genre to intelligently group similar songs!"
            />
            <FeatureCard
              icon="✨"
              title="CREATE NEW PLAYLISTS"
              description="Generate organized sub-playlists automatically, each with a cohesive vibe and feel!"
            />
          </div>
        </section>

        {/* Features Section */}
        <section className="pt-12 pb-16">
          <Card padding="3rem" background="rgba(212, 165, 116, 0.2)">
            <h2 className="text-center text-4xl font-black mb-8 text-primary-900 font-mono-bold text-shadow-cartoon letter-spacing-cartoon-lg">
              WHY USE THIS TOOL?
            </h2>
            <div className="flex flex-col gap-6 max-w-3xl mx-auto">
              <FeatureItem
                title="REDISCOVER YOUR MUSIC"
                description="Stop scrolling endlessly through your giant playlists. Find the perfect vibe instantly!"
              />
              <FeatureItem
                title="SMART ORGANIZATION"
                description="Automatically cluster songs by mood, energy, and genre without manual sorting!"
              />
              <FeatureItem
                title="BETTER LISTENING EXPERIENCE"
                description="Create cohesive playlists that flow naturally from song to song!"
              />
            </div>
          </Card>
        </section>
      </Container>
    </main>
  );
}

/**
 * FeatureItem component.
 * Displays a single feature in the Why Use section.
 */
function FeatureItem({
  title,
  description,
}: {
  title: string;
  description: string;
}): React.ReactElement {
  return (
    <div className="flex gap-4 items-start bg-primary-50 p-4 rounded-lg border-2 border-primary-700 shadow-cartoon-sm border-cartoon-2">
      <div className="text-3xl text-accent-500 flex-shrink-0 font-bold font-mono">✓</div>
      <div>
        <h3 className="m-0 mb-2 text-xl text-primary-900 font-black font-mono letter-spacing-cartoon">
          {title}
        </h3>
        <p className="m-0 text-base text-primary-800 leading-relaxed font-medium">
          {description}
        </p>
      </div>
    </div>
  );
}

export default LandingPage;
