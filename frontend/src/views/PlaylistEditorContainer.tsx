/**
 * PlaylistEditorContainer.tsx
 * Handles backend integration and state for the playlist organization flow.
 * Passes playlists and discard pool as props to PlaylistEditor.
 */

import React, { useState } from "react";
import {
  fetchPlaylistTracks,
  clusterTracks,
  getClusterNames,
  createPlaylists,
} from "../api/backendConnector";
import PlaylistEditor, { Playlist, DiscardPool } from "./PlaylistEditor";
import { useOAuthState } from "../auth/OAuthStateContext";
import Container from "../components/Container";
import Button from "../components/Button";

/**
 * Modal component for feedback.
 */
function Modal({
  open,
  children,
}: {
  open: boolean;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-neutral-900/30 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-primary-50 p-8 rounded-xl min-w-80 max-w-md shadow-2xl border-primary-700 cartoon-card border-cartoon-3 shadow-cartoon">
        {children}
      </div>
    </div>
  );
}

/**
 * PlaylistEditorContainer component.
 */
const PlaylistEditorContainer: React.FC = () => {
  const { state } = useOAuthState();
  const [playlistUrl, setPlaylistUrl] = useState("");
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [discardPool, setDiscardPool] = useState<DiscardPool>({ songs: [] });
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState<{ open: boolean; message: string }>({
    open: false,
    message: "",
  });
  const [createdLinks, setCreatedLinks] = useState<
    { name: string; url: string }[]
  >([]);

  console.log("PlaylistEditorContainer: state", state);

  /**
   * Handles the full playlist organization flow.
   */
  const handleOrganize = async () => {
    setLoading(true);
    setModal({ open: true, message: "Fetching playlist tracks..." });
    try {
      // 1. Fetch tracks and audio features
      if (!state) throw new Error("Missing OAuth state. Please log in again.");
      const tracksResp = await fetchPlaylistTracks(playlistUrl, state);
      const tracksData = tracksResp.data.tracks;

      setModal({ open: true, message: "Clustering tracks by vibe..." });
      // 2. Cluster tracks (n_clusters determined automatically by backend)
      const clusterResp = await clusterTracks(tracksData);
      const clusterIds = clusterResp.data.cluster_ids;

      setModal({ open: true, message: "Naming clusters..." });
      // 3. Get cluster names
      const namesResp = await getClusterNames(tracksData, clusterIds);
      const clusterNames = namesResp.data.cluster_names;

      // 4. Build playlists and discard pool
      const clusterMap: { [cid: string]: Playlist } = {};
      tracksData.forEach((item: any, idx: number) => {
        const cid = clusterIds[idx];
        if (!clusterMap[cid]) {
          clusterMap[cid] = {
            id: cid.toString(),
            name: clusterNames[cid] || `Vibe ${cid + 1}`,
            songs: [],
            selected: true,
          };
        }
        const track = item.track;
        clusterMap[cid].songs.push({
          id: track.id,
          title: track.name,
          artist: track.artists?.map((a: any) => a.name).join(", ") || "",
          selected: true,
        });
      });
      setPlaylists(Object.values(clusterMap));
      setDiscardPool({ songs: [] });
      setModal({ open: false, message: "" });
    } catch (err: any) {
      setModal({
        open: true,
        message: "Error: " + (err?.message ?? "Unknown error"),
      });
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handles playlist creation in Spotify.
   */
  const handleCreatePlaylists = async () => {
    setLoading(true);
    setModal({ open: true, message: "Creating playlists in Spotify..." });
    try {
      const selectedPlaylists = playlists
        .filter((p) => p.selected)
        .map((p) => ({
          name: p.name,
          description: "",
          tracks: p.songs.filter((s) => s.selected).map((s) => s.id),
        }));
      if (!state) throw new Error("Missing OAuth state. Please log in again.");
      const resp = await createPlaylists(selectedPlaylists, state);
      setCreatedLinks(resp.data.created || []);
      setModal({ open: true, message: "Playlists created successfully!" });
    } catch (err: any) {
      setModal({
        open: true,
        message: "Error: " + (err?.message ?? "Unknown error"),
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-primary-50 via-accent-50 to-secondary-100">
      <Container>
        <div className="flex flex-col items-center justify-center min-h-screen py-12">
          {/* Header */}
          <div className="text-center mb-12">
            <div className="text-6xl mb-4 animate-bounce" style={{ animationDuration: '2s' }}>🎵</div>
            <h1 className="text-5xl font-black text-primary-900 mb-6 font-mono-bold text-shadow-cartoon letter-spacing-cartoon-lg">
              ORGANIZE YOUR PLAYLIST
            </h1>
            <p className="text-xl text-primary-800 max-w-2xl bg-primary-100 p-4 rounded-lg border-2 border-primary-700 font-medium shadow-cartoon-sm border-cartoon-2">
              Enter your Spotify playlist URL or ID to start organizing your music by vibe, mood, and energy!
            </p>
          </div>

          {/* Input Section */}
          <div className="flex flex-col sm:flex-row gap-4 mb-8 w-full max-w-2xl">
            <input
              type="text"
              placeholder="Enter Spotify playlist URL or ID"
              value={playlistUrl}
              onChange={(e) => setPlaylistUrl(e.target.value)}
              className="flex-1 px-4 py-3 rounded-xl bg-primary-50 border-2 border-primary-700 text-primary-900 placeholder-primary-400 focus:outline-none focus:border-accent-500 focus:bg-white focus:ring-2 focus:ring-accent-200 transition-all cartoon-input font-medium font-mono shadow-cartoon-xs border-cartoon-2"
              disabled={loading}
            />
            <Button
              onClick={handleOrganize}
              disabled={loading || !playlistUrl}
              variant="spotify"
              size="large"
            >
              {loading ? "PROCESSING..." : "ORGANIZE PLAYLIST"}
            </Button>
          </div>

          {/* Playlist Editor */}
          {playlists.length > 0 && (
            <div className="w-full max-w-6xl">
              <PlaylistEditor
                initialPlaylists={playlists}
                initialDiscardPool={discardPool}
              />
              <div className="flex justify-center mt-8">
                <Button
                  onClick={handleCreatePlaylists}
                  disabled={loading}
                  variant="spotify"
                  size="large"
                >
                  {loading ? "Creating..." : "Create Playlists in Spotify"}
                </Button>
              </div>
            </div>
          )}
        </div>
      </Container>

      {/* Modal */}
      <Modal open={modal.open}>
        <div className="text-center">
          <p className="text-neutral-700 mb-6">{modal.message}</p>
          {!loading && createdLinks.length > 0 && (
            <div className="text-left">
              <h3 className="text-lg font-semibold text-neutral-800 mb-4">Created Playlists:</h3>
              <ul className="space-y-2 mb-6">
                {createdLinks.map((pl) => (
                  <li key={pl.url}>
                    <a
                      href={pl.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-500 hover:text-primary-600 underline transition-colors"
                    >
                      {pl.name}
                    </a>
                  </li>
                ))}
              </ul>
              <Button
                onClick={() => setModal({ open: false, message: "" })}
                variant="secondary"
                size="medium"
              >
                Close
              </Button>
            </div>
          )}
          {!loading && createdLinks.length === 0 && (
            <Button
              onClick={() => setModal({ open: false, message: "" })}
              variant="secondary"
              size="medium"
            >
              Close
            </Button>
          )}
        </div>
      </Modal>
    </main>
  );
};

export default PlaylistEditorContainer;
