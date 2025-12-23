// ComponentName.tsx
// Brief description of component purpose

// always named imports from React
import { ReactNode, ReactElement } from "react";

export interface ComponentNameProps {
  children: ReactNode;
  variant?: "primary" | "secondary";
  size?: "small" | "medium" | "large";
  disabled?: boolean;
  // Add additional props as needed
}

/**
 * ComponentName component.
 * Detailed description of component behavior and usage.
 */
export const ComponentName = ({
  children,
  variant = "primary",
  size = "medium",
  disabled = false,
}: ComponentNameProps): ReactElement => {
  // 1. Local state (if needed)

  // 2. Event handlers (if needed)

  // 3. Computed variant/size classes
  const getVariantClasses = (): string => {
    switch (variant) {
      case "secondary":
        return "bg-secondary-500 text-white";
      case "primary":
      default:
        return "bg-primary-500 text-white";
    }
  };

  const getSizeClasses = (): string => {
    switch (size) {
      case "small":
        return "px-3 py-1 text-sm";
      case "large":
        return "px-6 py-3 text-lg";
      case "medium":
      default:
        return "px-4 py-2 text-base";
    }
  };

  // 4. Compose final classes
  const baseClasses = `
    rounded-lg transition-all duration-200
    ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
    ${getVariantClasses()}
    ${getSizeClasses()}
  `;

  return (
    <div className={baseClasses}>
      {children}
    </div>
  );
}

export default ComponentName;
