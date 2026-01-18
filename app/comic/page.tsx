"use client";

import React, { useState, useEffect } from "react";
import ComicLoader from "@/components/ComicLoader";
import Link from "next/link";
import Logo from "@/components/Logo";

export default function ComicPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate generation time
    const timer = setTimeout(() => {
      setLoading(false);
    }, 4000);

    return () => clearTimeout(timer);
  }, []);

  return (
    <main className="min-h-screen p-8 md:p-16 flex flex-col items-center">
      <header className="w-full max-w-6xl flex justify-between items-center mb-12">
        <Link 
          href="/" 
          className="bg-comic-yellow text-black comic-button text-sm flex items-center space-x-2 transform -rotate-2"
        >
          <span>← BACK TO STUDIO</span>
        </Link>
        <div className="flex flex-col items-center">
          <Logo className="w-24 md:w-32 mb-2" />
          <h2 className="font-bangers text-4xl text-black">COMIC OUTPUT</h2>
        </div>
        <div className="w-24 h-4 bg-comic-red comic-border rotate-3 hidden md:block" />
      </header>

      <div className="w-full max-w-6xl">
        {loading ? (
          <div className="py-20">
            <ComicLoader />
          </div>
        ) : (
          <div className="space-y-12 animate-in fade-in zoom-in duration-500">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {/* TODO: integrate backend call to fetch actual comic pages */}
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div 
                  key={i} 
                  className="bg-white p-4 comic-border rounded-lg group cursor-pointer shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transition-all"
                >
                  <div className="aspect-[3/4] bg-gray-100 rounded flex items-center justify-center mb-4 overflow-hidden relative">
                    <span className="font-bangers text-6xl text-gray-200 z-0">{i}</span>
                    <div className="absolute inset-0 bg-comic-yellow opacity-0 group-hover:opacity-10 transition-opacity" />
                    <div className="absolute bottom-2 right-2 bg-comic-red text-white font-bangers px-2 py-1 text-sm transform rotate-2">
                      PAGE {i}
                    </div>
                  </div>
                  <div className="h-4 w-3/4 bg-gray-200 rounded animate-pulse mb-2" />
                  <div className="h-4 w-1/2 bg-gray-100 rounded animate-pulse" />
                </div>
              ))}
            </div>

            <div className="flex justify-center pt-8">
              <button className="bg-comic-yellow comic-button text-2xl px-12 py-4 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
                DOWNLOAD FULL COMIC (PDF)
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Decorative floating elements */}
      <div className="fixed top-20 right-[-30px] w-24 h-24 bg-comic-red rounded-full opacity-5 blur-2xl -z-10" />
      <div className="fixed bottom-20 left-[-30px] w-32 h-32 bg-comic-yellow rounded-full opacity-5 blur-2xl -z-10" />
    </main>
  );
}
