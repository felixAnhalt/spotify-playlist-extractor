// PlaylistEditor.test.tsx
import React from "react";
import { render, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import { PlaylistEditor, Playlist, DiscardPool } from "./PlaylistEditor";

/**
 * High-level test for PlaylistEditor UI flows.
 */
describe("PlaylistEditor", () => {
  const playlists: Playlist[] = [
    {
      id: "1",
      name: "Chill Vibes",
      songs: [
        { id: "s1", title: "Song A", artist: "Artist 1", selected: false },
        { id: "s2", title: "Song B", artist: "Artist 2", selected: false },
      ],
      selected: true,
    },
    {
      id: "2",
      name: "Workout",
      songs: [
        { id: "s3", title: "Song C", artist: "Artist 3", selected: false },
      ],
      selected: false,
    },
  ];

  const discardPool: DiscardPool = {
    songs: [{ id: "s4", title: "Song D", artist: "Artist 4", selected: false }],
  };

  it("renders playlists and discard pool", () => {
    const { getByDisplayValue, getByText } = render(
      <PlaylistEditor
        initialPlaylists={playlists}
        initialDiscardPool={discardPool}
      />
    );
    expect(getByDisplayValue("Chill Vibes")).toBeInTheDocument();
    expect(getByDisplayValue("Workout")).toBeInTheDocument();
    expect(getByText("Discard Pool")).toBeInTheDocument();
    expect(getByText("Song D — Artist 4")).toBeInTheDocument();
  });

  it("allows renaming a playlist", () => {
    const { getByDisplayValue } = render(
      <PlaylistEditor
        initialPlaylists={playlists}
        initialDiscardPool={discardPool}
      />
    );
    const input = getByDisplayValue("Chill Vibes") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Relaxed" } });
    expect(input.value).toBe("Relaxed");
  });

  it("allows selecting/deselecting playlists", () => {
    const { getAllByRole } = render(
      <PlaylistEditor
        initialPlaylists={playlists}
        initialDiscardPool={discardPool}
      />
    );
    const checkboxes = getAllByRole("checkbox");
    // First checkbox is for the first playlist
    fireEvent.click(checkboxes[0]);
    expect((checkboxes[0] as HTMLInputElement).checked).toBe(false);
  });

  it("allows selecting/deselecting songs", () => {
    const { getAllByLabelText } = render(
      <PlaylistEditor
        initialPlaylists={playlists}
        initialDiscardPool={discardPool}
      />
    );
    const songCheckbox = getAllByLabelText("Select song Song A")[0];
    fireEvent.click(songCheckbox);
    expect((songCheckbox as HTMLInputElement).checked).toBe(true);
  });
});
