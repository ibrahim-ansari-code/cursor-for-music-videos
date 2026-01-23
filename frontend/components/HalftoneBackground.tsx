"use client";

import React from "react";

const HalftoneBlob: React.FC<{ className?: string }> = ({ className }) => (
  <div className={`absolute w-72 h-72 pointer-events-none ${className}`}>
    <div 
      className="w-full h-full" 
      style={{
        backgroundImage: 'radial-gradient(var(--halftone-blob-color) 2.5px, transparent 2.5px)',
        backgroundSize: '10px 10px',
        WebkitMaskImage: 'radial-gradient(circle at center, black 0%, transparent 75%)',
        maskImage: 'radial-gradient(circle at center, black 0%, transparent 75%)',
      }} 
    />
  </div>
);

const HalftoneBackground: React.FC = () => {
  return (
    <div className="halftone-bg bg-[var(--background)]">
      {/* Background Glows */}
      <div className="absolute top-[-5%] right-[-5%] w-[40%] h-[40%] bg-comic-yellow opacity-[0.08] rounded-full blur-3xl" />
      <div className="absolute bottom-[-5%] left-[-5%] w-[40%] h-[40%] bg-comic-blue opacity-[0.08] rounded-full blur-3xl" />

      {/* Main Dotted Background */}
      <div 
        className="absolute inset-0 halftone-dot-pattern opacity-50" 
        style={{
          WebkitMaskImage: "radial-gradient(circle at center, black 0%, transparent 90%)",
          maskImage: "radial-gradient(circle at center, black 0%, transparent 90%)",
        }}
      />
      
      {/* Darker Radial Halftone Blobs */}
      <HalftoneBlob className="top-[10%] left-[5%] scale-90 opacity-60 rotate-45" />
      <HalftoneBlob className="top-[55%] right-[10%] scale-125 opacity-50 -rotate-12" />
      <HalftoneBlob className="bottom-[5%] left-[15%] scale-100 opacity-60" />
      <HalftoneBlob className="top-[35%] left-[45%] scale-150 opacity-30 rotate-90" />

      {/* Comic-style SVG Grain Texture */}
      <svg className="absolute inset-0 w-full h-full opacity-[0.04]" xmlns="http://www.w3.org/2000/svg">
        <filter id="halftone-noise">
          <feTurbulence type="fractalNoise" baseFrequency="0.6" numOctaves="2" stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncR type="discrete" tableValues="0 1" />
            <feFuncG type="discrete" tableValues="0 1" />
            <feFuncB type="discrete" tableValues="0 1" />
          </feComponentTransfer>
        </filter>
        <rect width="100%" height="100%" filter="url(#halftone-noise)" />
      </svg>
    </div>
  );
};

export default HalftoneBackground;
