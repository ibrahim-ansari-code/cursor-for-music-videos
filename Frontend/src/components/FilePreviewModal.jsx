import React, { useState, useEffect } from "react";
import PdfViewer from "./PdfViewer";

const FilePreviewModal = ({
  isOpen,
  onClose,
  fileUrl,
  fileName = "File Preview",
}) => {
  const [previewError, setPreviewError] = useState(false);
  const [iframeLoaded, setIframeLoaded] = useState(false);

  useEffect(() => {
    // Reset states when modal opens/closes or URL changes
    if (isOpen) {
      setPreviewError(false);
      setIframeLoaded(false);
    }
  }, [isOpen, fileUrl]);

  if (!isOpen || !fileUrl) {
    return null;
  }

  const isImage = (url) => {
    const cleanUrl = url.split(/[?#]/)[0];
    const extension = cleanUrl.split(".").pop()?.toLowerCase();
    return ["png", "jpg", "jpeg", "gif", "webp", "bmp", "svg"].includes(
      extension
    );
  };

  const isPdf = (url) => {
    const cleanUrl = url.split(/[?#]/)[0];
    const extension = cleanUrl.split(".").pop()?.toLowerCase();
    return extension === "pdf";
  };

  const handleIframeError = (e) => {
    setPreviewError(true);
    setIframeLoaded(true);
  };

  const handleIframeLoad = () => {
    setIframeLoaded(true);
    // Check if iframe actually loaded content
    try {
      const iframe = document.getElementById('file-preview-iframe');
      if (iframe && iframe.contentWindow) {
        // If we can't access the content, it might be blocked
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        if (!iframeDoc || iframeDoc.body.innerHTML === '') {
          setPreviewError(true);
        }
      }
    } catch (e) {
      // Cross-origin error - likely blocked
      setPreviewError(true);
    }
  };

  const handlePdfError = (error) => {
    setPreviewError(true);
  };

  const renderContent = () => {
    if (isImage(fileUrl)) {
      return (
        <div className="w-full h-full flex justify-center items-center overflow-hidden p-1 md:p-2">
          <img
            src={fileUrl}
            alt={fileName}
            className="max-w-full max-h-full object-contain"
            onError={() => setPreviewError(true)}
          />
        </div>
      );
    } else if (isPdf(fileUrl)) {
      // Use PdfViewer for PDF files
      return previewError ? (
        <div className="w-full h-full flex items-center justify-center bg-gray-50">
          <div className="text-center p-8">
            <div className="mb-4">
              <svg className="w-16 h-16 text-gray-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Unable to Load PDF
            </h3>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              The PDF could not be loaded. This might be due to network issues or file corruption.
            </p>
            <div className="space-y-3">
              <a
                href={fileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-6 py-3 text-base font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                Open PDF in New Tab
              </a>
              <div>
                <a
                  href={fileUrl}
                  download
                  className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download PDF
                </a>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <PdfViewer fileUrl={fileUrl} onError={handlePdfError} />
      );
    } else {
      // For other documents, keep the iframe approach with fallback UI
      return (
        <div className="w-full h-full relative">
          {!iframeLoaded && !previewError && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading preview...</p>
              </div>
            </div>
          )}
          
          {previewError ? (
            <div className="w-full h-full flex items-center justify-center bg-gray-50">
              <div className="text-center p-8">
                <div className="mb-4">
                  <svg className="w-16 h-16 text-gray-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Preview Blocked by Browser
                </h3>
                <p className="text-gray-600 mb-4 max-w-md mx-auto">
                  Chrome and other browsers block document previews for security reasons when:
                </p>
                <ul className="text-sm text-gray-500 mb-6 max-w-md mx-auto text-left list-disc list-inside">
                  <li>The document is served over HTTP on an HTTPS page</li>
                  <li>Cross-origin restrictions are in place</li>
                  <li>Enhanced security settings are enabled</li>
                  <li>Ad blockers or privacy extensions interfere</li>
                </ul>
                <div className="space-y-3">
                  <a
                    href={fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-6 py-3 text-base font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    Open Document in New Tab
                  </a>
                  <div>
                    <a
                      href={fileUrl}
                      download
                      className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400"
                    >
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Download File Instead
                    </a>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            // Note: This iframe will be blocked by browsers if Azure Blob Storage doesn't have proper CORS configuration
            // The storage account needs to allow the app's origin (localhost:5173, app.brikli.com, etc.) in its CORS settings
            <iframe
              id="file-preview-iframe"
              src={fileUrl}
              title={fileName}
              className="w-full h-full border-0"
              onLoad={handleIframeLoad}
              onError={handleIframeError}
              // Remove sandbox to be less restrictive
              // Allow downloads explicitly
              allow="download"
            />
          )}
        </div>
      );
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm overflow-y-auto h-full w-full z-50 flex justify-center items-center p-4"
      onClick={onClose}
    >
      <div
        className="glassmorphism-strong relative w-full max-w-4xl h-full max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex justify-between items-center p-4 dark-divider border-b">
          <h2
            className="text-xl font-semibold text-gray-800 dark:text-gray-100 truncate pr-2"
            title={fileName}
          >
            {fileName}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 p-1 rounded-full focus:outline-none focus:ring-2 focus:ring-gray-400"
            aria-label="Close file preview"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-grow dark-bg overflow-auto">
          {renderContent()}
        </div>

        {/* Modal Footer */}
        <div className="flex justify-between items-center p-4 dark-divider border-t dark-input">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {previewError && !isPdf(fileUrl) && (
              <span className="flex items-center">
                <svg className="w-4 h-4 mr-1 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Preview blocked by browser
              </span>
            )}
          </div>
          <div className="flex space-x-3">
            <a
              href={fileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 dark-panel dark-divider border rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              Open in New Tab
            </a>
            <a
              href={fileUrl}
              download
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download
            </a>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 dark-panel dark-divider border rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FilePreviewModal;
