import React from 'react';
import * as Sentry from '@sentry/react';
import DocumentDropdown from './DocumentDropdown';
import type { LeaseWithDocuments, LeaseDocument } from '../../types/lease';

interface LeaseActionsProps {
  lease: LeaseWithDocuments;
  onEdit: (lease: LeaseWithDocuments) => void;
  onDelete: (leaseId: number) => Promise<void>;
  onStatusChange: (lease: LeaseWithDocuments) => void;
  onDocumentUpload: (lease: LeaseWithDocuments) => void;
  onDocumentPreview: (lease: LeaseWithDocuments, document: LeaseDocument) => Promise<void>;
}

const LeaseActions: React.FC<LeaseActionsProps> = ({
  lease,
  onEdit,
  onDelete,
  onStatusChange,
  onDocumentUpload,
  onDocumentPreview,
}) => {
  const handlePreview = async (document: LeaseDocument) => {
    try {
      await onDocumentPreview(lease, document);
    } catch (error: any) {
      Sentry.logger.error('Document preview failed in actions', {
        error: error.message,
        leaseId: lease.id,
        documentId: document.id,
      });
    }
  };

  const hasDocuments = lease.documents && lease.documents.length > 0;

  return (
    <div className="flex items-center justify-center space-x-2">
      {/* Documents dropdown or upload button */}
      {hasDocuments ? (
        <DocumentDropdown lease={lease} onPreview={handlePreview} />
      ) : (
        <button
          type="button"
          onClick={() => onDocumentUpload(lease)}
          className="text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-1 transition-colors duration-150"
          title="Upload document"
        >
          <i className="fas fa-file-upload"></i>
        </button>
      )}

      {/* Edit button */}
      <button
        type="button"
        onClick={() => onEdit(lease)}
        className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 transition-colors duration-150"
        title="Edit lease"
      >
        <i className="fas fa-edit"></i>
      </button>

      {/* Status update button */}
      <button
        type="button"
        onClick={() => onStatusChange(lease)}
        className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 transition-colors duration-150"
        title="Update status"
      >
        <i className="fas fa-tasks"></i>
      </button>

      {/* Delete button */}
      <button
        type="button"
        onClick={() => onDelete(lease.id)}
        className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1 transition-colors duration-150"
        title="Delete lease"
      >
        <i className="fas fa-trash"></i>
      </button>
    </div>
  );
};

export default LeaseActions;

