import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download, ExternalLink, AlertCircle, FileText, Image as ImageIcon } from 'lucide-react';

interface FilePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  fileUrl: string | null;
  fileName?: string;
}

/**
 * File Preview Modal for Tenant Portal
 * Supports images, PDFs, and other document types
 * URL should already have SAS token appended
 */
const FilePreviewModal: React.FC<FilePreviewModalProps> = ({
  isOpen,
  onClose,
  fileUrl,
  fileName = 'File Preview',
}) => {
  const [previewError, setPreviewError] = useState<boolean>(false);
  const [iframeLoaded, setIframeLoaded] = useState<boolean>(false);

  // Reset states when modal opens/closes or URL changes
  useEffect(() => {
    if (isOpen) {
      setPreviewError(false);
      setIframeLoaded(false);
    }
  }, [isOpen, fileUrl]);

  if (!isOpen || !fileUrl) {
    return null;
  }

  const isImage = (url: string): boolean => {
    const cleanUrl = url.split(/[?#]/)[0];
    const extension = cleanUrl.split('.').pop()?.toLowerCase();
    return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'].includes(extension || '');
  };

  const isPdf = (url: string): boolean => {
    const cleanUrl = url.split(/[?#]/)[0];
    const extension = cleanUrl.split('.').pop()?.toLowerCase();
    return extension === 'pdf';
  };

  const handleIframeError = (): void => {
    setPreviewError(true);
    setIframeLoaded(true);
  };

  const handleIframeLoad = (): void => {
    setIframeLoaded(true);
    try {
      const iframe = document.getElementById('file-preview-iframe') as HTMLIFrameElement | null;
      if (iframe?.contentWindow) {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        if (!iframeDoc || iframeDoc.body.innerHTML === '') {
          setPreviewError(true);
        }
      }
    } catch {
      setPreviewError(true);
    }
  };

  const renderContent = (): React.ReactElement => {
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
    }

    if (isPdf(fileUrl)) {
      // Use iframe for PDF viewing - more reliable than react-pdf due to CORS restrictions
      // Browsers natively support PDF rendering in iframes without CORS issues
      return (
        <div className="w-full h-full">
          <iframe
            src={fileUrl}
            title={fileName}
            className="w-full h-full border-0"
            allow="fullscreen"
          />
        </div>
      );
    }

    // For other documents, use iframe with fallback UI
    return (
      <div className="w-full h-full relative">
        {!iframeLoaded && !previewError && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto mb-4" />
              <p className="text-gray-600">Loading preview...</p>
            </div>
          </div>
        )}

        {previewError ? (
          <div className="w-full h-full flex items-center justify-center">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center p-8 max-w-2xl"
            >
              <div className="mb-6 flex justify-center">
                <div className="p-4 bg-yellow-50 rounded-2xl">
                  <AlertCircle className="w-16 h-16 text-yellow-500" />
                </div>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-3">
                Preview Blocked by Browser
              </h3>
              <p className="text-gray-600 mb-6 leading-relaxed">
                Chrome and other browsers may block document previews for security reasons
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <a
                  href={fileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center px-6 py-3 text-base font-semibold text-white bg-gray-900 hover:bg-gray-800 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 cursor-pointer"
                >
                  <ExternalLink className="h-5 w-5 mr-2" />
                  Open in New Tab
                </a>
                <a
                  href={fileUrl}
                  download
                  className="inline-flex items-center justify-center px-6 py-3 text-base font-semibold text-gray-700 bg-white border-2 border-gray-300 hover:border-gray-400 rounded-xl transition-all duration-200 cursor-pointer"
                >
                  <Download className="h-5 w-5 mr-2" />
                  Download File
                </a>
              </div>
            </motion.div>
          </div>
        ) : (
          <iframe
            id="file-preview-iframe"
            src={fileUrl}
            title={fileName}
            className="w-full h-full border-0"
            onLoad={handleIframeLoad}
            onError={handleIframeError}
            allow="download"
          />
        )}
      </div>
    );
  };

  const getFileIcon = (): React.ReactElement => {
    if (isImage(fileUrl)) {
      return <ImageIcon className="h-5 w-5" />;
    }
    return <FileText className="h-5 w-5" />;
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 bg-black/70 backdrop-blur-md overflow-y-auto h-full w-full z-50 flex justify-center items-center p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 20 }}
            transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
            className="relative w-full max-w-6xl h-full max-h-[92vh] flex flex-col bg-white rounded-2xl shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 bg-linear-to-r from-gray-50 to-gray-100 border-b border-gray-200">
              <div className="flex items-center space-x-3 min-w-0 flex-1">
                <div className="shrink-0 p-2 bg-white rounded-xl shadow-sm">
                  {getFileIcon()}
                </div>
                <div className="min-w-0 flex-1">
                  <h2
                    className="text-lg font-semibold text-gray-900 truncate"
                    title={fileName}
                  >
                    {fileName}
                  </h2>
                  <p className="text-xs text-gray-500 truncate mt-0.5">
                    {isPdf(fileUrl) ? 'PDF Document' : isImage(fileUrl) ? 'Image File' : 'Document'}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center space-x-2 shrink-0 ml-4">
                <a
                  href={fileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-all cursor-pointer"
                  title="Open in new tab"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
                <a
                  href={fileUrl}
                  download
                  className="inline-flex items-center px-3 py-2 text-sm font-medium text-white bg-gray-900 hover:bg-gray-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 transition-all shadow-sm cursor-pointer"
                  title="Download file"
                >
                  <Download className="h-4 w-4" />
                </a>
                <button
                  type="button"
                  onClick={onClose}
                  className="inline-flex items-center p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-400 transition-all cursor-pointer"
                  aria-label="Close preview"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Content Area */}
            <div className="grow bg-gray-50 overflow-hidden relative">
              {renderContent()}
            </div>

            {/* Status Footer (only show if there's a warning) */}
            {previewError && !isPdf(fileUrl) && (
              <div className="flex items-center justify-center px-6 py-3 bg-yellow-50 border-t border-yellow-100">
                <AlertCircle className="h-4 w-4 text-yellow-600 mr-2" />
                <span className="text-sm text-yellow-700 font-medium">
                  Preview blocked by browser - use "Open in New Tab" to view
                </span>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default FilePreviewModal;
