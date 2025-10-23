import React, { useRef, useEffect } from 'react';
import * as Sentry from '@sentry/react';
import type { DocumentDropdownProps } from '../../types/lease';

const DocumentDropdown: React.FC<DocumentDropdownProps> = ({
  lease,
  isOpen,
  onToggle,
  onPreview,
}) => {
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        Sentry.logger.trace('Document dropdown closed by outside click', {
          leaseId: lease.id,
        });
        onToggle();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onToggle, lease.id]);

  const documents = lease.documents || [];

  if (!documents.length) {
    return null;
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => {
          Sentry.logger.trace('Document dropdown toggled', {
            leaseId: lease.id,
            documentCount: documents.length,
            opening: !isOpen,
          });
          onToggle();
        }}
        className="text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-1 transition-colors duration-150"
        title={`View ${documents.length} document${documents.length > 1 ? 's' : ''}`}
      >
        <i className="fas fa-eye"></i>
        {documents.length > 1 && (
          <span className="ml-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-200 px-1.5 py-0.5 rounded-full">
            {documents.length}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-56 rounded-md dark-shadow dark-panel ring-1 ring-black ring-opacity-5 dark:ring-gray-600 z-20">
          <div className="py-1" role="menu">
            {documents.map((doc, index) => (
              <button
                key={doc.id || index}
                type="button"
                onClick={() => {
                  Sentry.logger.debug('Document selected for preview', {
                    leaseId: lease.id,
                    documentId: doc.id,
                    documentType: doc.document_type,
                  });
                  onPreview(doc);
                }}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100 flex items-center justify-between transition-colors duration-150"
                role="menuitem"
              >
                <span className="truncate">
                  {doc.document_type.charAt(0).toUpperCase() + doc.document_type.slice(1)}
                </span>
                <i className="fas fa-external-link-alt text-gray-400 dark:text-gray-500 text-xs"></i>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentDropdown;

