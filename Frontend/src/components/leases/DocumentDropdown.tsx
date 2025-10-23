import React from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as Sentry from '@sentry/react';
import { Eye, ExternalLink } from 'lucide-react';
import type { LeaseWithDocuments, LeaseDocument } from '../../types/lease';

interface DocumentDropdownProps {
  lease: LeaseWithDocuments;
  onPreview: (document: LeaseDocument) => Promise<void>;
}

const DocumentDropdown: React.FC<DocumentDropdownProps> = ({ lease, onPreview }) => {
  const documents = lease.documents || [];

  if (!documents.length) {
    return null;
  }

  const handlePreview = async (doc: LeaseDocument) => {
    Sentry.logger.debug('Document selected for preview', {
      leaseId: lease.id,
      documentId: doc.id,
      documentType: doc.document_type,
    });
    
    try {
      await onPreview(doc);
    } catch (error: any) {
      Sentry.logger.error('Document preview failed', {
        error: error.message,
        leaseId: lease.id,
        documentId: doc.id,
      });
    }
  };

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          onClick={() => {
            Sentry.logger.trace('Document dropdown opened', {
              leaseId: lease.id,
              documentCount: documents.length,
            });
          }}
          className="text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-1 transition-colors duration-150 inline-flex items-center"
          title={`View ${documents.length} document${documents.length > 1 ? 's' : ''}`}
        >
          <Eye className="w-4 h-4" />
          {documents.length > 1 && (
            <span className="ml-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-200 px-1.5 py-0.5 rounded-full font-medium">
              {documents.length}
            </span>
          )}
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="min-w-[14rem] bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50"
          sideOffset={5}
          align="end"
          collisionPadding={10}
        >
          {documents.map((doc, index) => (
            <DropdownMenu.Item
              key={doc.id || index}
              onSelect={() => handlePreview(doc)}
              className="flex items-center justify-between px-4 py-2.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-purple-50 dark:hover:bg-purple-900/20 hover:text-purple-900 dark:hover:text-purple-100 cursor-pointer outline-none transition-colors group"
            >
              <span className="truncate font-medium">
                {doc.document_type.charAt(0).toUpperCase() + doc.document_type.slice(1)}
              </span>
              <ExternalLink className="w-3.5 h-3.5 text-gray-400 dark:text-gray-500 group-hover:text-purple-600 dark:group-hover:text-purple-400 ml-2 flex-shrink-0" />
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
};

export default DocumentDropdown;

