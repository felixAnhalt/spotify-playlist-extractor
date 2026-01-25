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
    * Also toggles the selected state of all songs in the playlist.
    */
   const handleSelectPlaylist = (playlistId: string) => {
     setPlaylists((pls) =>
       pls.map((p) => {
         if (p.id === playlistId) {
           const newSelected = !p.selected;
           return {
             ...p,
             selected: newSelected,
             songs: p.songs.map((s) => ({ ...s, selected: newSelected })),
           };
         }
         return p;
       })
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
      <div className="flex flex-col lg:flex-row lg:gap-6 xl:gap-8 items-start overflow-x-auto pb-4">
        {playlists.map((playlist) => (
          <div key={playlist.id} className="w-full lg:w-80 xl:min-w-[300px] mb-6 lg:mb-0">
            <div className="flex items-center gap-3 mb-3 p-2">
              <input
                type="checkbox"
                checked={playlist.selected}
                onChange={() => handleSelectPlaylist(playlist.id)}
                className="w-5 h-5 text-primary-500 rounded focus:ring-2 focus:ring-primary-300 border-2 border-primary-700"
                aria-label={`Select playlist ${playlist.name}`}
              />
              <input
                type="text"
                value={playlist.name}
                onChange={(e) => handleRename(playlist.id, e.target.value)}
                className="font-bold text-lg bg-primary-50 border-2 border-primary-700 rounded px-2 py-1 text-primary-900 placeholder-primary-400 flex-1 cartoon-input font-mono shadow-cartoon-xs border-cartoon-2"
                aria-label={`Rename playlist ${playlist.name}`}
              />
            </div>
            <Droppable droppableId={`playlist:${playlist.id}`}>
              {(provided) => (
                <ul
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                  className="bg-primary-50 p-3 min-h-24 rounded-lg border-primary-700 shadow-lg border-cartoon-3 shadow-cartoon"
                >
                  {playlist.songs.map((song, idx) => (
                    <Draggable key={song.id} draggableId={song.id} index={idx}>
                      {(dragProvided) => (
                        <li
                          ref={dragProvided.innerRef}
                          {...dragProvided.draggableProps}
                          {...dragProvided.dragHandleProps}
                          style={dragProvided.draggableProps.style}
                          className="bg-neutral-50 mb-2 p-2 rounded flex items-center border-2 border-primary-600 hover:bg-primary-100 hover:border-accent-500 transition-all duration-200 cartoon-song shadow-cartoon-song border-cartoon-2"
                        >
                          <input
                            type="checkbox"
                            checked={!!song.selected}
                            onChange={() =>
                              handleSelectSong(playlist.id, song.id)
                            }
                            className="w-4 h-4 text-accent-500 rounded focus:ring-2 focus:ring-accent-300 mr-3 border-2 border-accent-600"
                            aria-label={`Select song ${song.title}`}
                          />
                          <span className="text-sm font-medium text-primary-900 font-mono">
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
        <div className="w-full lg:w-80 xl:min-w-[300px]">
          <div className="font-bold text-lg text-primary-900 mb-3 p-2 bg-accent-200 border-2 border-accent-700 rounded font-mono shadow-cartoon-xs border-cartoon-2">
            🗑️ Discard Pool
          </div>
          <Droppable droppableId="discard:pool">
            {(provided) => (
              <ul
                ref={provided.innerRef}
                {...provided.droppableProps}
                className="bg-neutral-100 p-3 min-h-24 rounded-lg border-secondary-700 shadow-lg border-cartoon-3 shadow-cartoon"
              >
                {discardPool.songs.map((song, idx) => (
                  <Draggable key={song.id} draggableId={song.id} index={idx}>
                    {(dragProvided) => (
                      <li
                        ref={dragProvided.innerRef}
                        {...dragProvided.draggableProps}
                        {...dragProvided.dragHandleProps}
                        style={dragProvided.draggableProps.style}
                        className="bg-neutral-50 mb-2 p-2 rounded flex items-center border-2 border-secondary-600 hover:bg-secondary-50 hover:border-secondary-500 transition-all duration-200 cartoon-song shadow-cartoon-song border-cartoon-2"
                      >
                        <input
                           type="checkbox"
                           checked={!!song.selected}
                           onChange={() => handleSelectDiscardSong(song.id)}
                           className="w-4 h-4 text-secondary-500 rounded focus:ring-2 focus:ring-secondary-300 mr-3 border-2 border-secondary-600"
                           aria-label={`Select song ${song.title}`}
                         />
                        <span className="text-sm font-medium text-neutral-700 font-mono">
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
