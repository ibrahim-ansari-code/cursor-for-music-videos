"use client";

import React from "react";
import Logo from "./Logo";

export default function ComicLoader() {
  return (
    <div className="flex flex-col items-center justify-center space-y-8 p-12 relative overflow-hidden">
      <div className="relative z-10">
        {/* Animated Speech Bubble */}
        <div className="bg-white p-6 rounded-3xl comic-border relative animate-bounce flex items-center space-x-4">
          <Logo variant="icon" className="w-8 h-8 text-comic-red" />
          <p className="font-bangers text-3xl md:text-5xl text-comic-red tracking-wider">
            Generating your comic...
          </p>
          <Logo variant="icon" className="w-8 h-8 text-comic-red transform scale-x-[-1]" />
          
          {/* Bubble tail */}
          <div className="absolute -bottom-4 left-10 w-0 h-0 border-l-[15px] border-l-transparent border-r-[15px] border-r-transparent border-t-[20px] border-t-black"></div>
          <div className="absolute -bottom-[12px] left-[42px] w-0 h-0 border-l-[13px] border-l-transparent border-r-[13px] border-r-transparent border-t-[18px] border-t-white"></div>
        </div>
      </div>

      <div className="flex items-center space-x-4 z-10">
        <div className="w-6 h-6 bg-comic-yellow rounded-full comic-border animate-ping" style={{ animationDelay: "0s" }}></div>
        <div className="w-6 h-6 bg-comic-red rounded-full comic-border animate-ping" style={{ animationDelay: "0.2s" }}></div>
        <div className="w-6 h-6 bg-comic-blue rounded-full comic-border animate-ping" style={{ animationDelay: "0.4s" }}></div>
      </div>

      <div className="grid grid-cols-2 gap-4 opacity-30 z-10">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="w-32 h-40 bg-gray-200 rounded comic-border flex items-center justify-center animate-pulse"
          >
            <div className="relative">
              <Logo variant="minimal" className="w-12 h-12 text-gray-400 opacity-20" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
