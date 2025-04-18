// PlaylistEditor.tsx
import React, { useState } from "react";
import {
  DragDropContext,
  Droppable,
  Draggable,
  DropResult,
} from "@hello-pangea/dnd";

/**
 * Song type definition.
 */
export interface Song {
  id: string;
  title: string;
  artist: string;
  /**
   * Whether the song is selected for creation.
   */
  selected?: boolean;
}

/**
 * Playlist type definition.
 */
export interface Playlist {
  id: string;
  name: string;
  songs: Song[];
  selected: boolean;
}

/**
 * Discard pool type definition.
 */
export interface DiscardPool {
  songs: Song[];
}

/**
 * Props for PlaylistEditor.
 */
interface PlaylistEditorProps {
  initialPlaylists: Playlist[];
  initialDiscardPool: DiscardPool;
}

/**
 * PlaylistEditor component.
 * Displays and allows editing of proposed playlists and a discard pool.
 */
export const PlaylistEditor: React.FC<PlaylistEditorProps> = ({
  initialPlaylists,
  initialDiscardPool,
}) => {
  const [playlists, setPlaylists] = useState<Playlist[]>(initialPlaylists);
  const [discardPool, setDiscardPool] =
    useState<DiscardPool>(initialDiscardPool);

  /**
   * Handles drag-and-drop logic for moving songs between playlists and discard pool.
   */
  const onDragEnd = (result: DropResult) => {
    const { source, destination } = result;
    if (!destination) return;

    // Helper to find and remove a song from a playlist or discard pool
    const removeSong = (list: Song[], songId: string) => {
      const idx = list.findIndex((s) => s.id === songId);
      if (idx === -1) return { song: null, newList: list };
      const song = list[idx];
      const newList = [...list.slice(0, idx), ...list.slice(idx + 1)];
      return { song, newList };
    };

    // Source and destination parsing
    const [srcType, srcId] = source.droppableId.split(":");
    const [dstType, dstId] = destination.droppableId.split(":");

    let movedSong: Song | null = null;
    let updatedPlaylists = [...playlists];
    let updatedDiscard = { ...discardPool };

    // Remove from source
    if (srcType === "playlist") {
      const pIdx = playlists.findIndex((p) => p.id === srcId);
      if (pIdx !== -1) {
        const { song, newList } = removeSong(
          playlists[pIdx].songs,
          playlists[pIdx].songs[source.index].id
        );
        movedSong = song;
        updatedPlaylists[pIdx] = { ...playlists[pIdx], songs: newList };
      }
    } else if (srcType === "discard") {
      const { song, newList } = removeSong(
        discardPool.songs,
        discardPool.songs[source.index].id
      );
      movedSong = song;
      updatedDiscard.songs = newList;
    }

    if (!movedSong) return;

    // Add to destination
    if (dstType === "playlist") {
      const pIdx = updatedPlaylists.findIndex((p) => p.id === dstId);
      if (pIdx !== -1) {
        const newSongs = Array.from(updatedPlaylists[pIdx].songs);
        newSongs.splice(destination.index, 0, movedSong);
        updatedPlaylists[pIdx] = { ...updatedPlaylists[pIdx], songs: newSongs };
      }
    } else if (dstType === "discard") {
      const newSongs = Array.from(updatedDiscard.songs);
      newSongs.splice(destination.index, 0, movedSong);
      updatedDiscard.songs = newSongs;
    }

    setPlaylists(updatedPlaylists);
    setDiscardPool(updatedDiscard);
  };

  /**
   * Handles renaming a playlist.
   */
  const handleRename = (playlistId: string, newName: string) => {
    setPlaylists((pls) =>
      pls.map((p) => (p.id === playlistId ? { ...p, name: newName } : p))
    );
  };

  /**
   * Handles selection/deselection of a playlist.
   */
  const handleSelectPlaylist = (playlistId: string) => {
    setPlaylists((pls) =>
      pls.map((p) =>
        p.id === playlistId ? { ...p, selected: !p.selected } : p
      )
    );
  };

  /**
   * Handles selection/deselection of a song within a playlist.
   */
  const handleSelectSong = (playlistId: string, songId: string) => {
    setPlaylists((pls) =>
      pls.map((p) =>
        p.id === playlistId
          ? {
              ...p,
              songs: p.songs.map((s) =>
                s.id === songId ? { ...s, selected: !s.selected } : s
              ),
            }
          : p
      )
    );
  };

  /**
   * Handles selection/deselection of a song in the discard pool.
   */
  const handleSelectDiscardSong = (songId: string) => {
    setDiscardPool((dp) => ({
      songs: dp.songs.map((s) =>
        s.id === songId ? { ...s, selected: !s.selected } : s
      ),
    }));
  };

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <div style={{ display: "flex", gap: "2rem", alignItems: "flex-start" }}>
        {playlists.map((playlist) => (
          <div key={playlist.id} style={{ minWidth: 300 }}>
            <input
              type="checkbox"
              checked={playlist.selected}
              onChange={() => handleSelectPlaylist(playlist.id)}
              aria-label={`Select playlist ${playlist.name}`}
            />
            <input
              type="text"
              value={playlist.name}
              onChange={(e) => handleRename(playlist.id, e.target.value)}
              aria-label={`Rename playlist ${playlist.name}`}
              style={{ fontWeight: "bold", fontSize: "1.1em", marginLeft: 8 }}
            />
            <Droppable droppableId={`playlist:${playlist.id}`}>
              {(provided) => (
                <ul
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                  style={{
                    background: "#f8f8f8",
                    padding: 8,
                    minHeight: 80,
                    borderRadius: 4,
                    marginTop: 8,
                  }}
                >
                  {playlist.songs.map((song, idx) => (
                    <Draggable key={song.id} draggableId={song.id} index={idx}>
                      {(dragProvided) => (
                        <li
                          ref={dragProvided.innerRef}
                          {...dragProvided.draggableProps}
                          {...dragProvided.dragHandleProps}
                          style={{
                            ...dragProvided.draggableProps.style,
                            background: "#fff",
                            marginBottom: 4,
                            padding: 6,
                            borderRadius: 3,
                            display: "flex",
                            alignItems: "center",
                            border: "1px solid #ddd",
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={!!song.selected}
                            onChange={() =>
                              handleSelectSong(playlist.id, song.id)
                            }
                            aria-label={`Select song ${song.title}`}
                            style={{ marginRight: 8 }}
                          />
                          <span>
                            {song.title} — {song.artist}
                          </span>
                        </li>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </ul>
              )}
            </Droppable>
          </div>
        ))}
        <div style={{ minWidth: 300 }}>
          <div style={{ fontWeight: "bold", fontSize: "1.1em" }}>
            Discard Pool
          </div>
          <Droppable droppableId="discard:pool">
            {(provided) => (
              <ul
                ref={provided.innerRef}
                {...provided.droppableProps}
                style={{
                  background: "#f8f8f8",
                  padding: 8,
                  minHeight: 80,
                  borderRadius: 4,
                  marginTop: 8,
                }}
              >
                {discardPool.songs.map((song, idx) => (
                  <Draggable key={song.id} draggableId={song.id} index={idx}>
                    {(dragProvided) => (
                      <li
                        ref={dragProvided.innerRef}
                        {...dragProvided.draggableProps}
                        {...dragProvided.dragHandleProps}
                        style={{
                          ...dragProvided.draggableProps.style,
                          background: "#fff",
                          marginBottom: 4,
                          padding: 6,
                          borderRadius: 3,
                          display: "flex",
                          alignItems: "center",
                          border: "1px solid #ddd",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={!!song.selected}
                          onChange={() => handleSelectDiscardSong(song.id)}
                          aria-label={`Select song ${song.title}`}
                          style={{ marginRight: 8 }}
                        />
                        <span>
                          {song.title} — {song.artist}
                        </span>
                      </li>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </ul>
            )}
          </Droppable>
        </div>
      </div>
    </DragDropContext>
  );
};

export default PlaylistEditor;
