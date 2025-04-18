/**
 * PlaylistEditorContainer.tsx
 * Handles backend integration and state for the playlist organization flow.
 * Passes playlists and discard pool as props to PlaylistEditor.
 */

import React, { useState, useContext } from "react";
import {
  fetchPlaylistTracks,
  clusterTracks,
  getClusterNames,
  createPlaylists,
} from "../api/backendConnector";
import PlaylistEditor, { Playlist, DiscardPool, Song } from "./PlaylistEditor";

// Example OAuth state context (replace with your actual context)
const OAuthStateContext = React.createContext<{ state: string }>({ state: "" });

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
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        background: "rgba(0,0,0,0.3)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          background: "#fff",
          padding: 32,
          borderRadius: 8,
          minWidth: 320,
        }}
      >
        {children}
      </div>
    </div>
  );
}

/**
 * PlaylistEditorContainer component.
 */
const PlaylistEditorContainer: React.FC = () => {
  const { state } = useContext(OAuthStateContext);
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

  /**
   * Handles the full playlist organization flow.
   */
  const handleOrganize = async () => {
    setLoading(true);
    setModal({ open: true, message: "Fetching playlist tracks..." });
    try {
      // 1. Fetch tracks and audio features
      const tracksResp = await fetchPlaylistTracks(playlistUrl, state);
      const tracksData = tracksResp.data.tracks;

      setModal({ open: true, message: "Clustering tracks by vibe..." });
      // 2. Cluster tracks
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
    <div>
      <Modal open={modal.open}>
        <div>
          <p>{modal.message}</p>
          {!loading && createdLinks.length > 0 && (
            <div>
              <h3>Created Playlists:</h3>
              <ul>
                {createdLinks.map((pl) => (
                  <li key={pl.url}>
                    <a href={pl.url} target="_blank" rel="noopener noreferrer">
                      {pl.name}
                    </a>
                  </li>
                ))}
              </ul>
              <button onClick={() => setModal({ open: false, message: "" })}>
                Close
              </button>
            </div>
          )}
          {!loading && createdLinks.length === 0 && (
            <button onClick={() => setModal({ open: false, message: "" })}>
              Close
            </button>
          )}
        </div>
      </Modal>
      <div style={{ marginBottom: 24 }}>
        <input
          type="text"
          placeholder="Enter Spotify playlist URL or ID"
          value={playlistUrl}
          onChange={(e) => setPlaylistUrl(e.target.value)}
          style={{ width: 320, padding: 8, fontSize: "1em" }}
          disabled={loading}
        />
        <button
          onClick={handleOrganize}
          disabled={loading || !playlistUrl}
          style={{ marginLeft: 12 }}
        >
          Organize Playlist
        </button>
      </div>
      {playlists.length > 0 && (
        <div>
          <PlaylistEditor
            initialPlaylists={playlists}
            initialDiscardPool={discardPool}
          />
          <button
            onClick={handleCreatePlaylists}
            disabled={loading}
            style={{ marginTop: 24 }}
          >
            Create Playlists in Spotify
          </button>
        </div>
      )}
    </div>
  );
};

export default PlaylistEditorContainer;
