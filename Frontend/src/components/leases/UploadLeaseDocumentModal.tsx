import React, { useState } from 'react';
import { toast } from 'react-toastify';
import * as Sentry from '@sentry/react';
import { useUploadLeaseDocument } from '../../hooks/useLeases';
import type { Lease } from '../../types/lease';

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

  if (!isOpen) return null;

  const getDocumentTypeIcon = (type: string) => {
    switch (type) {
      case 'contract':
        return 'fa-file-contract';
      case 'addendum':
        return 'fa-file-signature';
      case 'notice':
        return 'fa-bell';
      case 'inspection':
        return 'fa-clipboard-check';
      default:
        return 'fa-file-alt';
    }
  };

  return (
    <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center p-4">
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm transition-opacity" 
        onClick={handleClose}
      ></div>
      
      <div className="glassmorphism relative rounded-xl max-w-lg w-full mx-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30">
              <i className="fas fa-cloud-upload-alt text-blue-600 dark:text-blue-400 text-lg"></i>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Upload Document
            </h3>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            type="button"
          >
            <i className="fas fa-times text-xl"></i>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleUploadDocument} className="p-6 space-y-5">
          {/* Lease Info */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <i className="fas fa-info-circle text-blue-600 dark:text-blue-400 mt-0.5"></i>
              <div className="flex-1 text-sm">
                <p className="font-medium text-gray-900 dark:text-gray-100">
                  {lease.tenant?.full_name || 
                   `${lease.tenant?.first_name || ''} ${lease.tenant?.last_name || ''}`.trim() || 
                   'Tenant'}
                </p>
                <p className="text-gray-600 dark:text-gray-400">
                  {lease.property?.name || `Property #${lease.property_id}`}
                  {lease.unit?.name && ` - Unit ${lease.unit.name}`}
                </p>
              </div>
            </div>
          </div>

          {/* Document Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <i className={`fas ${getDocumentTypeIcon(uploadDocumentType)} mr-2`}></i>
              Document Type
            </label>
            <div className="relative">
              <select
                className="dark-input block w-full py-3 pl-4 pr-10 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm transition-all appearance-none cursor-pointer bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-700/50"
                value={uploadDocumentType}
                onChange={(e) => setUploadDocumentType(e.target.value as DocumentType)}
                required
              >
                <option value="contract">📄 Lease Contract</option>
                <option value="addendum">✍️ Addendum</option>
                <option value="notice">🔔 Notice</option>
                <option value="inspection">📋 Inspection Report</option>
                <option value="other">📎 Other</option>
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                <i className="fas fa-chevron-down text-gray-400 text-xs"></i>
              </div>
            </div>
          </div>

          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <i className="fas fa-paperclip mr-2"></i>
              Select File
            </label>
            
            <div className="relative">
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
                className={`flex items-center justify-center w-full px-4 py-8 border-2 border-dashed rounded-lg cursor-pointer transition-all ${
                  uploadFile
                    ? 'border-green-400 bg-green-50 dark:bg-green-900/20 dark:border-green-600'
                    : 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20'
                }`}
              >
                <div className="text-center">
                  {uploadFile ? (
                    <>
                      <i className="fas fa-check-circle text-4xl text-green-500 dark:text-green-400 mb-3"></i>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                        {uploadFile.name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {formatFileSize(uploadFile.size)}
                      </p>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          setUploadFile(null);
                        }}
                        className="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline"
                      >
                        Change file
                      </button>
                    </>
                  ) : (
                    <>
                      <i className="fas fa-cloud-upload-alt text-4xl text-gray-400 dark:text-gray-500 mb-3"></i>
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
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="inline-flex items-center px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              disabled={uploadDocumentMutation.isPending}
            >
              <i className="fas fa-times mr-2"></i>
              Cancel
            </button>
            <button
              type="submit"
              disabled={!uploadFile || uploadDocumentMutation.isPending}
              className="inline-flex items-center px-5 py-2.5 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-lg shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {uploadDocumentMutation.isPending ? (
                <>
                  <svg
                    className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Uploading...
                </>
              ) : (
                <>
                  <i className="fas fa-upload mr-2"></i>
                  Upload Document
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UploadLeaseDocumentModal;

