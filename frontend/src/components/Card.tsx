// Card.tsx
// Reusable card component for content sections

import * as React from "react";

export interface CardProps {
  children: React.ReactNode;
  hover?: boolean;
  padding?: string;
  background?: string;
}

/**
 * Card component.
 * Reusable card with optional hover effect.
 */
function Card({
  children,
  hover = false,
  padding = "2rem",
  background = "rgba(212, 165, 116, 0.3)",
}: CardProps): React.ReactElement {
  const [isHovered, setIsHovered] = React.useState(false);

  const cardClasses = `
    rounded-lg transition-all duration-200 transform cartoon-card
    ${hover && isHovered ? "-translate-y-2 rotate-1" : ""}
    ${hover && !isHovered ? "hover:-translate-y-2 hover:rotate-1" : ""}
  `;

  return (
    <div
      className={`${cardClasses} ${background === "rgba(245, 230, 211, 0.8)" ? 'bg-primary-50-opacity' : ''} border-primary-700 shadow-cartoon border-cartoon-3`}
      style={{ 
        padding,
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {children}
    </div>
  );
}

export default Card;
