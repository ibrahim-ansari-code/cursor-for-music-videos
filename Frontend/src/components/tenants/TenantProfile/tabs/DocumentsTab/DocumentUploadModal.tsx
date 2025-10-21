/**
 * Document Upload Modal
 * 
 * Modal for uploading new tenant documents with comprehensive metadata.
 * Supports drag-and-drop file upload, category/type selection, tags, notes, and expiry tracking.
 */

import React, { useState, useRef, useEffect } from 'react';
import { toast } from 'react-toastify';
import * as Sentry from '@sentry/react';
import { DocumentCategory, CATEGORY_LABELS, formatFileSize } from '../../../../../types/tenantDocument';
import { useUploadTenantDocument, useDocumentTaxonomy } from '../../../../../hooks/useTenantDocuments';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  tenantId: string;
  tenantName: string;
}

// File upload constraints
const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25MB
const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/jpg',
  'image/heic',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];

const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  tenantId,
  tenantName,
}) => {
  // Form state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<DocumentCategory | ''>('');
  const [selectedType, setSelectedType] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [notes, setNotes] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMutation = useUploadTenantDocument();
  const { data: taxonomy } = useDocumentTaxonomy();

  // Reset form when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setUploadFile(null);
      setSelectedCategory('');
      setSelectedType('');
      setTags([]);
      setTagInput('');
      setNotes('');
      setExpiryDate('');
      setIsDragging(false);
    }
  }, [isOpen]);

  // Get available types for selected category
  const availableTypes = selectedCategory && taxonomy
    ? taxonomy.categories.find(cat => cat.key === selectedCategory)?.types || []
    : [];

  // Check if selected category requires expiry
  const requiresExpiry = selectedCategory && taxonomy
    ? taxonomy.categories.find(cat => cat.key === selectedCategory)?.requires_expiry || false
    : false;

  // File validation
  const validateFile = (file: File): boolean => {
    if (file.size > MAX_FILE_SIZE) {
      toast.error(`File too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB.`);
      return false;
    }

    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      toast.error('Invalid file type. Please upload PDF, DOCX, PNG, JPG, or HEIC files.');
      return false;
    }

    return true;
  };

  // Handle file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target?.files;
    if (!files || files.length === 0) {
      setUploadFile(null);
      return;
    }

    const file = files[0];
    if (validateFile(file)) {
      setUploadFile(file);
    } else {
      e.target.value = ''; // Reset input
    }
  };

  // Handle drag and drop
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (validateFile(file)) {
        setUploadFile(file);
      }
    }
  };

  // Handle tag addition
  const handleAddTag = () => {
    const newTag = tagInput.trim().toLowerCase();
    if (!newTag) return;

    if (tags.length >= 10) {
      toast.error('Maximum 10 tags allowed');
      return;
    }

    if (tags.map(t => t.toLowerCase()).includes(newTag)) {
      toast.error('Tag already added');
      return;
    }

    setTags([...tags, tagInput.trim()]);
    setTagInput('');
  };

  // Handle tag removal
  const handleRemoveTag = (index: number) => {
    setTags(tags.filter((_, i) => i !== index));
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!uploadFile) {
      toast.error('Please select a file to upload');
      return;
    }

    if (!selectedCategory) {
      toast.error('Please select a document category');
      return;
    }

    if (!selectedType) {
      toast.error('Please select a document type');
      return;
    }

    try {
      await uploadMutation.mutateAsync({
        tenantId,
        file: uploadFile,
        document_category: selectedCategory as DocumentCategory,
        document_type: selectedType,
        tags,
        notes: notes.trim() || undefined,
        expiry_date: expiryDate || null,
      });

      toast.success('Document uploaded successfully');
      onClose();
    } catch (err) {
      console.error('Error uploading document:', err);
      const error = err as any;
      const errorMessage =
        error?.data?.detail ||
        error?.message ||
        'Failed to upload document. Please try again.';
      toast.error(errorMessage);

      // Report to Sentry
      Sentry.captureException(err, {
        tags: {
          component: 'DocumentUploadModal',
          action: 'upload_tenant_document',
          feature: 'tenant_documents',
        },
        contexts: {
          upload: {
            tenant_id: tenantId,
            document_category: selectedCategory,
            document_type: selectedType,
            file_name: uploadFile?.name,
            file_size: uploadFile?.size,
          },
        },
      });
    }
  };

  const handleClose = () => {
    if (uploadMutation.isPending) {
      toast.info('Please wait for upload to complete');
      return;
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm transition-opacity"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-800 rounded-xl max-w-2xl w-full shadow-2xl">
        {/* Header - Compact */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Upload Document
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {tenantName}
                </p>
              </div>
            </div>
            <button
              onClick={handleClose}
              disabled={uploadMutation.isPending}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
              type="button"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Body - Compact Spacing */}
          <form onSubmit={handleSubmit} className="p-5 space-y-3">
          {/* File Upload Area - More Compact */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              File <span className="text-red-500">*</span>
            </label>
            <div
              className={`border-2 border-dashed rounded-lg p-3 text-center transition-colors ${
                isDragging
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
              }`}
              onDragEnter={handleDragEnter}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {uploadFile ? (
                <div className="py-2">
                  <div className="flex items-center justify-center gap-2 mb-1">
                    <svg className="w-5 h-5 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate max-w-md">
                      {uploadFile.name}
                    </p>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                    {formatFileSize(uploadFile.size)}
                  </p>
                  <button
                    type="button"
                    onClick={() => setUploadFile(null)}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                  >
                    Change file
                  </button>
                </div>
              ) : (
                <div className="py-2">
                  <svg className="mx-auto w-8 h-8 text-gray-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <div className="text-sm mb-1">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
                    >
                      Click to browse
                    </button>
                    <span className="text-gray-600 dark:text-gray-400"> or drag and drop</span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    PDF, DOCX, PNG, JPG, HEIC up to 25MB
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileChange}
                    accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.heic"
                    className="hidden"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Document Category */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Document Category <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value as DocumentCategory | '');
                setSelectedType(''); // Reset type when category changes
              }}
              className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            >
              <option value="">Select category...</option>
              {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* Document Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Document Type <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              disabled={!selectedCategory}
              className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              required
            >
              <option value="">Select type...</option>
              {availableTypes.map((type) => (
                <option key={type} value={type}>
                  {type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </option>
              ))}
            </select>
            {!selectedCategory && (
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Select a category first
              </p>
            )}
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tags (optional)
            </label>
            <div className="space-y-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddTag();
                    }
                  }}
                  placeholder="Add a tag..."
                  disabled={tags.length >= 10}
                  className="flex-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={handleAddTag}
                  disabled={!tagInput.trim() || tags.length >= 10}
                  className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add
                </button>
              </div>
              
              {tags.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {tags.map((tag, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400 rounded-full text-xs font-medium"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() => handleRemoveTag(index)}
                        className="hover:text-blue-900 dark:hover:text-blue-300"
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  ))}
                </div>
              )}
              
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {tags.length}/10 tags
              </p>
            </div>
          </div>

          {/* Expiry Date */}
          {requiresExpiry && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Expiry Date <span className="text-xs text-orange-500">(recommended for this category)</span>
              </label>
              <input
                type="date"
                value={expiryDate}
                onChange={(e) => setExpiryDate(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>
          )}

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Notes (optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={280}
              rows={2}
              placeholder="Add any additional notes about this document..."
              className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 text-right">
              {notes.length}/280 characters
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={handleClose}
              disabled={uploadMutation.isPending}
              className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!uploadFile || !selectedCategory || !selectedType || uploadMutation.isPending}
              className="px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {uploadMutation.isPending ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  Upload
                </>
              )}
            </button>
          </div>
          </form>
        </div>
    </div>
  );
};

export default DocumentUploadModal;


