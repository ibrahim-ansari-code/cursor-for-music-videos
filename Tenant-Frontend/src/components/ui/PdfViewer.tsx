import React, { useState, useEffect, useMemo } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

interface PdfViewerProps {
  fileUrl: string;
  onError?: (error: Error) => void;
}

interface DocumentLoadSuccess {
  numPages: number;
}

// Track if worker has been initialized (prevents duplicate setup)
let workerInitialized = false;

/**
 * Lazy initialization of PDF.js worker
 * Runs once on first component mount to avoid SSR/testing issues
 */
const setupPdfWorker = (): void => {
  if (workerInitialized) return;

  // Use unpkg CDN (recommended by PDF.js official docs)
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
  workerInitialized = true;
  console.info('[PDF Viewer] Worker initialized');
};

const PdfViewer: React.FC<PdfViewerProps> = ({ fileUrl, onError }) => {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);

  // Initialize worker on mount (lazy initialization)
  useEffect(() => {
    setupPdfWorker();
  }, []);

  // Reset to first page when file URL changes
  useEffect(() => {
    setPageNumber(1);
  }, [fileUrl]);

  // Memoize PDF.js options to prevent unnecessary Document reloads
  const pdfOptions = useMemo(() => {
    return {
      // Use CDN for cmaps (character maps for international PDFs)
      cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
      cMapPacked: true,
      // IMPORTANT: withCredentials must be false for Azure SAS tokens
      withCredentials: false,
      // Enable standard fonts for better rendering
      standardFontDataUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
      // Disable range requests - fetch entire PDF at once to avoid auth issues
      disableRange: true,
      // Disable streaming to ensure SAS token is used for all requests
      disableStream: true,
    };
  }, []);

  const onDocumentLoadSuccess = ({ numPages }: DocumentLoadSuccess): void => {
    setNumPages(numPages);
  };

  const onDocumentLoadError = (error: Error): void => {
    console.error('[PDF Viewer] Error loading PDF:', error);
    if (onError) {
      onError(error);
    }
  };

  const goToPrevPage = (): void => {
    setPageNumber((prevPageNumber) => Math.max(prevPageNumber - 1, 1));
  };

  const goToNextPage = (): void => {
    setPageNumber((prevPageNumber) => Math.min(prevPageNumber + 1, numPages || 1));
  };

  const zoomIn = (): void => {
    setScale((prevScale) => Math.min(prevScale + 0.2, 2.5));
  };

  const zoomOut = (): void => {
    setScale((prevScale) => Math.max(prevScale - 0.2, 0.5));
  };

  const resetZoom = (): void => {
    setScale(1.0);
  };

  return (
    <div className="pdf-viewer-container flex flex-col h-full">
      {/* PDF Controls */}
      <div className="pdf-controls bg-gray-100 border-b border-gray-300 p-3 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {/* Page Navigation */}
          <button
            onClick={goToPrevPage}
            disabled={pageNumber <= 1}
            className="px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
            aria-label="Previous page"
            type="button"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="text-sm text-gray-700">
            Page {pageNumber} of {numPages || '?'}
          </span>
          <button
            onClick={goToNextPage}
            disabled={!numPages || pageNumber >= numPages}
            className="px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
            aria-label="Next page"
            type="button"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center space-x-2">
          <button
            onClick={zoomOut}
            className="px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors cursor-pointer"
            aria-label="Zoom out"
            type="button"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            </svg>
          </button>
          <button
            onClick={resetZoom}
            className="px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors cursor-pointer"
            type="button"
          >
            {Math.round(scale * 100)}%
          </button>
          <button
            onClick={zoomIn}
            className="px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors cursor-pointer"
            aria-label="Zoom in"
            type="button"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
      </div>

      {/* PDF Document */}
      <div className="pdf-document-container flex-1 overflow-auto bg-gray-50 p-4">
        <div className="flex justify-center">
          <Document
            file={{ url: fileUrl }}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={
              <div className="flex items-center justify-center p-8">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto mb-4"></div>
                  <p className="text-gray-600">Loading PDF...</p>
                </div>
              </div>
            }
            error={
              <div className="flex items-center justify-center p-8">
                <div className="text-center max-w-md">
                  <svg className="w-16 h-16 text-red-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Failed to load PDF</h3>
                  <p className="text-gray-600 mb-4">
                    The PDF could not be loaded. Please try downloading the file instead.
                  </p>
                </div>
              </div>
            }
            noData={
              <div className="flex items-center justify-center p-8">
                <div className="text-center">
                  <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No PDF data</h3>
                  <p className="text-gray-600">No PDF file was provided.</p>
                </div>
              </div>
            }
            options={pdfOptions}
          >
            <Page
              pageNumber={pageNumber}
              scale={scale}
              renderTextLayer={true}
              renderAnnotationLayer={true}
              className="shadow-lg"
              loading={
                <div className="flex items-center justify-center p-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                </div>
              }
            />
          </Document>
        </div>
      </div>
    </div>
  );
};

export default PdfViewer;
