/**
 * Documents Tab Component
 * 
 * Main container for tenant document management.
 * Displays filterable list of documents with upload, preview, and management capabilities.
 */

import React, { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { EnrichedTenant } from '../../../../../types/tenant';
import { DocumentFilters as DocumentFiltersType, TenantDocument } from '../../../../../types/tenantDocument';
import { useTenantDocuments } from '../../../../../hooks/useTenantDocuments';
import DocumentFilters from './DocumentFilters';
import DocumentsTable from './DocumentsTable';

interface OutletContext {
  tenant: EnrichedTenant;
  refetch: () => void;
  openFilePreviewModal: (url: string, name: string) => void;
  openDocumentUploadModal: () => void;
  openDocumentEditModal: (document: TenantDocument) => void;
}

const DocumentsTab: React.FC = () => {
  const context = useOutletContext<OutletContext>();
  
  // Filter state
  const [filters, setFilters] = useState<DocumentFiltersType>({});

  // Guard: Handle undefined context gracefully (occurs during refetch or initial load)
  // Parent TenantProfile handles the loading spinner, so we just return null briefly
  if (!context || !context.tenant) {
    return null;
  }

  const { tenant, openFilePreviewModal, openDocumentUploadModal, openDocumentEditModal } = context;

  // Fetch documents with filters
  const { data: documentsResponse, isLoading, error, refetch } = useTenantDocuments(
    tenant.id?.toString(),
    filters
  );

  const documents = documentsResponse?.documents || [];
  const totalCount = documentsResponse?.total || 0;

  // Error state
  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12">
        <div className="text-center">
          <div className="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {error instanceof Error ? error.message : 'Failed to load documents'}
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Main Documents Card */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Filters Bar */}
        <DocumentFilters
          filters={filters}
          onFiltersChange={setFilters}
          onUploadClick={openDocumentUploadModal}
          documentCount={totalCount}
        />

        {/* Documents Table */}
        <div className="overflow-x-auto">
          <DocumentsTable
            documents={documents}
            tenantId={tenant.id?.toString() || ''}
            onPreview={openFilePreviewModal}
            onEdit={openDocumentEditModal}
            isLoading={isLoading}
          />
        </div>

        {/* Showing X of Y indicator */}
        {!isLoading && documents.length > 0 && (
          <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Showing {documents.length} of {totalCount} document{totalCount !== 1 ? 's' : ''}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentsTab;
