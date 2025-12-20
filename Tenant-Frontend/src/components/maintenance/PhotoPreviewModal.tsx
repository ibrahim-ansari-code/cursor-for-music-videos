import React, { useEffect, useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react';

interface PhotoPreviewModalProps {
  photos: string[];
  initialIndex: number;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Full-screen photo preview modal with navigation
 * - Keyboard navigation (ESC to close, arrows to navigate)
 * - Click outside to close
 * - Open in new tab option
 * - Supports both images and PDFs
 */
const PhotoPreviewModal: React.FC<PhotoPreviewModalProps> = ({
  photos,
  initialIndex,
  isOpen,
  onClose,
}) => {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);

  // Update current index when initialIndex changes
  useEffect(() => {
    setCurrentIndex(initialIndex);
  }, [initialIndex]);

  const handlePrevious = useCallback(() => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : photos.length - 1));
  }, [photos.length]);

  const handleNext = useCallback(() => {
    setCurrentIndex((prev) => (prev < photos.length - 1 ? prev + 1 : 0));
  }, [photos.length]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowLeft') {
        handlePrevious();
      } else if (e.key === 'ArrowRight') {
        handleNext();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handlePrevious, handleNext, onClose]);

  const currentPhoto = photos[currentIndex];
  const isPdf = currentPhoto?.toLowerCase().includes('.pdf');

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-10001"
        onClick={onClose}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 bg-white/90 rounded-full hover:bg-white transition-all shadow-lg z-10"
          aria-label="Close preview"
        >
          <X className="h-6 w-6 text-gray-700" />
        </button>

        {/* Navigation - Previous */}
        {photos.length > 1 && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              handlePrevious();
            }}
            className="absolute left-4 p-3 bg-white/90 rounded-full hover:bg-white transition-all shadow-lg z-10"
            aria-label="Previous photo"
          >
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </button>
        )}

        {/* Navigation - Next */}
        {photos.length > 1 && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleNext();
            }}
            className="absolute right-4 p-3 bg-white/90 rounded-full hover:bg-white transition-all shadow-lg z-10"
            aria-label="Next photo"
          >
            <ChevronRight className="h-6 w-6 text-gray-700" />
          </button>
        )}

        {/* Photo Counter */}
        {photos.length > 1 && (
          <div className="absolute top-4 left-1/2 transform -translate-x-1/2 px-4 py-2 bg-black/70 text-white rounded-full text-sm font-medium">
            {currentIndex + 1} / {photos.length}
          </div>
        )}

        {/* Open in New Tab Button */}
        <a
          href={currentPhoto}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="absolute bottom-4 right-4 p-3 bg-white/90 rounded-full hover:bg-white transition-all shadow-lg flex items-center gap-2 text-sm font-medium text-gray-700"
          aria-label="Open in new tab"
        >
          <ExternalLink className="h-5 w-5" />
          <span className="hidden sm:inline">Open</span>
        </a>

        {/* Image/PDF Display */}
        <motion.div
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
          exit={{ scale: 0.9 }}
          className="relative max-w-[90vw] max-h-[80vh] bg-white rounded-2xl overflow-hidden shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          {isPdf ? (
            <div className="flex flex-col items-center justify-center p-12 min-w-[300px] min-h-[400px]">
              <svg
                className="w-20 h-20 text-gray-400 mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p className="text-gray-600 mb-4 text-center">
                PDF Document
              </p>
              <a
                href={currentPhoto}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2"
              >
                <ExternalLink className="h-4 w-4" />
                Open PDF
              </a>
            </div>
          ) : (
            <img
              src={currentPhoto}
              alt={`Photo ${currentIndex + 1}`}
              className="max-w-full max-h-[80vh] object-contain"
            />
          )}
        </motion.div>

        {/* Thumbnail Strip (if multiple photos) */}
        {photos.length > 1 && (
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2 bg-black/70 p-2 rounded-lg max-w-[90vw] overflow-x-auto">
            {photos.map((photo, index) => {
              const isActive = index === currentIndex;
              const thumbIsPdf = photo.toLowerCase().includes('.pdf');
              
              return (
                <button
                  key={index}
                  onClick={(e) => {
                    e.stopPropagation();
                    setCurrentIndex(index);
                  }}
                  className={`relative shrink-0 w-16 h-16 rounded-lg overflow-hidden border-2 transition-all ${
                    isActive
                      ? 'border-white scale-110'
                      : 'border-transparent opacity-60 hover:opacity-100'
                  }`}
                >
                  {thumbIsPdf ? (
                    <div className="w-full h-full bg-gray-700 flex items-center justify-center">
                      <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                  ) : (
                    <img
                      src={photo}
                      alt={`Thumbnail ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                  )}
                </button>
              );
            })}
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
};

export default PhotoPreviewModal;

