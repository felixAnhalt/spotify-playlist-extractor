import axios from "axios";

// @ts-ignore
const BACKEND_BASE_PATH =
  import.meta.env.VITE_BACKEND_BASE_PATH || "http://localhost:8000";

const AUTH_PATH = `${BACKEND_BASE_PATH}/auth`;
const PLAYLIST_PATH = `${BACKEND_BASE_PATH}/playlist`;

/**
 * Initiates Spotify login.
 */
export const login = () => {
  return axios.get<{ redirect_url: string }>(`${AUTH_PATH}/login`, {
    withCredentials: true
  });
};

export const callback = (queryString: string) => {
    return axios.get(`${AUTH_PATH}/callback${queryString}`, {
      withCredentials: true,
    });
}

/**
 * Fetches playlist tracks and audio features.
 * @param playlist_id_or_url Spotify playlist ID or URL
 * @param state OAuth state string
 */
export const fetchPlaylistTracks = (
  playlist_id_or_url: string,
  state: string
) => {
  return axios.post(`${PLAYLIST_PATH}/tracks`, { playlist_id_or_url, state });
};

/**
 * Clusters tracks by vibe.
 * The backend automatically determines the optimal number of clusters based on audio feature variance.
 * @param tracks Array of track objects with audio_features
 */
export const clusterTracks = (tracks: any[]) => {
  return axios.post(`${PLAYLIST_PATH}/cluster`, { tracks });
};

/**
 * Gets LLM-generated cluster names.
 * @param tracks Array of track objects with audio_features
 * @param cluster_ids Array of cluster assignments
 */
export const getClusterNames = (tracks: any[], cluster_ids: number[]) => {
  return axios.post(`${PLAYLIST_PATH}/cluster-names`, { tracks, cluster_ids });
};

/**
 * Creates playlists in the user's Spotify account.
 * @param playlists Array of { name, description, tracks }
 * @param state OAuth state string
 * @param publicFlag Whether playlists should be public (optional)
 */
export const createPlaylists = (
  playlists: any[],
  state: string,
  publicFlag: boolean = false
) => {
  return axios.post(`${PLAYLIST_PATH}/create`, {
    playlists,
    state,
    public: publicFlag,
  });
};
