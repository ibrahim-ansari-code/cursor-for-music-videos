"use client";

import React from "react";

interface LogoProps {
  variant?: "full" | "minimal" | "icon";
  className?: string;
}

export default function Logo({ variant = "full", className = "" }: LogoProps) {
  if (variant === "icon") {
    return (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={className}
      >
        <path
          d="M13 2L3 14H12L11 22L21 10H12L13 2Z"
          fill="currentColor"
          stroke="black"
          strokeWidth="2"
          strokeLinejoin="round"
        />
      </svg>
    );
  }

  if (variant === "minimal") {
    return (
      <svg
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={className}
      >
        <path
          d="M50 5L60 35L95 40L70 60L80 95L50 80L20 95L30 60L5 40L40 35L50 5Z"
          fill="currentColor"
          stroke="black"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <circle cx="20" cy="20" r="5" fill="currentColor" opacity="0.5" />
        <circle cx="80" cy="15" r="3" fill="currentColor" opacity="0.3" />
        <circle cx="15" cy="80" r="4" fill="currentColor" opacity="0.4" />
      </svg>
    );
  }

  return (
    <div className={`relative inline-block ${className}`}>
      <svg
        viewBox="0 0 300 150"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-auto"
      >
        <defs>
          <pattern id="halftone" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
            <circle cx="3" cy="3" r="1.5" fill="#0057FF" fillOpacity="0.2" />
          </pattern>
        </defs>

        {/* Burst Background */}
        <path
          d="M150 10L175 45L220 35L210 75L260 85L220 105L240 140L180 120L150 145L120 120L60 140L80 105L40 85L90 75L80 35L125 45L150 10Z"
          fill="white"
          stroke="black"
          strokeWidth="3"
        />
        <path
          d="M150 10L175 45L220 35L210 75L260 85L220 105L240 140L180 120L150 145L120 120L60 140L80 105L40 85L90 75L80 35L125 45L150 10Z"
          fill="url(#halftone)"
        />

        {/* 3D Text Effect (Red Shadow) */}
        <text
          x="150"
          y="75"
          textAnchor="middle"
          className="font-bangers"
          fontSize="48"
          fill="#FF4141"
          transform="translate(4, 4)"
          style={{ fontFamily: 'var(--font-bangers)' }}
        >
          SOUND
        </text>
        <text
          x="150"
          y="115"
          textAnchor="middle"
          className="font-bangers"
          fontSize="54"
          fill="#FF4141"
          transform="translate(4, 4)"
          style={{ fontFamily: 'var(--font-bangers)' }}
        >
          SKETCH
        </text>

        {/* Main Text (Yellow) */}
        <text
          x="150"
          y="75"
          textAnchor="middle"
          className="font-bangers"
          fontSize="48"
          fill="#FFE600"
          stroke="black"
          strokeWidth="2"
          style={{ fontFamily: 'var(--font-bangers)' }}
        >
          SOUND
        </text>
        <text
          x="150"
          y="115"
          textAnchor="middle"
          className="font-bangers"
          fontSize="54"
          fill="#FFE600"
          stroke="black"
          strokeWidth="2"
          style={{ fontFamily: 'var(--font-bangers)' }}
        >
          SKETCH
        </text>

        {/* Decorative Stars */}
        <path d="M260 30 L265 40 L275 42 L267 48 L270 58 L260 52 L250 58 L253 48 L245 42 L255 40 Z" fill="#FFE600" stroke="black" />
        <path d="M40 110 L45 120 L55 122 L47 128 L50 138 L40 132 L30 138 L33 128 L25 122 L35 120 Z" fill="#FFE600" stroke="black" />
      </svg>
    </div>
  );
}
