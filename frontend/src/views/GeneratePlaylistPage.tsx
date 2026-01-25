/**
 * GeneratePlaylistPage.tsx
 * AI-powered playlist generation from a reference playlist.
 */

import React, { useState } from "react";
import { useNavigate } from "react-router";
import { generatePlaylistFromReference, createPlaylists } from "../api/backendConnector";
import { useOAuthState } from "../auth/OAuthStateContext";
import Container from "../components/Container";
import Button from "../components/Button";
import Modal from "../components/Modal";

interface RecommendedTrack {
  track: any;
  audio_features: any;
  fit_score: number;
}

interface GeneratedPlaylist {
  recommended_tracks: RecommendedTrack[];
  playlist_profile: Record<string, number>;
  llm_reasoning: string;
  method: "llm" | "algorithmic";
}

const GeneratePlaylistPage: React.FC = () => {
  const navigate = useNavigate();
  const { state } = useOAuthState();
  const [referenceUrl, setReferenceUrl] = useState("");
  const [playlistName, setPlaylistName] = useState("");
  const [songLimit, setSongLimit] = useState(20);
  const [loading, setLoading] = useState(false);
  const [generated, setGenerated] = useState<GeneratedPlaylist | null>(null);
  const [selectedTracks, setSelectedTracks] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const [modal, setModal] = useState<{ open: boolean; message: string }>({
    open: false,
    message: "",
  });
  const [createdLinks, setCreatedLinks] = useState<
    { name: string; url: string }[]
  >([]);

  const handleGenerate = async () => {
    if (!state) {
      setError("Please log in first");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const resp = await generatePlaylistFromReference(
        referenceUrl,
        playlistName,
        state,
        songLimit
      );

      const data: GeneratedPlaylist = resp.data;
      setGenerated(data);

      // Select all tracks by default
      const allIds = new Set(data.recommended_tracks.map(t => t.track.id));
      setSelectedTracks(allIds);

    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || "Failed to generate playlist";
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleTrack = (trackId: string) => {
    setSelectedTracks(prev => {
      const next = new Set(prev);
      if (next.has(trackId)) {
        next.delete(trackId);
      } else {
        next.add(trackId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (!generated) return;
    const allIds = new Set(generated.recommended_tracks.map(t => t.track.id));
    setSelectedTracks(allIds);
  };

  const handleDeselectAll = () => {
    setSelectedTracks(new Set());
  };

  const handleCreatePlaylist = async () => {
    if (!generated || !state) {
      setModal({ open: true, message: "Error: Missing data. Please try again." });
      return;
    }

    setLoading(true);
    setError("");
    setModal({ open: true, message: "Creating playlist in Spotify..." });

    try {
      const trackIds = generated.recommended_tracks
        .filter(t => selectedTracks.has(t.track.id))
        .map(t => t.track.id);

      console.log("Creating playlist with:", {
        playlistName,
        trackCount: trackIds.length,
        description: generated.llm_reasoning
      });

      const resp = await createPlaylists(
        [{
          name: playlistName,
          description: "",
          tracks: trackIds
        }],
        state,
        false  // private by default
      );

      console.log("Create response:", resp.data);

      if (resp.data?.created && resp.data.created.length > 0) {
        console.log("Playlist created successfully:", resp.data.created);
        setCreatedLinks(resp.data.created);
        setModal({ open: true, message: "Playlist created successfully!" });
      } else {
        console.warn("No playlists in response:", resp.data);
        setModal({ open: true, message: "Error: No playlists were created. Please check backend logs." });
      }

    } catch (err: any) {
      console.error("Error creating playlist:", err);
      const errorMsg = err?.response?.data?.detail || err?.message || "Failed to create playlist";
      setModal({ open: true, message: "Error: " + errorMsg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-linear-to-br from-primary-50 via-accent-50 to-secondary-100">
      <Container>
        <div className="flex flex-col items-center justify-center min-h-screen py-12">
          {/* Header */}
          <div className="text-center mb-12">
            <div className="text-6xl mb-4 animate-bounce" style={{ animationDuration: '2s' }}>🤖🎵</div>
            <h1 className="text-5xl font-black text-primary-900 mb-6 font-mono-bold text-shadow-cartoon letter-spacing-cartoon-lg">
              AI PLAYLIST GENERATOR
            </h1>
            <p className="text-xl text-primary-800 max-w-2xl bg-primary-100 p-4 rounded-lg border-2 border-primary-700 font-medium shadow-cartoon-sm border-cartoon-2">
              Give a reference playlist and a name - our AI will pick the perfect songs for your vibe!
            </p>

            {/* Feature Toggle Navigation */}
            <div className="mt-6 flex gap-4 justify-center">
              <button
                onClick={() => navigate("/organize")}
                className="px-6 py-2 font-bold rounded-full bg-primary-100 text-primary-900 border-2 border-primary-700 border-cartoon-2 shadow-cartoon-xs hover:bg-primary-200 transition-all font-mono"
              >
                📂 Organize Playlists
              </button>
              <button
                onClick={() => {}}
                disabled
                className="px-6 py-2 font-bold rounded-full bg-accent-500 text-white border-2 border-accent-700 border-cartoon-2 shadow-cartoon-xs cursor-default opacity-100"
              >
                🤖 AI Generator
              </button>
            </div>
          </div>

          {/* Input Form */}
          {!generated && (
            <div className="w-full max-w-2xl space-y-4">
              <div>
                <label className="block text-sm font-bold text-primary-900 mb-2">
                  New Playlist Name
                </label>
                <input
                  type="text"
                  placeholder="e.g., Late Night Coding, Morning Motivation..."
                  value={playlistName}
                  onChange={(e) => setPlaylistName(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl bg-primary-50 border-2 border-primary-700 text-primary-900 placeholder-primary-400 focus:outline-none focus:border-accent-500 focus:bg-white focus:ring-2 focus:ring-accent-200 transition-all font-medium font-mono shadow-cartoon-xs border-cartoon-2"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-primary-900 mb-2">
                  Reference Playlist URL or ID
                </label>
                <input
                  type="text"
                  placeholder="https://open.spotify.com/playlist/..."
                  value={referenceUrl}
                  onChange={(e) => setReferenceUrl(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl bg-primary-50 border-2 border-primary-700 text-primary-900 placeholder-primary-400 focus:outline-none focus:border-accent-500 focus:bg-white focus:ring-2 focus:ring-accent-200 transition-all font-medium font-mono shadow-cartoon-xs border-cartoon-2"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-primary-900 mb-2">
                  Number of Songs (optional)
                </label>
                <input
                  type="number"
                  min="0"
                  max="50"
                  value={songLimit}
                  onChange={(e) => setSongLimit(parseInt(e.target.value) || 20)}
                  className="w-full px-4 py-3 rounded-xl bg-primary-50 border-2 border-primary-700 text-primary-900 focus:outline-none focus:border-accent-500 focus:bg-white focus:ring-2 focus:ring-accent-200 transition-all font-medium font-mono shadow-cartoon-xs border-cartoon-2"
                  disabled={loading}
                />
              </div>

              {error && (
                <div className="bg-red-100 border-2 border-red-500 text-red-700 px-4 py-3 rounded-xl font-medium">
                  {error}
                </div>
              )}

              <Button
                onClick={handleGenerate}
                disabled={loading || !playlistName || !referenceUrl}
                variant="spotify"
                size="large"
              >
                {loading ? "GENERATING..." : "GENERATE PLAYLIST"}
              </Button>
            </div>
          )}

           {/* Generated Results */}
           {generated && createdLinks.length === 0 && (
             <div className="w-full max-w-4xl">
               <div className="bg-white border-2 border-primary-700 rounded-xl p-6 mb-6 shadow-cartoon">
                 <h2 className="text-2xl font-bold text-primary-900 mb-4">
                   {playlistName}
                 </h2>
                 <div className="bg-accent-50 p-4 rounded-lg border-2 border-accent-500 mb-6">
                   <p className="text-sm font-medium text-accent-900">
                     <strong>AI Reasoning:</strong> {generated.llm_reasoning}
                   </p>
                   {generated.method === "algorithmic" && (
                     <p className="text-xs text-accent-700 mt-2">
                       (Fallback: Algorithmic selection used)
                     </p>
                   )}
                 </div>

                 <div className="flex gap-4 mb-4">
                   <Button onClick={handleSelectAll} variant="secondary" size="small">
                     Select All
                   </Button>
                   <Button onClick={handleDeselectAll} variant="secondary" size="small">
                     Deselect All
                   </Button>
                   <span className="text-sm text-primary-700 flex items-center">
                     {selectedTracks.size} of {generated.recommended_tracks.length} selected
                   </span>
                 </div>

                 <div className="space-y-2 max-h-96 overflow-y-auto">
                   {generated.recommended_tracks.map((item) => (
                     <div
                       key={item.track.id}
                       className={`flex items-center gap-4 p-3 rounded-lg border-2 transition-all cursor-pointer ${
                         selectedTracks.has(item.track.id)
                           ? "bg-accent-50 border-accent-500"
                           : "bg-gray-50 border-gray-300"
                       }`}
                       onClick={() => handleToggleTrack(item.track.id)}
                     >
                       <input
                         type="checkbox"
                         checked={selectedTracks.has(item.track.id)}
                         onChange={() => handleToggleTrack(item.track.id)}
                         className="w-5 h-5"
                       />
                       <div className="flex-1">
                         <div className="font-medium text-primary-900">
                           {item.track.name}
                         </div>
                         <div className="text-sm text-primary-600">
                           {item.track.artists?.map((a: any) => a.name).join(", ")}
                         </div>
                       </div>
                       <div className="text-sm font-bold text-accent-700">
                         {Math.round(item.fit_score * 100)}% match
                       </div>
                     </div>
                   ))}
                 </div>
               </div>

               <div className="flex gap-4 justify-center">
                 <Button
                   onClick={() => {
                     setGenerated(null);
                     setSelectedTracks(new Set());
                     setError("");
                   }}
                   variant="secondary"
                   size="large"
                 >
                   Start Over
                 </Button>
                 <Button
                   onClick={handleCreatePlaylist}
                   disabled={loading || selectedTracks.size === 0}
                   variant="spotify"
                   size="large"
                 >
                   {loading ? "Creating..." : "Create Playlist in Spotify"}
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
               <h3 className="text-lg font-semibold text-neutral-800 mb-4">Created Playlist:</h3>
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
                 onClick={() => {
                   setModal({ open: false, message: "" });
                   setCreatedLinks([]);
                   setGenerated(null);
                   setSelectedTracks(new Set());
                   setPlaylistName("");
                   setReferenceUrl("");
                   setError("");
                 }}
                 variant="secondary"
                 size="medium"
               >
                 Create Another
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

export default GeneratePlaylistPage;
