/**
 * Documents Tab Component
 * 
 * Main container for tenant document management.
 * Displays filterable list of documents with upload, preview, and management capabilities.
 */

import React, { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { EnrichedTenant } from '../../../../../types/tenant';
import { DocumentFilters as DocumentFiltersType } from '../../../../../types/tenantDocument';
import { useTenantDocuments } from '../../../../../hooks/useTenantDocuments';
import DocumentFilters from './DocumentFilters';
import DocumentsTable from './DocumentsTable';
import DocumentUploadModal from './DocumentUploadModal';

interface OutletContext {
  tenant: EnrichedTenant;
  refetch: () => void;
  openFilePreviewModal: (url: string, name: string) => void;
}

const DocumentsTab: React.FC = () => {
  const context = useOutletContext<OutletContext>();
  
  // Filter state
  const [filters, setFilters] = useState<DocumentFiltersType>({});
  
  // Modal state
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Guard: Handle undefined context gracefully (occurs during refetch or initial load)
  if (!context || !context.tenant) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading documents...</p>
        </div>
      </div>
    );
  }

  const { tenant, openFilePreviewModal } = context;

  // Fetch documents with filters
  const { data: documentsResponse, isLoading, error, refetch } = useTenantDocuments(
    tenant.id?.toString(),
    filters
  );

  const documents = documentsResponse?.documents || [];
  const totalCount = documentsResponse?.total || 0;

  // Handle upload modal
  const handleOpenUploadModal = () => {
    setShowUploadModal(true);
  };

  const handleCloseUploadModal = () => {
    setShowUploadModal(false);
  };

  // Get tenant display name
  const getTenantDisplayName = (): string => {
    if (tenant.tenant_type === 'Company') {
      return tenant.company_name || tenant.contact_person || 'Company';
    }
    if (tenant.first_name || tenant.last_name) {
      return `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim();
    }
    return 'Tenant';
  };

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
          onUploadClick={handleOpenUploadModal}
          documentCount={totalCount}
        />

        {/* Documents Table */}
        <div className="overflow-x-auto">
          <DocumentsTable
            documents={documents}
            tenantId={tenant.id?.toString() || ''}
            onPreview={openFilePreviewModal}
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

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={showUploadModal}
        onClose={handleCloseUploadModal}
        tenantId={tenant.id?.toString() || ''}
        tenantName={getTenantDisplayName()}
      />
    </div>
  );
};

export default DocumentsTab;
