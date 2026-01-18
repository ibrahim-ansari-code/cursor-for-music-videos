"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import UrlInputBox from "@/components/UrlInputBox";
import Logo from "@/components/Logo";
import StickerPeel from "@/components/StickerPeel";

export default function Home() {
  const router = useRouter();
  
  // State for Module A: Audio to Comic
  const [audioUrl, setAudioUrl] = useState<string>("");
  const [isAudioUrlValid, setIsAudioUrlValid] = useState<boolean>(false);
  
  // State for Module B: Images to Audiobook
  const [imageUrls, setImageUrls] = useState<string[]>([]);
  const [areImageUrlsValid, setAreImageUrlsValid] = useState<boolean>(false);

  const handleComicSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (audioUrl && isAudioUrlValid) {
      // TODO: integrate backend call for audio-to-comic
      console.log("Generating Comic from audio URL:", audioUrl);
      router.push("/comic");
    }
  };

  const handleAudioSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (imageUrls.length > 0 && areImageUrlsValid) {
      // TODO: integrate backend call for images-to-audiobook
      console.log("Generating Audiobook from:", imageUrls.length, "image URLs");
      router.push("/audiobook");
    }
  };

  const handleAudioUrlChange = (url: string | string[]) => {
    setAudioUrl(url as string);
  };

  const handleImageUrlsChange = (urls: string | string[]) => {
    setImageUrls(urls as string[]);
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-start p-6 sm:p-12 md:p-24 relative overflow-x-hidden">
      {/* Brand Badge */}
      <div className="absolute top-6 left-6 md:top-12 md:left-12 z-50">
        <Logo className="w-32 md:w-48 transform -rotate-3 hover:rotate-0 transition-transform cursor-pointer" />
      </div>

      <div className="z-10 w-full max-w-6xl flex flex-col items-center text-center mt-16 md:mt-0">
        <header className="mb-16 space-y-4">
          <h1 className="font-bangers text-5xl md:text-7xl lg:text-8xl text-black tracking-tight leading-tight">
            <span className="relative inline-block">
              THE
              <div className="absolute top-0 -left-[180px] w-32 h-32 z-50 flex items-center justify-center">
                <StickerPeel
                  imageSrc="/Whack.png"
                  width={110}
                  rotate={-15}
                  peelBackHoverPct={20}
                  peelBackActivePct={40}
                  shadowIntensity={0.6}
                  lightingIntensity={0.1}
                  initialPosition={{ x: 0, y: 0 }}
                />
              </div>
            </span> ULTIMATE <span className="relative inline-block text-comic-red">
              COMIC
              <div className="absolute top-[-80px] left-[200px] w-32 h-32 z-50 flex items-center justify-center">
                <StickerPeel
                  imageSrc="/Zap.png"
                  width={110}
                  rotate={20}
                  peelBackHoverPct={20}
                  peelBackActivePct={40}
                  shadowIntensity={0.6}
                  lightingIntensity={0.1}
                  initialPosition={{ x: 0, y: 0 }}
                />
              </div>
            </span> <br className="hidden md:block" />
            <span className="relative inline-block">
              &
              <div className="absolute top-[36px] -left-[350px] w-32 h-32 z-[60] flex items-center justify-center">
                <StickerPeel
                  imageSrc="/Click%20Me.png"
                  width={110}
                  rotate={12}
                  peelBackHoverPct={20}
                  peelBackActivePct={40}
                  shadowIntensity={0.6}
                  lightingIntensity={0.1}
                  initialPosition={{ x: 0, y: 0 }}
                />
              </div>
              <div className="absolute top-0 -left-[180px] w-32 h-32 z-[60] flex items-center justify-center">
                <StickerPeel
                  imageSrc="/Ouch.png"
                  width={110}
                  rotate={-10}
                  peelBackHoverPct={20}
                  peelBackActivePct={40}
                  shadowIntensity={0.6}
                  lightingIntensity={0.1}
                  initialPosition={{ x: 0, y: 0 }}
                />
              </div>
            </span> <span className="text-comic-blue underline decoration-8">AUDIO</span>{' '}
            <span className="relative inline-block">
              STUDIO
              <div className="absolute -top-16 right-[-348px] w-32 h-32 z-50 flex items-center justify-center">
                <StickerPeel
                  imageSrc="/sticker.png"
                  width={110}
                  rotate={12}
                  peelBackHoverPct={20}
                  peelBackActivePct={40}
                  shadowIntensity={0.6}
                  lightingIntensity={0.1}
                  initialPosition={{ x: 0, y: 0 }}
                />
              </div>
              <div className="absolute top-[36px] right-[-248px] w-32 h-32 z-50 flex items-center justify-center">
                <StickerPeel
                  imageSrc="/Boom.png"
                  width={110}
                  rotate={-8}
                  peelBackHoverPct={20}
                  peelBackActivePct={40}
                  shadowIntensity={0.6}
                  lightingIntensity={0.1}
                  initialPosition={{ x: 0, y: 0 }}
                />
              </div>
            </span>
          </h1>
          <p className="font-comic text-lg md:text-xl text-gray-700 max-w-2xl mx-auto">
            Two powerful tools, one comic-book style studio. <br className="hidden md:block" />
            Choose your mission below and let the AI do the heavy <span className="relative inline-block">
              lifting!
              <div className="absolute top-[-40px] left-[300px] w-32 h-32 z-50 flex items-center justify-center">
                <StickerPeel
                  imageSrc="/Wham.png"
                  width={110}
                  rotate={15}
                  peelBackHoverPct={20}
                  peelBackActivePct={40}
                  shadowIntensity={0.6}
                  lightingIntensity={0.1}
                  initialPosition={{ x: 0, y: 0 }}
                />
              </div>
            </span>
          </p>
        </header>

        {/* Dual Module Grid */}
        <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-16 items-stretch">
          
          {/* Module 1: Audio to Comic */}
          <section className="flex flex-col space-y-6">
            <div className="flex-1">
              <UrlInputBox
                title="AUDIO TO COMIC"
                description="Paste an audiobook URL and we'll visualize it into a stunning comic book format."
                accentColor="bg-comic-yellow"
                onUrlChange={handleAudioUrlChange}
                onValidationChange={setIsAudioUrlValid}
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                }
              />
            </div>
            <button
              onClick={handleComicSubmit}
              disabled={!audioUrl || !isAudioUrlValid}
              className={`w-full text-xl h-14 flex items-center justify-center space-x-3 ${
                audioUrl && isAudioUrlValid
                  ? "bg-comic-yellow text-black hover:bg-yellow-400" 
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
              } comic-button`}
            >
              <span>{audioUrl && isAudioUrlValid ? "POW! GENERATE COMIC" : !audioUrl ? "ENTER AUDIO URL" : "FIX INVALID URL"}</span>
            </button>
          </section>

          {/* Module 2: PNGs to Audiobook */}
          <section className="flex flex-col space-y-6">
            <div className="flex-1">
              <UrlInputBox
                title="IMAGES TO AUDIO"
                description="Paste a series of image URLs (PNG/JPG) and we'll weave them into an immersive audiobook."
                multiple={true}
                accentColor="bg-comic-blue"
                onUrlChange={handleImageUrlsChange}
                onValidationChange={setAreImageUrlsValid}
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                }
              />
            </div>
            <button
              onClick={handleAudioSubmit}
              disabled={imageUrls.length === 0 || !areImageUrlsValid}
              className={`w-full text-xl h-14 flex items-center justify-center space-x-3 ${
                imageUrls.length > 0 && areImageUrlsValid
                  ? "bg-comic-blue text-white hover:bg-blue-600" 
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
              } comic-button`}
            >
              <span>{imageUrls.length > 0 && areImageUrlsValid ? "BAM! GENERATE AUDIO" : imageUrls.length === 0 ? "ENTER IMAGE URLS" : "FIX INVALID URLS"}</span>
            </button>
          </section>

        </div>

      </div>
    </main>
  );
}
