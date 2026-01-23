"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import Logo from "@/components/Logo";
import ComicLoader from "@/components/ComicLoader";
import { 
  generateComicFromAudio, 
  base64ToImageUrl, 
  downloadPanel,
  downloadPage,
  type ComicPanel,
  type ComicPage,
  type GenerationProgress,
  type ComicGenerationResponse
} from "@/lib/api";

type GenerationStage = 'loading' | 'transcribing' | 'analyzing' | 'extracting' | 'generating_prompts' | 'organizing' | 'generating' | 'complete' | 'error';

export default function ComicPage() {
  const [stage, setStage] = useState<GenerationStage>('loading');
  const [progress, setProgress] = useState<GenerationProgress | null>(null);
  const [pages, setPages] = useState<ComicPage[]>([]);
  const [panels, setPanels] = useState<ComicPanel[]>([]);  // Keep for backward compatibility
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [error, setError] = useState<string>("");
  const [metadata, setMetadata] = useState<{ title?: string; chapter?: string } | null>(null);
  const [selectedPage, setSelectedPage] = useState<ComicPage | null>(null);

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
          aspectRatio: '16:9',
          panelsPerPage: 5
        },
        (progressUpdate) => {
          setProgress(progressUpdate);
          
          // Map backend stages to frontend stages
          if (progressUpdate.stage === 'transcribing') {
            setStage('transcribing');
          } else if (progressUpdate.stage === 'analyzing_story') {
            setStage('analyzing');
          } else if (progressUpdate.stage === 'extracting_characters') {
            setStage('extracting');
          } else if (progressUpdate.stage === 'generating_panel_prompts') {
            setStage('generating_prompts');
          } else if (progressUpdate.stage === 'grouping_pages') {
            setStage('organizing');
          } else if (progressUpdate.stage === 'generating_pages') {
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
        // Use pages if available, otherwise fall back to panels
        if (result.pages && result.pages.length > 0) {
          setPages(result.pages.filter(p => p.success === true));
          setCurrentPageIndex(0);
        } else {
          // Backward compatibility: convert panels to pages
          const panelsList = result.panels.filter(p => p.success === true);
          setPanels(panelsList);
        }
        
        // Extract metadata from transcript
        const metadataEntry = result.transcript.find((t: any) => t._type === 'metadata');
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

  const handleDownloadAll = async () => {
    // Helper function to create a delay
    const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

    if (pages.length > 0) {
      // Download pages sequentially with proper delays
      for (let i = 0; i < pages.length; i++) {
        const page = pages[i];
        try {
          downloadPage(page, `comic_page_${page.page_number}.png`);
          // Wait 1000ms between downloads to avoid browser blocking
          if (i < pages.length - 1) {
            await delay(1000);
          }
        } catch (error) {
          console.error(`Failed to download page ${page.page_number}:`, error);
        }
      }
    } else {
      // Backward compatibility: download panels sequentially
      for (let i = 0; i < panels.length; i++) {
        const panel = panels[i];
        try {
          downloadPanel(panel, `comic_panel_${i + 1}.png`);
          // Wait 1000ms between downloads to avoid browser blocking
          if (i < panels.length - 1) {
            await delay(1000);
          }
        } catch (error) {
          console.error(`Failed to download panel ${i + 1}:`, error);
        }
      }
    }
  };

  const getStageTitle = (stage: GenerationStage): string => {
    switch (stage) {
      case 'transcribing': return 'TRANSCRIBING AUDIO...';
      case 'analyzing': return 'ANALYZING STORY...';
      case 'extracting': return 'EXTRACTING CHARACTERS...';
      case 'generating_prompts': return 'GENERATING PROMPTS...';
      case 'organizing': return 'ORGANIZING PAGES...';
      case 'generating': return 'GENERATING COMIC PAGES...';
      case 'complete': return 'COMPLETE!';
      case 'error': return 'ERROR';
      default: return 'LOADING...';
    }
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
        {stage !== 'complete' && stage !== 'error' ? (
          <div className="py-20">
            <ComicLoader />
            <div className="text-center mt-8">
              <p className="font-bangers text-2xl text-black mb-2">
                {getStageTitle(stage)}
              </p>
              {progress && (
                <>
                  <p className="font-comic text-gray-600 mb-1">{progress.message}</p>
                  {progress.current !== undefined && progress.total !== undefined && (
                    <p className="font-comic text-sm text-gray-500 mb-2">
                      {progress.current} of {progress.total}
                    </p>
                  )}
                  <div className="w-64 mx-auto mt-4 h-3 bg-gray-200 rounded-full overflow-hidden comic-border">
                    <div 
                      className="h-full bg-comic-yellow transition-all duration-500"
                      style={{ width: `${progress.progress}%` }}
                    />
                  </div>
                  <p className="font-comic text-xs text-gray-400 mt-2">
                    {Math.round(progress.progress)}%
                  </p>
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
            {pages.length === 0 && panels.length === 0 ? (
              <div className="text-center py-20">
                <p className="font-bangers text-2xl text-gray-400">No pages were generated.</p>
                <Link href="/" className="mt-4 inline-block bg-comic-yellow text-black comic-button px-8 py-3">
                  TRY AGAIN
                </Link>
              </div>
            ) : pages.length > 0 ? (
              <>
                {/* Page Viewer with Navigation */}
                <div className="bg-white p-6 comic-border rounded-lg shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
                  <div className="flex items-center justify-between mb-4">
                    <button
                      onClick={() => setCurrentPageIndex(Math.max(0, currentPageIndex - 1))}
                      disabled={currentPageIndex === 0}
                      className="bg-comic-yellow text-black comic-button px-6 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      ← PREVIOUS
                    </button>
                    <div className="text-center">
                      <p className="font-bangers text-xl text-black">
                        PAGE {currentPageIndex + 1} OF {pages.length}
                      </p>
                      <p className="font-comic text-sm text-gray-600">
                        {pages[currentPageIndex]?.panels?.length || 0} panels on this page
                      </p>
                    </div>
                    <button
                      onClick={() => setCurrentPageIndex(Math.min(pages.length - 1, currentPageIndex + 1))}
                      disabled={currentPageIndex === pages.length - 1}
                      className="bg-comic-yellow text-black comic-button px-6 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      NEXT →
                    </button>
                  </div>
                  
                  {pages[currentPageIndex] && (
                    <div 
                      className="cursor-pointer"
                      onClick={() => setSelectedPage(pages[currentPageIndex])}
                    >
                      <img 
                        src={base64ToImageUrl(pages[currentPageIndex].image_base64, pages[currentPageIndex].mime_type)}
                        alt={`Page ${pages[currentPageIndex].page_number}`}
                        className="w-full rounded-lg border-4 border-black"
                      />
                    </div>
                  )}
                </div>

                {/* Page Navigation Dots */}
                {pages.length > 1 && (
                  <div className="flex justify-center gap-2">
                    {pages.map((_, index) => (
                      <button
                        key={index}
                        onClick={() => setCurrentPageIndex(index)}
                        className={`w-3 h-3 rounded-full comic-border transition-all ${
                          index === currentPageIndex 
                            ? 'bg-comic-red scale-125' 
                            : 'bg-gray-300 hover:bg-gray-400'
                        }`}
                        aria-label={`Go to page ${index + 1}`}
                      />
                    ))}
                  </div>
                )}

                <div className="flex justify-center pt-8 space-x-4">
                  <button 
                    onClick={handleDownloadAll}
                    className="bg-comic-yellow comic-button text-2xl px-12 py-4 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
                  >
                    DOWNLOAD ALL PAGES
                  </button>
                  <Link 
                    href="/"
                    className="bg-comic-blue text-white comic-button text-2xl px-12 py-4 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
                  >
                    CREATE ANOTHER
                  </Link>
                </div>
              </>
            ) : (
              // Backward compatibility: show panels in grid
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                  {panels.map((panel, index) => (
                    <div 
                      key={panel.panel_id} 
                      className="bg-white p-4 comic-border rounded-lg group cursor-pointer shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transition-all"
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

      {/* Page Modal */}
      {selectedPage && (
        <div 
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedPage(null)}
        >
          <div 
            className="bg-white comic-border rounded-lg max-w-6xl w-full max-h-[90vh] overflow-auto p-6"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-4">
              <h3 className="font-bangers text-2xl">PAGE {selectedPage.page_number}</h3>
              <button 
                onClick={() => setSelectedPage(null)}
                className="w-10 h-10 bg-comic-red text-white comic-border rounded-full flex items-center justify-center hover:brightness-110"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            {selectedPage.image_base64 && (
              <img 
                src={base64ToImageUrl(selectedPage.image_base64, selectedPage.mime_type)}
                alt={`Page ${selectedPage.page_number}`}
                className="w-full rounded-lg mb-4"
              />
            )}
            {selectedPage.panels && selectedPage.panels.length > 0 && (
              <div className="bg-gray-100 p-4 rounded-lg comic-border">
                <p className="font-bangers text-lg mb-2">Panels on this page:</p>
                <ul className="list-disc list-inside space-y-1">
                  {selectedPage.panels.map((panel, idx) => (
                    <li key={idx} className="font-comic text-sm text-gray-600">
                      Panel {idx + 1}: {panel.prompt || 'No description'}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="mt-4 flex justify-end">
              <button 
                onClick={() => downloadPage(selectedPage)}
                className="bg-comic-yellow comic-button px-6 py-2"
              >
                DOWNLOAD PAGE
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
