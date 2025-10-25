import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download, ExternalLink, AlertCircle, FileText, Image as ImageIcon, Loader2 } from 'lucide-react';
import PdfViewer from './PdfViewer';

interface FilePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  fileUrl: string | null;
  fileName?: string;
}

interface SecureUrlResponse {
  secure_url: string;
  expires_at: string;
  expires_in_seconds: number;
}

/**
 * File Preview Modal with Secure Azure SAS Support
 * 
 * Automatically fetches SAS tokens for private Azure blob URLs
 * Supports images, PDFs, and other document types
 */
const FilePreviewModal: React.FC<FilePreviewModalProps> = ({
  isOpen,
  onClose,
  fileUrl,
  fileName = 'File Preview',
}) => {
  const [previewError, setPreviewError] = useState<boolean>(false);
  const [iframeLoaded, setIframeLoaded] = useState<boolean>(false);
  const [secureUrl, setSecureUrl] = useState<string | null>(null);
  const [isLoadingSecureUrl, setIsLoadingSecureUrl] = useState<boolean>(false);

  // Fetch secure URL for Azure blob files when modal opens
  useEffect(() => {
    const fetchSecureUrl = async (): Promise<void> => {
      if (!isOpen || !fileUrl) {
        setSecureUrl(null);
        return;
      }

      // Check if it's an Azure blob URL that needs a SAS token
      const isAzureUrl = fileUrl.startsWith('https://') && fileUrl.includes('blob.core.windows.net');
      const alreadyHasSAS = fileUrl.includes('?sv=') || fileUrl.includes('?se=');

      if (!isAzureUrl || alreadyHasSAS) {
        // Not Azure or already has SAS - use as-is
        setSecureUrl(fileUrl);
        return;
      }

      // Azure URL without SAS - fetch secure URL
      setIsLoadingSecureUrl(true);
      try {
        // Import the appropriate API function based on URL pattern
        let secureUrlData: SecureUrlResponse;
        
        if (fileUrl.includes('/expense-receipts/')) {
          const { getSecureExpenseReceiptUrl } = await import('../utils/api/accounting');
          secureUrlData = await getSecureExpenseReceiptUrl(fileUrl);
        } else if (fileUrl.includes('/payment-receipts/')) {
          const { getSecurePaymentReceiptUrl } = await import('../utils/api/accounting');
          secureUrlData = await getSecurePaymentReceiptUrl(fileUrl);
        } else if (fileUrl.includes('/property-images/')) {
          const { propertyImagesApi } = await import('../utils/api/propertyImages');
          secureUrlData = await propertyImagesApi.getSecureImageUrl(fileUrl);
        } else if (fileUrl.includes('/maintenance-photos/')) {
          const { getSecurePhotoUrl } = await import('../utils/api/maintenance');
          secureUrlData = await getSecurePhotoUrl(fileUrl);
        } else {
          // Unknown container or tenant/lease documents (already handled elsewhere) - use original URL
          setSecureUrl(fileUrl);
          return;
        }
        
        setSecureUrl(secureUrlData.secure_url);
        console.log('[FilePreviewModal] Generated secure URL, expires:', secureUrlData.expires_at);
      } catch (error) {
        console.error('Failed to fetch secure URL:', error);
        // Fallback to original URL (will likely fail but shows error state)
        setSecureUrl(fileUrl);
      } finally {
        setIsLoadingSecureUrl(false);
      }
    };

    fetchSecureUrl();
  }, [isOpen, fileUrl]);

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
    // Check if iframe actually loaded content
    try {
      const iframe = document.getElementById('file-preview-iframe') as HTMLIFrameElement | null;
      if (iframe?.contentWindow) {
        // If we can't access the content, it might be blocked
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        if (!iframeDoc || iframeDoc.body.innerHTML === '') {
          setPreviewError(true);
        }
      }
    } catch {
      // Cross-origin error - likely blocked
      setPreviewError(true);
    }
  };

  const handlePdfError = (): void => {
    setPreviewError(true);
  };

  const renderContent = (): JSX.Element => {
    // Show loading state while fetching secure URL
    if (isLoadingSecureUrl || !secureUrl) {
      return (
        <div className="w-full h-full flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center gap-4"
          >
            <div className="relative">
              <div className="w-16 h-16 border-4 border-blue-100 dark:border-blue-900 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center">
                <Loader2 className="h-6 w-6 text-blue-600 dark:text-blue-400 animate-pulse" />
              </div>
            </div>
            <div className="text-center">
              <p className="text-base font-medium text-gray-900 dark:text-gray-100 mb-1">Loading preview...</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Fetching secure access token</p>
            </div>
          </motion.div>
        </div>
      );
    }

    if (isImage(secureUrl)) {
      return (
        <div className="w-full h-full flex justify-center items-center overflow-hidden p-1 md:p-2">
          <img
            src={secureUrl}
            alt={fileName}
            className="max-w-full max-h-full object-contain"
            onError={() => setPreviewError(true)}
          />
        </div>
      );
    }
    
    if (isPdf(secureUrl)) {
      // Use PdfViewer for PDF files
      return previewError ? (
        <div className="w-full h-full flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center p-8 max-w-lg"
          >
            <div className="mb-6 flex justify-center">
              <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-2xl">
                <FileText className="w-16 h-16 text-red-400 dark:text-red-500" />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
              Unable to Load PDF
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-8 leading-relaxed">
              The PDF could not be loaded. This might be due to file corruption or network issues.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <a
                href={secureUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center px-6 py-3 text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
              >
                <ExternalLink className="h-5 w-5 mr-2" />
                Open in New Tab
              </a>
              <a
                href={secureUrl}
                download
                className="inline-flex items-center justify-center px-6 py-3 text-base font-semibold text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 rounded-xl transition-all duration-200"
              >
                <Download className="h-5 w-5 mr-2" />
                Download PDF
              </a>
            </div>
          </motion.div>
        </div>
      ) : (
        <PdfViewer fileUrl={secureUrl} onError={handlePdfError} />
      );
    }
    
    // For other documents, keep the iframe approach with fallback UI
    return (
      <div className="w-full h-full relative">
        {!iframeLoaded && !previewError && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
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
                <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-2xl">
                  <AlertCircle className="w-16 h-16 text-yellow-500 dark:text-yellow-400" />
                </div>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
                Preview Blocked by Browser
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6 leading-relaxed">
                Chrome and other browsers may block document previews for security reasons
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <a
                  href={secureUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center px-6 py-3 text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
                >
                  <ExternalLink className="h-5 w-5 mr-2" />
                  Open in New Tab
                </a>
                <a
                  href={secureUrl}
                  download
                  className="inline-flex items-center justify-center px-6 py-3 text-base font-semibold text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 rounded-xl transition-all duration-200"
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
            src={secureUrl}
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

  const getFileIcon = (): JSX.Element => {
    if (!secureUrl) return <FileText className="h-5 w-5" />;
    
    if (isImage(secureUrl)) {
      return <ImageIcon className="h-5 w-5" />;
    }
    if (isPdf(secureUrl)) {
      return <FileText className="h-5 w-5" />;
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
            className="relative w-full max-w-6xl h-full max-h-[92vh] flex flex-col bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modern Header with Icon */}
            <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-800 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center space-x-3 min-w-0 flex-1">
                <div className="flex-shrink-0 p-2 bg-white dark:bg-gray-700 rounded-xl shadow-sm">
                  {getFileIcon()}
                </div>
                <div className="min-w-0 flex-1">
                  <h2
                    className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate"
                    title={fileName}
                  >
                    {fileName}
                  </h2>
                  {secureUrl && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                      {isPdf(secureUrl) ? 'PDF Document' : isImage(secureUrl) ? 'Image File' : 'Document'}
                    </p>
                  )}
                </div>
              </div>
              
              {/* Action Buttons in Header */}
              <div className="flex items-center space-x-2 flex-shrink-0 ml-4">
                {secureUrl && !isLoadingSecureUrl && (
                  <>
                    <a
                      href={secureUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                      title="Open in new tab"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                    <a
                      href={secureUrl}
                      download
                      className="inline-flex items-center px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all shadow-sm"
                      title="Download file"
                    >
                      <Download className="h-4 w-4" />
                    </a>
                  </>
                )}
                <button
                  type="button"
                  onClick={onClose}
                  className="inline-flex items-center p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-400 transition-all"
                  aria-label="Close preview"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Modal Body - Content Area */}
            <div className="flex-grow bg-gray-50 dark:bg-gray-900 overflow-hidden relative">
              {renderContent()}
            </div>

            {/* Status Footer (only show if there's a warning) */}
            {previewError && secureUrl && !isPdf(secureUrl) && (
              <div className="flex items-center justify-center px-6 py-3 bg-yellow-50 dark:bg-yellow-900/20 border-t border-yellow-100 dark:border-yellow-900/30">
                <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mr-2" />
                <span className="text-sm text-yellow-700 dark:text-yellow-300 font-medium">
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

