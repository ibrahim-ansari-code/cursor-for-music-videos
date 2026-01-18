"use client";

import React, { useState, useEffect } from "react";
import AudioLoader from "@/components/AudioLoader";
import Link from "next/link";
import Logo from "@/components/Logo";

export default function AudiobookPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate generation time
    const timer = setTimeout(() => {
      setLoading(false);
    }, 4500);

    return () => clearTimeout(timer);
  }, []);

  return (
    <main className="min-h-screen p-8 md:p-16 flex flex-col items-center">
      <header className="w-full max-w-6xl flex justify-between items-center mb-12">
        <Link 
          href="/" 
          className="bg-comic-red text-white comic-button text-sm flex items-center space-x-2 transform -rotate-2"
        >
          <span>← BACK TO STUDIO</span>
        </Link>
        <div className="flex flex-col items-center">
          <Logo className="w-24 md:w-32 mb-2" />
          <h2 className="font-bangers text-4xl text-black">AUDIOBOOK OUTPUT</h2>
        </div>
        <div className="w-24 h-4 bg-comic-blue comic-border rotate-3 hidden md:block" />
      </header>

      <div className="w-full max-w-4xl">
        {loading ? (
          <div className="py-20">
            <AudioLoader />
          </div>
        ) : (
          <div className="space-y-12 animate-in fade-in zoom-in duration-500">
            {/* Record Cover Style Player */}
            <div className="bg-white p-8 md:p-12 comic-border rounded-3xl shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] flex flex-col md:flex-row items-center gap-12">
              
              {/* "Album Art" Placeholder */}
              <div className="w-64 h-64 bg-comic-bg comic-border rounded-xl flex items-center justify-center relative overflow-hidden group">
                <div className="absolute inset-0 bg-comic-blue/5 group-hover:bg-comic-blue/10 transition-colors" />
                <Logo variant="icon" className="w-32 h-32 text-comic-blue opacity-20 transform -rotate-12" />
                <div className="absolute top-4 left-4 bg-comic-red text-white font-bangers px-3 py-1 text-lg transform -rotate-6">
                  VOICE AI
                </div>
                <div className="absolute bottom-4 right-4 bg-comic-yellow text-black font-bangers px-3 py-1 text-lg transform rotate-3">
                  STORY-1
                </div>
              </div>

              {/* Player Controls Placeholder */}
              <div className="flex-1 w-full space-y-8">
                <div>
                  <h3 className="font-bangers text-4xl mb-2 text-comic-blue">YOUR GENERATED MASTERPIECE</h3>
                  <p className="font-comic text-gray-600 italic">Synthesized from your image series.</p>
                </div>

                {/* Fake Progress Bar */}
                <div className="space-y-2">
                  <div className="h-4 w-full bg-gray-100 comic-border rounded-full overflow-hidden">
                    <div className="h-full w-1/3 bg-comic-red animate-pulse" />
                  </div>
                  <div className="flex justify-between font-comic font-bold text-xs">
                    <span>04:12</span>
                    <span>12:45</span>
                  </div>
                </div>

                {/* Fake Controls */}
                <div className="flex items-center justify-center space-x-6">
                  <button className="w-12 h-12 bg-white comic-border rounded-full flex items-center justify-center hover:bg-gray-50 active:translate-y-1 transition-all">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                  </button>
                  <button className="w-20 h-20 bg-comic-red text-white comic-border rounded-full flex items-center justify-center hover:bg-red-500 active:scale-95 transition-all shadow-lg">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 ml-1" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  </button>
                  <button className="w-12 h-12 bg-white comic-border rounded-full flex items-center justify-center hover:bg-gray-50 active:translate-y-1 transition-all">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <div className="flex flex-col md:flex-row justify-center gap-6 pt-8">
              <button className="bg-comic-yellow comic-button text-2xl px-12 py-4 flex items-center space-x-3">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span>DOWNLOAD AUDIO (MP3)</span>
              </button>
              <button className="bg-white comic-button text-2xl px-12 py-4 text-gray-500">
                SHARE STORY
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Decorative floating elements */}
      <div className="fixed top-20 right-[-30px] w-24 h-24 bg-comic-blue rounded-full opacity-5 blur-2xl -z-10" />
      <div className="fixed bottom-20 left-[-30px] w-32 h-32 bg-comic-red rounded-full opacity-5 blur-2xl -z-10" />
    </main>
  );
}
