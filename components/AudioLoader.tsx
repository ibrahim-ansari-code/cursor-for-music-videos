"use client";

import React from "react";

export default function AudioLoader() {
  return (
    <div className="flex flex-col items-center justify-center space-y-8 p-12">
      <div className="relative">
        {/* Animated Speech Bubble / Sound Wave Container */}
        <div className="bg-white p-8 rounded-3xl comic-border relative animate-pulse shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
          <p className="font-bangers text-3xl md:text-5xl text-comic-blue tracking-wider text-center">
            MIXING YOUR <br /> AUDIOBOOK...
          </p>
          
          {/* Animated Equalizer Bars */}
          <div className="flex items-end justify-center space-x-2 mt-6 h-12">
            {[0, 1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="w-3 bg-comic-red border-2 border-black rounded-t"
                style={{
                  height: `${Math.random() * 100}%`,
                  animation: `bounce-height 0.5s ease-in-out infinite alternate ${i * 0.1}s`
                }}
              />
            ))}
          </div>

          {/* Bubble tail - comic style */}
          <div className="absolute -bottom-4 right-10 w-0 h-0 border-l-[15px] border-l-transparent border-r-[15px] border-r-transparent border-t-[20px] border-t-black"></div>
          <div className="absolute -bottom-[12px] right-[42px] w-0 h-0 border-l-[13px] border-l-transparent border-r-[13px] border-r-transparent border-t-[18px] border-t-white"></div>
        </div>
      </div>

      <div className="flex flex-col items-center space-y-4">
        <p className="font-comic font-bold text-gray-500 italic">"Patience is a virtue, especially for listeners..."</p>
        <div className="flex space-x-3">
          <div className="w-4 h-4 bg-comic-blue rounded-full comic-border animate-bounce" style={{ animationDelay: "0s" }}></div>
          <div className="w-4 h-4 bg-comic-yellow rounded-full comic-border animate-bounce" style={{ animationDelay: "0.2s" }}></div>
          <div className="w-4 h-4 bg-comic-red rounded-full comic-border animate-bounce" style={{ animationDelay: "0.4s" }}></div>
        </div>
      </div>

      <style jsx>{`
        @keyframes bounce-height {
          from { height: 20%; }
          to { height: 100%; }
        }
      `}</style>
    </div>
  );
}
