import React from "react";

interface LogoProps {
  size?: number;
  className?: string;
}

/**
 * ContentSignal brand mark.
 * Minimal document silhouette with an ascending signal vector (data -> change -> insight).
 * Clean vector geometry optimized for 24-32px display.
 */
export function Logo({ size = 26, className = "" }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
      aria-label="ContentSignal Logo"
    >
      {/* Document Silhouette Base */}
      <path
        d="M6.5 4.75C6.5 3.7835 7.2835 3 8.25 3H17.75L22.5 7.75V23.25C22.5 24.2165 21.7165 25 20.75 25H8.25C7.2835 25 6.5 24.2165 6.5 23.25V4.75Z"
        className="fill-slate-100/90 dark:fill-slate-900 stroke-slate-800 dark:stroke-slate-200"
        strokeWidth="1.65"
        strokeLinejoin="round"
      />

      {/* Fold Flap */}
      <path
        d="M17.5 3V7.25C17.5 7.66421 17.8358 8 18.25 8H22.5"
        className="fill-slate-200/80 dark:fill-slate-800 stroke-slate-800 dark:stroke-slate-200"
        strokeWidth="1.65"
        strokeLinejoin="round"
      />

      {/* Ascending Signal Vector (data -> change -> insight) */}
      <path
        d="M9.75 18L13 14.25L15.75 16.5L19.25 11"
        className="stroke-teal-600 dark:stroke-teal-400"
        strokeWidth="2.1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Terminal Signal Node (Insight Point) */}
      <circle
        cx="19.25"
        cy="11"
        r="1.6"
        className="fill-teal-600 dark:fill-teal-400"
      />
    </svg>
  );
}
