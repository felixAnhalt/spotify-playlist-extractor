// Button.tsx
// Reusable button component with variants

import * as React from "react";

export interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "spotify";
  size?: "small" | "medium" | "large";
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
  ariaLabel?: string;
}

/**
 * Button component.
 * Reusable button with multiple variants and sizes.
 */
function Button({
  children,
  onClick,
  variant = "primary",
  size = "medium",
  disabled = false,
  type = "button",
  ariaLabel,
}: ButtonProps): React.ReactElement {
  const getVariantClasses = (): string => {
    switch (variant) {
      case "spotify":
        return "bg-accent-500 text-primary-900 border-2 border-primary-700 font-bold hover:bg-accent-400 hover:shadow-xl cartoon-button";
      case "secondary":
        return "bg-secondary-200 text-primary-900 border-2 border-secondary-700 font-bold hover:bg-secondary-100 hover:shadow-xl cartoon-button";
      case "primary":
      default:
        return "bg-primary-500 text-primary-50 border-2 border-primary-700 font-bold hover:bg-primary-400 hover:shadow-xl cartoon-button";
    }
  };

  const getSizeClasses = (): string => {
    switch (size) {
      case "small":
        return "px-4 py-2 text-sm";
      case "large":
        return "px-10 py-3 text-xl";
      case "medium":
      default:
        return "px-7 py-3 text-base";
    }
  };

  const baseClasses = `
    rounded-lg font-bold transition-all duration-200 transform font-mono
    ${disabled ? "opacity-50 cursor-not-allowed scale-95" : "cursor-pointer"}
    ${!disabled && "hover:-translate-y-1 hover:scale-105 active:scale-95 active:translate-y-0"}
    ${getVariantClasses()}
    ${getSizeClasses()}
    cartoon-button-base border-cartoon-3 shadow-cartoon relative uppercase letter-spacing-cartoon
  `;

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={baseClasses}
      aria-label={ariaLabel}
    >
      {children}
    </button>
  );
}

export default Button;
