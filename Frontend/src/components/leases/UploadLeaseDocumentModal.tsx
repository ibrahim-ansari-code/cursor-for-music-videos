import React, { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { motion } from 'framer-motion';
import { toast } from 'react-toastify';
import * as Sentry from '@sentry/react';
import { X, Upload, FileText } from 'lucide-react';
import { useUploadLeaseDocument } from '../../hooks/useLeasesQueries';
import type { Lease } from '../../types/lease';
import { getTenantDisplayName } from '../../utils/tenantUtils';

interface UploadLeaseDocumentModalProps {
  isOpen: boolean;
  onClose: () => void;
  lease: Lease;
  onUploadSuccess?: () => void;
}

type DocumentType = 'contract' | 'addendum' | 'notice' | 'inspection' | 'other';

interface ApiError {
  data?: {
    detail?: string;
  };
  message?: string;
}

// File upload constraints
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_MIME_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

// Format file size for display
const formatFileSize = (bytes: number): string => {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }
  return `${(bytes / 1024).toFixed(2)} KB`;
};

const UploadLeaseDocumentModal: React.FC<UploadLeaseDocumentModalProps> = ({
  isOpen,
  onClose,
  lease,
  onUploadSuccess,
}) => {
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDocumentType, setUploadDocumentType] = useState<DocumentType>('contract');

  const uploadDocumentMutation = useUploadLeaseDocument();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target?.files;
    if (!files || files.length === 0) {
      setUploadFile(null);
      return;
    }
    
    const file = files[0];
    
    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      toast.error(`File too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB.`);
      e.target.value = ''; // Reset input
      return;
    }
    
    // Validate MIME type
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      toast.error('Invalid file type. Please upload PDF, DOC, or image files.');
      e.target.value = ''; // Reset input
      return;
    }
    
    setUploadFile(file);
  };

  const handleUploadDocument = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!uploadFile || !lease) {
      toast.error('Please select a file to upload.');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('document_type', uploadDocumentType);

      await uploadDocumentMutation.mutateAsync({
        leaseId: lease.id,
        formData,
      });

      toast.success('Document uploaded successfully.');
      
      // Reset form state
      setUploadFile(null);
      setUploadDocumentType('contract');
      
      // Call success callback if provided
      if (onUploadSuccess) {
        onUploadSuccess();
      }
      
      onClose();
    } catch (err) {
      console.error('Error uploading document:', err);
      const error = err as ApiError;
      const errorMessage =
        error?.data?.detail ||
        error?.message ||
        'Failed to upload document. Please try again.';
      toast.error(errorMessage);
      
      // Report to Sentry with contextual information
      Sentry.captureException(err, {
        tags: {
          component: 'UploadLeaseDocumentModal',
          action: 'upload_lease_document',
          feature: 'leases',
        },
        contexts: {
          lease: {
            id: lease.id,
            property_id: lease.property_id,
            tenant_id: lease.tenant_id,
          },
          upload: {
            document_type: uploadDocumentType,
            file_name: uploadFile?.name,
            file_size: uploadFile?.size,
          },
        },
      });
    }
  };

  const handleClose = () => {
    setUploadFile(null);
    setUploadDocumentType('contract');
    onClose();
  };

  const getDocumentTypeIcon = (type: string) => {
    switch (type) {
      case 'contract':
        return '📄';
      case 'addendum':
        return '✍️';
      case 'notice':
        return '🔔';
      case 'inspection':
        return '📋';
      default:
        return '📎';
    }
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={handleClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-sm z-50">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0"
          />
        </Dialog.Overlay>

        <Dialog.Content className="fixed left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%] z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
            className="w-[90vw] max-w-lg bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Clean Header matching NewExpenseModal */}
            <div className="relative bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <Upload className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      Upload Document
                    </Dialog.Title>
                    <Dialog.Description className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                      Add a document to this lease
                    </Dialog.Description>
                  </div>
                </div>
                <Dialog.Close asChild>
                  <button
                    className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                    disabled={uploadDocumentMutation.isPending}
                    aria-label="Close"
                  >
                    <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                  </button>
                </Dialog.Close>
              </div>
            </div>

            {/* Content area */}
            <motion.div
              className="p-6 bg-gray-50/50 dark:bg-gray-800/50"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
            >
              <form onSubmit={handleUploadDocument} className="space-y-5">
                {/* Lease Info */}
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {getTenantDisplayName(lease.tenant)}
                      </p>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
                        {lease.property?.name || `Property #${lease.property_id}`}
                        {lease.unit?.name && ` - Unit ${lease.unit.name}`}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Document Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Document Type
                  </label>
                  <select
                    className="block w-full px-4 py-2.5 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:focus:ring-blue-400 transition-colors"
                    value={uploadDocumentType}
                    onChange={(e) => setUploadDocumentType(e.target.value as DocumentType)}
                    required
                  >
                    <option value="contract">{getDocumentTypeIcon('contract')} Lease Contract</option>
                    <option value="addendum">{getDocumentTypeIcon('addendum')} Addendum</option>
                    <option value="notice">{getDocumentTypeIcon('notice')} Notice</option>
                    <option value="inspection">{getDocumentTypeIcon('inspection')} Inspection Report</option>
                    <option value="other">{getDocumentTypeIcon('other')} Other</option>
                  </select>
                </div>

                {/* File Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Select File
                  </label>

                  <input
                    id="file-upload"
                    type="file"
                    className="hidden"
                    onChange={handleFileChange}
                    accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                    required
                  />
                  <label
                    htmlFor="file-upload"
                    className={`flex flex-col items-center justify-center w-full px-4 py-8 border-2 border-dashed rounded-lg cursor-pointer transition-all ${
                      uploadFile
                        ? 'border-green-300 bg-green-50 dark:bg-green-900/20 dark:border-green-600'
                        : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700/50 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20'
                    }`}
                  >
                    <div className="text-center">
                      {uploadFile ? (
                        <>
                          <div className="w-12 h-12 mx-auto mb-3 flex items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                            <svg
                              className="w-6 h-6 text-green-600 dark:text-green-400"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M5 13l4 4L19 7"
                              />
                            </svg>
                          </div>
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                            {uploadFile.name}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                            {formatFileSize(uploadFile.size)}
                          </p>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              setUploadFile(null);
                            }}
                            className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
                          >
                            Change file
                          </button>
                        </>
                      ) : (
                        <>
                          <Upload className="w-10 h-10 mx-auto mb-3 text-gray-400 dark:text-gray-500" />
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Click to upload or drag and drop
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            PDF, DOC, DOCX, JPG, PNG (max 10MB)
                          </p>
                        </>
                      )}
                    </div>
                  </label>
                </div>
              </form>
            </motion.div>

            {/* Clean Footer matching NewExpenseModal */}
            <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-3 flex justify-end items-center bg-white dark:bg-gray-800 space-x-3">
              <button
                type="button"
                onClick={handleClose}
                disabled={uploadDocumentMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={() => {
                  const form = document.querySelector('form');
                  if (form) {
                    form.requestSubmit();
                  }
                }}
                disabled={!uploadFile || uploadDocumentMutation.isPending}
                className={`px-5 py-2 text-sm font-medium text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 ${
                  uploadDocumentMutation.isPending || !uploadFile
                    ? 'bg-gray-400 dark:bg-gray-600'
                    : 'bg-blue-600 dark:bg-blue-700 hover:bg-blue-700 dark:hover:bg-blue-600'
                }`}
              >
                {uploadDocumentMutation.isPending ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Uploading...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    <span>Upload Document</span>
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

export default UploadLeaseDocumentModal;

