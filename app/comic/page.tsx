"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import Logo from "@/components/Logo";
import ComicLoader from "@/components/ComicLoader";
import { 
  generateComicFromAudio, 
  base64ToImageUrl, 
  downloadPanel,
  type ComicPanel,
  type GenerationProgress,
  type ComicGenerationResponse
} from "@/lib/api";

type GenerationStage = 'loading' | 'transcribing' | 'generating' | 'complete' | 'error';

export default function ComicPage() {
  const [stage, setStage] = useState<GenerationStage>('loading');
  const [progress, setProgress] = useState<GenerationProgress | null>(null);
  const [panels, setPanels] = useState<ComicPanel[]>([]);
  const [error, setError] = useState<string>("");
  const [metadata, setMetadata] = useState<{ title?: string; chapter?: string } | null>(null);
  const [selectedPanel, setSelectedPanel] = useState<ComicPanel | null>(null);

  const processAudio = useCallback(async () => {
    try {
      // Get audio data from sessionStorage
      const audioDataStr = sessionStorage.getItem('audioData');
      if (!audioDataStr) {
        setError("No audio data found. Please go back and upload an audio file.");
        setStage('error');
        return;
      }

      const audioData = JSON.parse(audioDataStr);
      
      // Convert data URL back to File if it's a file upload
      let file: File;
      if (audioData.type === 'file') {
        // Convert base64 data URL to File
        const response = await fetch(audioData.data);
        const blob = await response.blob();
        file = new File([blob], audioData.name, { type: audioData.mimeType || 'audio/mpeg' });
      } else if (audioData.type === 'url') {
        // For URL, we would need to handle this differently
        // For now, show a message that URL processing is coming soon
        setError("URL processing is coming soon. Please upload a file directly.");
        setStage('error');
        return;
      } else {
        setError("Invalid audio data format.");
        setStage('error');
        return;
      }

      setStage('transcribing');

      // Call the API
      const result = await generateComicFromAudio(
        file,
        {
          style: 'storybook',
          aspectRatio: '16:9'
        },
        (progressUpdate) => {
          setProgress(progressUpdate);
          if (progressUpdate.stage === 'transcribing') {
            setStage('transcribing');
          } else if (progressUpdate.stage === 'generating_images' || progressUpdate.stage === 'generating_prompts') {
            setStage('generating');
          } else if (progressUpdate.stage === 'complete') {
            setStage('complete');
          } else if (progressUpdate.stage === 'error') {
            setError(progressUpdate.message);
            setStage('error');
          }
        }
      );

      if (result.success) {
        setPanels(result.panels.filter(p => p.status === 'success'));
        
        // Extract metadata from transcript
        const metadataEntry = result.transcript.find(t => t._type === 'metadata');
        if (metadataEntry) {
          setMetadata({
            title: (metadataEntry as { title?: string }).title,
            chapter: (metadataEntry as { chapter?: string }).chapter
          });
        }
        
        setStage('complete');
      } else {
        setError(result.error_message || 'Comic generation failed');
        setStage('error');
      }

      // Clear session storage
      sessionStorage.removeItem('audioData');

    } catch (err) {
      console.error('Generation error:', err);
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      setStage('error');
    }
  }, []);

  useEffect(() => {
    processAudio();
  }, [processAudio]);

  const handleDownloadAll = () => {
    panels.forEach((panel, index) => {
      setTimeout(() => {
        downloadPanel(panel, `comic_panel_${index + 1}.png`);
      }, index * 500); // Stagger downloads
    });
  };

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
          {metadata?.title && (
            <p className="font-comic text-lg text-gray-600 mt-1">{metadata.title}</p>
          )}
        </div>
        <div className="w-24 h-4 bg-comic-red comic-border rotate-3 hidden md:block" />
      </header>

      <div className="w-full max-w-6xl">
        {stage === 'loading' || stage === 'transcribing' || stage === 'generating' ? (
          <div className="py-20">
            <ComicLoader />
            <div className="text-center mt-8">
              <p className="font-bangers text-2xl text-black mb-2">
                {stage === 'loading' && "LOADING..."}
                {stage === 'transcribing' && "TRANSCRIBING AUDIO..."}
                {stage === 'generating' && "GENERATING PANELS..."}
              </p>
              {progress && (
                <>
                  <p className="font-comic text-gray-600">{progress.message}</p>
                  <div className="w-64 mx-auto mt-4 h-3 bg-gray-200 rounded-full overflow-hidden comic-border">
                    <div 
                      className="h-full bg-comic-yellow transition-all duration-500"
                      style={{ width: `${progress.progress}%` }}
                    />
                  </div>
                </>
              )}
            </div>
          </div>
        ) : stage === 'error' ? (
          <div className="py-20 text-center">
            <div className="w-24 h-24 mx-auto mb-6 bg-comic-red rounded-full flex items-center justify-center comic-border">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="font-bangers text-3xl text-comic-red mb-4">OOPS! SOMETHING WENT WRONG!</h3>
            <p className="font-comic text-gray-600 mb-8 max-w-md mx-auto">{error}</p>
            <div className="flex justify-center space-x-4">
              <Link 
                href="/"
                className="bg-comic-yellow text-black comic-button px-8 py-3"
              >
                TRY AGAIN
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-12 animate-in fade-in zoom-in duration-500">
            {panels.length === 0 ? (
              <div className="text-center py-20">
                <p className="font-bangers text-2xl text-gray-400">No panels were generated.</p>
                <Link href="/" className="mt-4 inline-block bg-comic-yellow text-black comic-button px-8 py-3">
                  TRY AGAIN
                </Link>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                  {panels.map((panel, index) => (
                    <div 
                      key={panel.panel_id} 
                      className="bg-white p-4 comic-border rounded-lg group cursor-pointer shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transition-all"
                      onClick={() => setSelectedPanel(panel)}
                    >
                      <div className="aspect-[3/4] bg-gray-100 rounded flex items-center justify-center mb-4 overflow-hidden relative">
                        {panel.image_base64 ? (
                          <img 
                            src={base64ToImageUrl(panel.image_base64, panel.mime_type)} 
                            alt={`Panel ${index + 1}`}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <span className="font-bangers text-6xl text-gray-200">{index + 1}</span>
                        )}
                        <div className="absolute inset-0 bg-comic-yellow opacity-0 group-hover:opacity-10 transition-opacity" />
                        <div className="absolute bottom-2 right-2 bg-comic-red text-white font-bangers px-2 py-1 text-sm transform rotate-2">
                          PANEL {index + 1}
                        </div>
                      </div>
                      {panel.prompt && (
                        <p className="font-comic text-sm text-gray-600 line-clamp-2">{panel.prompt}</p>
                      )}
                    </div>
                  ))}
                </div>

                <div className="flex justify-center pt-8 space-x-4">
                  <button 
                    onClick={handleDownloadAll}
                    className="bg-comic-yellow comic-button text-2xl px-12 py-4 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
                  >
                    DOWNLOAD ALL PANELS
                  </button>
                  <Link 
                    href="/"
                    className="bg-comic-blue text-white comic-button text-2xl px-12 py-4 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
                  >
                    CREATE ANOTHER
                  </Link>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Panel Modal */}
      {selectedPanel && (
        <div 
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedPanel(null)}
        >
          <div 
            className="bg-white comic-border rounded-lg max-w-4xl w-full max-h-[90vh] overflow-auto p-6"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-4">
              <h3 className="font-bangers text-2xl">PANEL {selectedPanel.panel_id}</h3>
              <button 
                onClick={() => setSelectedPanel(null)}
                className="w-10 h-10 bg-comic-red text-white comic-border rounded-full flex items-center justify-center hover:brightness-110"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            {selectedPanel.image_base64 && (
              <img 
                src={base64ToImageUrl(selectedPanel.image_base64, selectedPanel.mime_type)}
                alt={`Panel ${selectedPanel.panel_id}`}
                className="w-full rounded-lg mb-4"
              />
            )}
            {selectedPanel.prompt && (
              <div className="bg-gray-100 p-4 rounded-lg comic-border">
                <p className="font-comic text-sm text-gray-600">{selectedPanel.prompt}</p>
              </div>
            )}
            <div className="mt-4 flex justify-end">
              <button 
                onClick={() => downloadPanel(selectedPanel)}
                className="bg-comic-yellow comic-button px-6 py-2"
              >
                DOWNLOAD PANEL
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Decorative floating elements */}
      <div className="fixed top-20 right-[-30px] w-24 h-24 bg-comic-red rounded-full opacity-5 blur-2xl -z-10" />
      <div className="fixed bottom-20 left-[-30px] w-32 h-32 bg-comic-yellow rounded-full opacity-5 blur-2xl -z-10" />
    </main>
  );
}
