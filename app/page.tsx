"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import UploadBox from "@/components/UploadBox";
import Logo from "@/components/Logo";

export default function Home() {
  const router = useRouter();
  
  // State for Module A: Audio to Comic
  const [audioFile, setAudioFile] = useState<File | null>(null);
  
  // State for Module B: Images to Audiobook
  const [imageFiles, setImageFiles] = useState<File[]>([]);

  const handleComicSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (audioFile) {
      // TODO: integrate backend call for audio-to-comic
      console.log("Generating Comic from:", audioFile.name);
      router.push("/comic");
    }
  };

  const handleAudioSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (imageFiles.length > 0) {
      // TODO: integrate backend call for images-to-audiobook
      console.log("Generating Audiobook from:", imageFiles.length, "images");
      router.push("/audiobook");
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-start p-6 sm:p-12 md:p-24 relative overflow-x-hidden">
      {/* Brand Badge */}
      <div className="absolute top-6 left-6 md:top-12 md:left-12 z-50">
        <Logo className="w-32 md:w-48 transform -rotate-3 hover:rotate-0 transition-transform cursor-pointer" />
      </div>

      {/* Decorative Accents */}
      <div className="absolute top-[-5%] right-[-5%] w-[30%] h-[30%] bg-comic-yellow opacity-10 rounded-full blur-3xl -z-10" />
      <div className="absolute bottom-[-5%] left-[-5%] w-[30%] h-[30%] bg-comic-blue opacity-10 rounded-full blur-3xl -z-10" />

      <div className="z-10 w-full max-w-6xl flex flex-col items-center text-center mt-16 md:mt-0">
        <header className="mb-16 space-y-4">
          <h1 className="font-bangers text-5xl md:text-7xl lg:text-8xl text-black tracking-tight leading-tight">
            THE ULTIMATE <span className="text-comic-red">COMIC</span> <br className="hidden md:block" />
            & <span className="text-comic-blue underline decoration-8">AUDIO</span> STUDIO
          </h1>
          <p className="font-comic text-lg md:text-xl text-gray-700 max-w-2xl mx-auto">
            Two powerful tools, one comic-book style studio. <br className="hidden md:block" />
            Choose your mission below and let the AI do the heavy lifting!
          </p>
        </header>

        {/* Dual Module Grid */}
        <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-16 items-stretch">
          
          {/* Module 1: Audio to Comic */}
          <section className="flex flex-col space-y-6">
            <div className="flex-1">
              <UploadBox
                title="AUDIO TO COMIC"
                description="Upload an audiobook file and we'll visualize it into a stunning comic book format."
                accept="audio/*"
                accentColor="bg-comic-yellow"
                onFilesSelect={(files) => setAudioFile(files[0] || null)}
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                }
              />
            </div>
            <button
              onClick={handleComicSubmit}
              disabled={!audioFile}
              className={`w-full text-xl h-14 flex items-center justify-center space-x-3 ${
                audioFile 
                  ? "bg-comic-yellow text-black hover:bg-yellow-400" 
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
              } comic-button`}
            >
              <span>{audioFile ? "POW! GENERATE COMIC" : "SELECT AUDIO"}</span>
            </button>
          </section>

          {/* Module 2: PNGs to Audiobook */}
          <section className="flex flex-col space-y-6">
            <div className="flex-1">
              <UploadBox
                title="IMAGES TO AUDIO"
                description="Upload a series of images (PNG/JPG) and we'll weave them into an immersive audiobook."
                accept="image/png, image/jpeg"
                multiple={true}
                accentColor="bg-comic-blue"
                onFilesSelect={(files) => setImageFiles(files)}
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                }
              />
            </div>
            <button
              onClick={handleAudioSubmit}
              disabled={imageFiles.length === 0}
              className={`w-full text-xl h-14 flex items-center justify-center space-x-3 ${
                imageFiles.length > 0 
                  ? "bg-comic-blue text-white hover:bg-blue-600" 
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
              } comic-button`}
            >
              <span>{imageFiles.length > 0 ? "BAM! GENERATE AUDIO" : "SELECT IMAGES"}</span>
            </button>
          </section>

        </div>

      </div>
    </main>
  );
}
