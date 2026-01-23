"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Logo from "@/components/Logo";
import StickerPeel from "@/components/StickerPeel";

export default function Home() {
  const router = useRouter();
  
  // State for Module A: Audio to Comic - now supports file upload
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioUrl, setAudioUrl] = useState<string>("");
  const [inputMode, setInputMode] = useState<'file' | 'url'>('file');
  const audioInputRef = useRef<HTMLInputElement>(null);
  
  // State for Module B: Images to Audiobook
  const [imageUrls, setImageUrls] = useState<string[]>([""]);
  const [imageErrors, setImageErrors] = useState<boolean[]>([false]);

  // Validation
  const isValidUrl = (url: string) => {
    if (!url.trim()) return true;
    try {
      const parsedUrl = new URL(url);
      return parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:";
    } catch {
      return false;
    }
  };

  const isAudioValid = inputMode === 'file' ? audioFile !== null : (audioUrl.trim() !== "" && isValidUrl(audioUrl));
  const areImageUrlsValid = imageUrls.some(u => u.trim() !== "") && imageUrls.every(u => u.trim() === "" || isValidUrl(u));

  const handleAudioFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAudioFile(file);
    }
  };

  const handleComicSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isAudioValid) {
      // Store the file or URL in sessionStorage for the comic page
      if (inputMode === 'file' && audioFile) {
        // Store file info - we'll use a temporary approach with FileReader
        const reader = new FileReader();
        reader.onload = () => {
          sessionStorage.setItem('audioData', JSON.stringify({
            type: 'file',
            name: audioFile.name,
            data: reader.result,
            mimeType: audioFile.type
          }));
          router.push("/comic");
        };
        reader.readAsDataURL(audioFile);
      } else if (inputMode === 'url' && audioUrl) {
        sessionStorage.setItem('audioData', JSON.stringify({
          type: 'url',
          url: audioUrl
        }));
        router.push("/comic");
      }
    }
  };

  const handleAudioSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (areImageUrlsValid) {
      const validUrls = imageUrls.filter(u => u.trim() !== "");
      sessionStorage.setItem('imageUrls', JSON.stringify(validUrls));
      router.push("/audiobook");
    }
  };

  const handleImageUrlChange = (index: number, value: string) => {
    const newUrls = [...imageUrls];
    newUrls[index] = value;
    setImageUrls(newUrls);

    const newErrors = [...imageErrors];
    newErrors[index] = !isValidUrl(value);
    setImageErrors(newErrors);
  };

  const addImageField = () => {
    setImageUrls([...imageUrls, ""]);
    setImageErrors([...imageErrors, false]);
  };

  const removeImageField = (index: number) => {
    if (imageUrls.length > 1) {
      setImageUrls(imageUrls.filter((_, i) => i !== index));
      setImageErrors(imageErrors.filter((_, i) => i !== index));
    } else {
      setImageUrls([""]);
      setImageErrors([false]);
    }
  };

  const removeAudioFile = () => {
    setAudioFile(null);
    if (audioInputRef.current) {
      audioInputRef.current.value = '';
    }
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
              <span className="absolute top-0 -left-[180px] w-32 h-32 z-50 flex items-center justify-center">
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
              </span>
            </span> ULTIMATE <span className="relative inline-block text-comic-red">
              COMIC
              <span className="absolute top-[-80px] left-[200px] w-32 h-32 z-50 flex items-center justify-center">
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
              </span>
            </span> <br className="hidden md:block" />
            <span className="relative inline-block">
              &
              <span className="absolute top-[236px] -left-[250px] w-32 h-32 z-[60] flex items-center justify-center">
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
              </span>
              <span className="absolute top-0 -left-[180px] w-32 h-32 z-[60] flex items-center justify-center">
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
              </span>
            </span> <span className="text-comic-blue underline decoration-8">AUDIO</span>{' '}
            <span className="relative inline-block">
              STUDIO
              <span className="absolute -top-16 right-[-348px] w-32 h-32 z-50 flex items-center justify-center">
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
              </span>
              <span className="absolute top-[36px] right-[-248px] w-32 h-32 z-50 flex items-center justify-center">
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
              </span>
            </span>
          </h1>
          <div className="font-comic text-lg md:text-xl text-gray-700 max-w-2xl mx-auto">
            Two powerful tools, one comic-book style studio. <br className="hidden md:block" />
            Choose your mission below and let the AI do the heavy <span className="relative inline-block">
              lifting!
              <span className="absolute top-[-40px] left-[300px] w-32 h-32 z-50 flex items-center justify-center">
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
              </span>
            </span>
          </div>
        </header>

        {/* Dual Module Grid */}
        <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-16 items-stretch">
          
          {/* Module 1: Audio to Comic */}
          <section className="flex flex-col space-y-6">
            <div className="relative w-full p-8 bg-white comic-border rounded-2xl transition-all h-full flex flex-col">
              <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-black/20 rounded-xl p-6 bg-comic-bg/30">
                <div className="w-16 h-16 bg-comic-yellow rounded-full flex items-center justify-center mb-4 comic-border transform -rotate-3">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </div>

                <h3 className="font-bangers text-2xl mb-1 text-black">AUDIO TO COMIC</h3>
                <p className="font-comic text-center text-sm text-gray-600 mb-4 px-4">
                  Upload an audio file or paste a URL and we&apos;ll visualize it into a stunning comic book format.
                </p>

                {/* Mode Toggle */}
                <div className="flex space-x-2 mb-4">
                  <button
                    type="button"
                    onClick={() => setInputMode('file')}
                    className={`px-4 py-2 font-comic text-sm comic-border rounded-lg transition-all ${
                      inputMode === 'file' 
                        ? 'bg-comic-yellow text-black' 
                        : 'bg-white text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    Upload File
                  </button>
                  <button
                    type="button"
                    onClick={() => setInputMode('url')}
                    className={`px-4 py-2 font-comic text-sm comic-border rounded-lg transition-all ${
                      inputMode === 'url' 
                        ? 'bg-comic-yellow text-black' 
                        : 'bg-white text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    Paste URL
                  </button>
                </div>

                <div className="w-full">
                  {inputMode === 'file' ? (
                    <>
                      <input
                        ref={audioInputRef}
                        type="file"
                        accept="audio/mpeg,audio/mp3,audio/wav,audio/x-wav,audio/m4a,.mp3,.wav,.m4a"
                        onChange={handleAudioFileChange}
                        className="hidden"
                        id="audio-upload"
                      />
                      {audioFile ? (
                        <div className="flex items-center justify-between p-4 bg-comic-yellow/20 comic-border rounded-lg">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-comic-yellow rounded-full flex items-center justify-center comic-border">
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                              </svg>
                            </div>
                            <div className="text-left">
                              <p className="font-comic text-sm font-bold text-black truncate max-w-[180px]">
                                {audioFile.name}
                              </p>
                              <p className="font-comic text-xs text-gray-500">
                                {(audioFile.size / (1024 * 1024)).toFixed(2)} MB
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={removeAudioFile}
                            className="w-8 h-8 flex items-center justify-center bg-comic-red text-white comic-border rounded-full hover:brightness-110 transition-all"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ) : (
                        <label
                          htmlFor="audio-upload"
                          className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-black/30 rounded-lg cursor-pointer hover:border-black/50 hover:bg-comic-yellow/10 transition-all"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-gray-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                          </svg>
                          <span className="font-comic text-sm text-gray-600">Click to upload audio</span>
                          <span className="font-comic text-xs text-gray-400 mt-1">MP3, WAV, or M4A</span>
                        </label>
                      )}
                    </>
                  ) : (
                    <input
                      type="text"
                      value={audioUrl}
                      onChange={(e) => setAudioUrl(e.target.value)}
                      placeholder="Paste audio URL here..."
                      className={`w-full p-4 font-comic text-sm comic-border rounded-lg focus:ring-2 focus:ring-black/5 outline-none ${
                        audioUrl && !isValidUrl(audioUrl) ? 'border-comic-red' : ''
                      }`}
                    />
                  )}
                </div>
              </div>

              {/* Decorative corner elements */}
              <div className="absolute top-3 right-3 flex space-x-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-comic-red border border-black" />
                <div className="w-2.5 h-2.5 rounded-full bg-comic-blue border border-black" />
              </div>
            </div>
            <button
              onClick={handleComicSubmit}
              disabled={!isAudioValid}
              className={`w-full text-xl h-14 flex items-center justify-center space-x-3 ${
                isAudioValid
                  ? "bg-comic-yellow text-black hover:bg-yellow-400" 
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
              } comic-button`}
            >
              <span>{isAudioValid ? "POW! GENERATE COMIC" : inputMode === 'file' ? "UPLOAD AUDIO FILE" : "ENTER AUDIO URL"}</span>
            </button>
          </section>

          {/* Module 2: PNGs to Audiobook */}
          <section className="flex flex-col space-y-6">
            <div className="relative w-full p-8 bg-white comic-border rounded-2xl transition-all h-full flex flex-col">
              <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-black/20 rounded-xl p-6 bg-comic-bg/30">
                <div className="w-16 h-16 bg-comic-blue rounded-full flex items-center justify-center mb-4 comic-border transform -rotate-3">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                </div>

                <h3 className="font-bangers text-2xl mb-1 text-black">IMAGES TO AUDIO</h3>
                <p className="font-comic text-center text-sm text-gray-600 mb-6 px-4">
                  Paste a series of image URLs (PNG/JPG) and we&apos;ll weave them into an immersive audiobook.
                </p>

                <div className="w-full space-y-3">
                  <div className="max-h-48 overflow-y-auto w-full space-y-3 pr-2 scrollbar-thin scrollbar-thumb-gray-300">
                    {imageUrls.map((url, index) => (
                      <div key={index} className="flex flex-col space-y-1">
                        <div className="flex items-center space-x-2">
                          <input
                            type="text"
                            value={url}
                            onChange={(e) => handleImageUrlChange(index, e.target.value)}
                            placeholder={`Image URL #${index + 1}`}
                            className={`flex-1 p-3 font-comic text-sm comic-border rounded-lg focus:ring-2 focus:ring-black/5 outline-none ${imageErrors[index] ? 'border-comic-red' : ''}`}
                          />
                          <button
                            type="button"
                            onClick={() => removeImageField(index)}
                            className="w-10 h-10 flex flex-shrink-0 items-center justify-center bg-comic-red text-white comic-border rounded-lg hover:brightness-110 active:translate-y-0.5 transition-all"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                        {imageErrors[index] && (
                          <p className="text-comic-red text-[10px] font-bold px-1 uppercase tracking-tight">
                            Invalid URL! Check your link.
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={addImageField}
                    className="w-full py-2 flex items-center justify-center space-x-2 bg-white comic-border rounded-lg font-comic text-sm hover:bg-gray-50 active:translate-y-0.5 transition-all mt-2"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    <span>ADD ANOTHER URL</span>
                  </button>
                </div>
              </div>

              {/* Decorative corner elements */}
              <div className="absolute top-3 right-3 flex space-x-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-comic-red border border-black" />
                <div className="w-2.5 h-2.5 rounded-full bg-comic-blue border border-black" />
              </div>
            </div>
            <button
              onClick={handleAudioSubmit}
              disabled={!areImageUrlsValid}
              className={`w-full text-xl h-14 flex items-center justify-center space-x-3 ${
                areImageUrlsValid
                  ? "bg-comic-blue text-white hover:bg-blue-600" 
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
              } comic-button`}
            >
              <span>{areImageUrlsValid ? "BAM! GENERATE AUDIO" : "ENTER IMAGE URLS"}</span>
            </button>
          </section>

        </div>

      </div>
    </main>
  );
}
