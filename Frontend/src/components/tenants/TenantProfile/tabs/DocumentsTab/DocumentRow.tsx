/**
 * Document Row Component
 *
 * Renders a single document in the table with metadata and actions.
 * Includes preview, download, edit, and delete functionality.
 * Uses Radix UI DropdownMenu with Portal for proper overflow handling.
 */

import React, { useState } from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { toast } from 'react-toastify';
import { TenantDocument, formatFileSize, getCategoryLabel, getDocumentDisplayName } from '../../../../../types/tenantDocument';
import StatusBadge from './StatusBadge';
import ExpiryBadge from './ExpiryBadge';
import { getSecureTenantDocumentUrl } from '../../../../../utils/api/tenantDocuments';
import { useDeleteTenantDocument } from '../../../../../hooks/useTenantDocuments';

interface DocumentRowProps {
  document: TenantDocument;
  tenantId: string;
  onPreview: (url: string, name: string) => void;
  onEdit?: (document: TenantDocument) => void;
}

const DocumentRow: React.FC<DocumentRowProps> = ({ document, tenantId, onPreview, onEdit }) => {
  const [isLoadingUrl, setIsLoadingUrl] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);

  const deleteMutation = useDeleteTenantDocument();

  // Get file type icon
  const getFileIcon = () => {
    const fileType = document.file_type.toLowerCase();

    if (fileType.includes('pdf')) {
      return (
        <svg className="w-5 h-5 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      );
    }

    if (fileType.includes('word') || fileType.includes('document')) {
      return (
        <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      );
    }

    if (fileType.includes('image')) {
      return (
        <svg className="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      );
    }

    // Default document icon
    return (
      <svg className="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    );
  };

  // Handle preview action
  const handlePreview = async () => {
    setIsLoadingUrl(true);
    try {
      const { secure_url } = await getSecureTenantDocumentUrl(tenantId, document.id);
      onPreview(secure_url, getDocumentDisplayName(document));
    } catch (error: any) {
      console.error('Failed to get secure URL:', error);
      toast.error(error?.message || 'Failed to preview document');
    } finally {
      setIsLoadingUrl(false);
    }
  };

  // Handle download action
  const handleDownload = async () => {
    setIsLoadingUrl(true);
    try {
      const { secure_url } = await getSecureTenantDocumentUrl(tenantId, document.id);
      // Use noopener,noreferrer to prevent reverse tabnabbing attacks
      window.open(secure_url, '_blank', 'noopener,noreferrer');
      toast.success('Download started');
    } catch (error: any) {
      console.error('Failed to get secure URL:', error);
      toast.error(error?.message || 'Failed to download document');
    } finally {
      setIsLoadingUrl(false);
    }
  };

  // Handle edit action
  const handleEdit = () => {
    if (onEdit) {
      onEdit(document);
    }
  };

  // Handle delete action
  const handleDelete = async () => {
    if (!isConfirmingDelete) {
      setIsConfirmingDelete(true);
      // Set a timer to reset the confirmation state after 3 seconds
      setTimeout(() => setIsConfirmingDelete(false), 3000);
      return;
    }

    try {
      await deleteMutation.mutateAsync({
        tenantId,
        documentId: document.id,
      });
      toast.success('Document deleted successfully');
    } catch (error: any) {
      console.error('Failed to delete document:', error);
      toast.error(error?.message || 'Failed to delete document');
    } finally {
      setIsConfirmingDelete(false);
    }
  };

  // Format upload date
  const formatUploadDate = (): string => {
    const date = new Date(document.uploaded_at);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <tr className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
      {/* File Type Icon + Name */}
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0">
            {getFileIcon()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
              {getDocumentDisplayName(document)}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {document.document_name ? document.file_name + ' · ' : ''}{formatFileSize(document.file_size)}
            </p>
          </div>
        </div>
      </td>

      {/* Category */}
      <td className="px-6 py-4">
        <span className="text-sm text-gray-900 dark:text-gray-100">
          {getCategoryLabel(document.document_category)}
        </span>
      </td>

      {/* Type */}
      <td className="px-6 py-4">
        <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
          {document.document_type.replace(/_/g, ' ')}
        </span>
      </td>

      {/* Upload Date */}
      <td className="px-6 py-4">
        <span className="text-sm text-gray-700 dark:text-gray-300" title={new Date(document.uploaded_at).toLocaleString()}>
          {formatUploadDate()}
        </span>
      </td>

      {/* Expiry */}
      <td className="px-6 py-4">
        <ExpiryBadge document={document} />
      </td>

      {/* Status */}
      <td className="px-6 py-4">
        <StatusBadge status={document.status} />
      </td>

      {/* Actions */}
      <td className="px-6 py-4">
        <div className="flex items-center justify-end gap-2">
          {/* Quick Preview Button */}
          <button
            onClick={handlePreview}
            disabled={isLoadingUrl}
            className="p-2 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors disabled:opacity-50"
            title="Preview document"
          >
            {isLoadingUrl ? (
              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            )}
          </button>

          {/* More Actions Dropdown - Using Radix UI Portal to escape overflow containers */}
          <DropdownMenu.Root onOpenChange={(open) => !open && setIsConfirmingDelete(false)}>
            <DropdownMenu.Trigger asChild>
              <button
                className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title="More actions"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                </svg>
              </button>
            </DropdownMenu.Trigger>

            <DropdownMenu.Portal>
              <DropdownMenu.Content
                className="min-w-[12rem] bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-[9999]"
                sideOffset={5}
                align="end"
                collisionPadding={10}
              >
                <DropdownMenu.Item
                  onSelect={handleDownload}
                  disabled={isLoadingUrl}
                  className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer outline-none disabled:opacity-50"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download
                </DropdownMenu.Item>

                {onEdit && (
                  <DropdownMenu.Item
                    onSelect={handleEdit}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer outline-none"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    Edit Details
                  </DropdownMenu.Item>
                )}

                <DropdownMenu.Separator className="h-px bg-gray-200 dark:bg-gray-700 my-1" />

                <DropdownMenu.Item
                  onSelect={(e) => {
                    e.preventDefault();
                    handleDelete();
                  }}
                  disabled={deleteMutation.isPending}
                  className={`flex items-center gap-2 px-4 py-2 text-sm cursor-pointer outline-none disabled:opacity-50 ${
                    isConfirmingDelete
                      ? 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/30 font-semibold'
                      : 'text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30'
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  {deleteMutation.isPending ? 'Deleting...' : isConfirmingDelete ? 'Confirm Delete?' : 'Delete'}
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
      </td>
    </tr>
  );
};

export default DocumentRow;
