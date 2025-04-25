import React, { createContext, useContext, useEffect, useState } from "react";

interface OAuthStateContextType {
  state: string | null;
  setState: (s: string | null) => void;
}

const OAuthStateContext = createContext<OAuthStateContextType>({
  state: null,
  setState: () => {},
});

/**
 * OAuthStateProvider component.
 * Reads state from localStorage on mount and provides it via context.
 */
export const OAuthStateProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [state, setState] = useState<string | null>(() =>
    localStorage.getItem("spotify_oauth_state")
  );

  useEffect(() => {
    if (state) {
      localStorage.setItem("spotify_oauth_state", state);
    }
  }, [state]);

  return (
    <OAuthStateContext.Provider value={{ state, setState }}>
      {children}
    </OAuthStateContext.Provider>
  );
};

/**
 * Hook to use OAuth state context.
 */
export const useOAuthState = () => useContext(OAuthStateContext);
