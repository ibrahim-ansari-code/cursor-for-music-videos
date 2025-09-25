import React, { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Receipt, Upload, Check, AlertCircle, Brain } from 'lucide-react';
import { ReceiptPreview as SharedReceiptPreview } from '../../ui/SharedModalComponents';
import type { ReceiptUploadState } from '../../ui/SharedModalComponents';

interface SmartReceiptProcessorProps {
  receiptState: ReceiptUploadState;
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  isSubmitting?: boolean;
  className?: string;
}

/**
 * Smart Receipt Processor Component
 */
const SmartReceiptProcessor: React.FC<SmartReceiptProcessorProps> = ({
  receiptState,
  onFileChange,
  isSubmitting = false,
  className = '',
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragActive, setIsDragActive] = useState(false);

  // Handle drag events
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set drag inactive if we're actually leaving the dropzone container
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragActive(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const mockEvent = {
        target: {
          files: e.dataTransfer.files,
        },
      } as React.ChangeEvent<HTMLInputElement>;
      onFileChange(mockEvent);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  };

  const isProcessing = receiptState.isParsingReceipt;
  const hasError = !!receiptState.receiptParseError;
  const isSuccess = !!receiptState.currentReceiptUrl && !isProcessing && !hasError;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`bg-gradient-to-br from-white to-emerald-50/30 dark:from-gray-800 dark:to-emerald-900/20 rounded-xl p-4 border border-emerald-100 dark:border-emerald-700 shadow-sm hover:shadow-md transition-shadow duration-200 ${className}`}
    >
      <div className="flex items-start gap-3">
        {/* Left Section - Branding & Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-5">
            {/* Enhanced Icon Container - Centered */}
            <div className="relative flex-shrink-0">
              <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-emerald-600 dark:from-emerald-600 dark:to-emerald-700 rounded-xl flex items-center justify-center shadow-lg">
                <Receipt className="w-6 h-6 text-white" />
              </div>
              {/* AI Badge*/}
              <div className="absolute -top-1.5 -right-1.5 w-6 h-6 bg-gradient-to-br from-purple-500 to-purple-600 dark:from-purple-600 dark:to-purple-700 rounded-full flex items-center justify-center border-2 border-white dark:border-gray-800 shadow-sm">
                <Brain className="w-3 h-3 text-white" />
              </div>
            </div>

            {/* Text Content */}
            <div className="flex-1 py-1.5">
              <div className="flex items-center gap-2.5 mb-1">
                <h3 className="text-md font-semibold text-gray-900 dark:text-gray-100">
                  Smart Receipt Processing
                </h3>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300 border border-purple-200 dark:border-purple-700">
                  AI-Powered
                </span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                Auto-extract amount, tax details, date & description from receipt
              </p>
            </div>
          </div>
        </div>

        {/* Right Section - Compact Dropzone */}
        <div className="w-64">
          {/* Compact Dropzone - Same Height as Left Section */}
          <div
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onKeyDown={handleKeyPress}
            tabIndex={0}
            role="button"
            aria-label="Click or drag to upload receipt"
            className={`
              relative border-2 border-dashed rounded-lg p-3 h-16 flex items-center justify-center text-center transition-all duration-200 cursor-pointer
              ${isDragActive 
                ? 'border-emerald-400 dark:border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20' 
                : isProcessing 
                  ? 'border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20' 
                  : hasError
                    ? 'border-red-300 dark:border-red-600 bg-red-50 dark:bg-red-900/20'
                    : isSuccess
                      ? 'border-green-300 dark:border-green-600 bg-green-50 dark:bg-green-900/20'
                      : 'border-emerald-200 dark:border-emerald-700 bg-white dark:bg-gray-700 hover:border-emerald-300 dark:hover:border-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20'
              }
              ${isSubmitting || isProcessing ? 'opacity-75 cursor-not-allowed' : ''}
              focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:focus:ring-emerald-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              id="receipt_file"
              name="receipt_file"
              accept=".pdf,.png,.jpg,.jpeg,image/*"
              onChange={onFileChange}
              disabled={isSubmitting || isProcessing}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
              aria-label="Upload receipt file"
            />
            <AnimatePresence mode="wait">
              {/* Default State - Horizontal Layout */}
              {!isProcessing && !hasError && !isSuccess && (
                <motion.div
                  key="default"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center space-x-6"
                >
                  <div className="w-6 h-6 bg-gradient-to-br from-emerald-100 to-emerald-200 dark:from-emerald-800 dark:to-emerald-900 rounded flex items-center justify-center">
                    <Upload className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="text-center">
                    <p className="font-medium text-gray-900 dark:text-gray-100 text-xs">Drop or Click to Browse</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">PDF, PNG, JPG (10MB max)</p>
                  </div>
                </motion.div>
              )}

              {/* Processing State - Compact */}
              {isProcessing && (
                <motion.div
                  key="processing"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center space-x-2"
                >
                  <div className="relative">
                    <div className="w-5 h-5 border-2 border-blue-200 dark:border-blue-600 rounded-full animate-spin border-t-blue-600 dark:border-t-blue-400"></div>
                    <Brain className="w-2 h-2 text-blue-600 dark:text-blue-400 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                  </div>
                  <div className="text-left">
                    <p className="text-xs font-semibold text-blue-800 dark:text-blue-300">Processing...</p>
                  </div>
                </motion.div>
              )}

              {/* Error State - Compact */}
              {hasError && (
                <motion.div
                  key="error"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center space-x-2"
                >
                  <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" />
                  <p className="text-xs font-semibold text-red-800 dark:text-red-300 truncate">Upload failed</p>
                </motion.div>
              )}

              {/* Success State - Compact */}
              {isSuccess && (
                <motion.div
                  key="success"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center space-x-2"
                >
                  <div className="w-5 h-5 bg-green-500 dark:bg-green-600 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" strokeWidth={3} />
                  </div>
                  <div className="text-left flex-1">
                    <p className="text-xs font-semibold text-green-800 dark:text-green-300">Success!</p>
                    <button
                      type="button"
                      onClick={() => receiptState.setShowReceiptPreview(!receiptState.showReceiptPreview)}
                      className="text-xs text-green-700 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300 underline"
                    >
                      {receiptState.showReceiptPreview ? 'Hide' : 'View'}
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Receipt Preview */}
      {receiptState.currentReceiptUrl && receiptState.showReceiptPreview && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-4 pt-4 border-t border-emerald-100 dark:border-emerald-700"
        >
          <SharedReceiptPreview
            show={true}
            receiptUrl={receiptState.currentReceiptUrl}
          />
        </motion.div>
      )}
    </motion.div>
  );
};

export default SmartReceiptProcessor;
