// Container.tsx
// Reusable container component for consistent layout

import * as React from "react";

export interface ContainerProps {
  children: React.ReactNode;
  maxWidth?: string;
  centered?: boolean;
  padding?: string;
}

/**
 * Container component.
 * Provides consistent layout constraints and centering.
 */
function Container({
  children,
  maxWidth = "1200px",
  centered = true,
  padding = "2rem",
}: ContainerProps): React.ReactElement {
  const containerClasses = `
    w-full
    ${centered ? "mx-auto" : "mx-0"}
    ${padding}
  `;

  return (
    <div 
      className={containerClasses}
      style={{ maxWidth }}
    >
      {children}
    </div>
  );
}

export default Container;
