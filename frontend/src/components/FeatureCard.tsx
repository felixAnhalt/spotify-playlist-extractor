// FeatureCard.tsx
// Feature card component for displaying app features

import * as React from "react";
import Card from "./Card";

export interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
}

/**
 * FeatureCard component.
 * Displays a single feature with icon, title, and description.
 */
function FeatureCard({ icon, title, description }: FeatureCardProps): React.ReactElement {
  return (
    <Card hover padding="2rem" background="rgba(245, 230, 211, 0.8)">
      <div className="flex flex-col items-center text-center gap-4">
        <div className="text-6xl leading-none animate-bounce animate-bounce-slow">
          {icon}
        </div>
        <h3 className="text-xl m-0 text-primary-900 font-black text-center font-mono-bold letter-spacing-cartoon leading-snug">
          {title}
        </h3>
        <p className="m-0 text-base leading-relaxed text-primary-800 font-medium">
          {description}
        </p>
      </div>
    </Card>
  );
}

export default FeatureCard;
