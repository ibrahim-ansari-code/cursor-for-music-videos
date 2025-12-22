import React, { useState } from 'react';
import * as Sentry from '@sentry/react';
import { FaFileContract, FaEye, FaDownload, FaFileAlt, FaMapMarkerAlt, FaCalendarAlt, FaDollarSign, FaUser, FaUsers, FaBuilding } from 'react-icons/fa';
import { useLeaseDocuments } from '@/hooks/useLeaseDocuments';
import { getLeaseDocumentSecureUrl, getTenantDocumentSecureUrl } from '@/utils/api/documents';
import type { LeaseDocument, TenantDocument } from '@/utils/api/documents';
import { formatDateForDisplay } from '@/utils/dateHelpers';
import FilePreviewModal from '@/components/ui/FilePreviewModal';

/**
 * LeaseDocumentsContent Component
 * Displays the tenant's lease agreement and additional documents
 */
const LeaseDocumentsContent: React.FC = () => {
  const {
    leaseInfo,
    leaseDocuments,
    additionalDocuments,
    isLoading,
    error,
  } = useLeaseDocuments();

  const [loadingDocId, setLoadingDocId] = useState<string | number | null>(null);

  // File preview modal state
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewFileName, setPreviewFileName] = useState<string>('');

  // Handle viewing a lease document in preview modal
  const handleViewLeaseDocument = async (doc: LeaseDocument) => {
    if (!leaseInfo) return;
    try {
      setLoadingDocId(doc.id);
      const { secure_url } = await getLeaseDocumentSecureUrl(leaseInfo.lease_id, doc.id);
      setPreviewUrl(secure_url);
      setPreviewFileName(doc.name);
      setPreviewModalOpen(true);
    } catch (err) {
      console.error('Failed to get document URL:', err);
      Sentry.captureException(err);
    } finally {
      setLoadingDocId(null);
    }
  };

  // Close preview modal
  const handleClosePreview = () => {
    setPreviewModalOpen(false);
    setPreviewUrl(null);
    setPreviewFileName('');
  };

  // Handle downloading a lease document
  const handleDownloadLeaseDocument = async (doc: LeaseDocument) => {
    if (!leaseInfo) return;
    try {
      setLoadingDocId(`download-${doc.id}`);
      const { secure_url } = await getLeaseDocumentSecureUrl(leaseInfo.lease_id, doc.id);
      const link = document.createElement('a');
      link.href = secure_url;
      link.download = doc.name;
      link.click();
    } catch (err) {
      console.error('Failed to download document:', err);
      Sentry.captureException(err);
    } finally {
      setLoadingDocId(null);
    }
  };

  // Handle downloading a tenant document
  const handleDownloadTenantDocument = async (doc: TenantDocument) => {
    if (!leaseInfo) return;
    try {
      setLoadingDocId(`tenant-${doc.id}`);
      const { secure_url } = await getTenantDocumentSecureUrl(leaseInfo.tenant_id, doc.id);
      const link = document.createElement('a');
      link.href = secure_url;
      link.download = doc.file_name;
      link.click();
    } catch (err) {
      console.error('Failed to download document:', err);
      Sentry.captureException(err);
    } finally {
      setLoadingDocId(null);
    }
  };

  // Format document type for display
  const formatDocumentType = (type: string): string => {
    return type
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  if (isLoading) {
    return <LeaseDocumentsSkeleton />;
  }

  if (error || !leaseInfo) {
    return (
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
        <div className="text-center py-12">
          <FaFileContract className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">Unable to load documents</h3>
          <p className="mt-2 text-sm text-gray-500">
            {error?.message || 'Please try again later.'}
          </p>
        </div>
      </div>
    );
  }

  // Find the main lease document (contract type)
  const mainLeaseDoc = leaseDocuments.find(
    doc => doc.document_type === 'contract' || doc.document_type === 'lease'
  ) || leaseDocuments[0];

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200">
      <div className="p-6">
        {/* Page Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-800">Lease Documents</h1>
          <p className="mt-1 text-sm text-gray-500">
            Access and download your lease agreement and other important documents
          </p>
        </div>

        {/* Main Lease Agreement Card */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-gray-200 rounded-lg">
                <FaFileContract className="h-6 w-6 text-gray-700" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Lease Agreement</h2>
                <p className="text-sm text-gray-600">
                  Valid from {formatDateForDisplay(leaseInfo.lease_start)} to {formatDateForDisplay(leaseInfo.lease_end)}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              {mainLeaseDoc && (
                <>
                  <button
                    onClick={() => handleViewLeaseDocument(mainLeaseDoc)}
                    disabled={loadingDocId === mainLeaseDoc.id}
                    className="inline-flex items-center px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    <FaEye className="mr-2 h-4 w-4" />
                    {loadingDocId === mainLeaseDoc.id ? 'Loading...' : 'View Document'}
                  </button>
                  <button
                    onClick={() => handleDownloadLeaseDocument(mainLeaseDoc)}
                    disabled={loadingDocId === `download-${mainLeaseDoc.id}`}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    <FaDownload className="mr-2 h-4 w-4" />
                    Download
                  </button>
                </>
              )}
              {!mainLeaseDoc && (
                <span className="text-sm text-gray-500 italic">No document uploaded</span>
              )}
            </div>
          </div>

          {/* Lease Summary */}
          <div className="mt-6 border-t border-gray-200 pt-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Lease Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Property */}
              <div>
                <div className="flex items-center text-sm text-gray-500 mb-1">
                  <FaMapMarkerAlt className="mr-2 h-4 w-4 shrink-0" />
                  Property
                </div>
                <p className="font-medium text-gray-900 pl-6">{leaseInfo.property_address}</p>
                <p className="text-sm text-gray-600 pl-6">{leaseInfo.unit_name}</p>
              </div>

              {/* Lease Term */}
              <div>
                <div className="flex items-center text-sm text-gray-500 mb-1">
                  <FaCalendarAlt className="mr-2 h-4 w-4 shrink-0" />
                  Lease Term
                </div>
                <p className="font-medium text-gray-900 pl-6">
                  Start: {formatDateForDisplay(leaseInfo.lease_start)}
                </p>
                <p className="text-sm text-gray-600 pl-6">
                  End: {formatDateForDisplay(leaseInfo.lease_end)}
                </p>
              </div>

              {/* Monthly Rent */}
              <div>
                <div className="flex items-center text-sm text-gray-500 mb-1">
                  <FaDollarSign className="mr-2 h-4 w-4 shrink-0" />
                  Monthly Rent
                </div>
                <p className="font-medium text-gray-900 pl-6">{leaseInfo.monthly_rent}</p>
                <p className="text-sm text-gray-600 pl-6">
                  Due on the {getOrdinalSuffix(leaseInfo.rent_due_day)} of each month
                </p>
              </div>

              {/* Security Deposit */}
              <div>
                <div className="flex items-center text-sm text-gray-500 mb-1">
                  <FaBuilding className="mr-2 h-4 w-4 shrink-0" />
                  Security Deposit
                </div>
                <p className="font-medium text-gray-900 pl-6">{leaseInfo.security_deposit}</p>
                {leaseInfo.security_deposit_paid_date && (
                  <p className="text-sm text-gray-600 pl-6">
                    Paid on {formatDateForDisplay(leaseInfo.security_deposit_paid_date)}
                  </p>
                )}
              </div>

              {/* Landlord */}
              <div>
                <div className="flex items-center text-sm text-gray-500 mb-1">
                  <FaUser className="mr-2 h-4 w-4 shrink-0" />
                  Landlord
                </div>
                <p className="font-medium text-gray-900 pl-6">{leaseInfo.landlord_name}</p>
                {leaseInfo.landlord_email && (
                  <p className="text-sm text-gray-600 pl-6">{leaseInfo.landlord_email}</p>
                )}
              </div>

              {/* Tenant */}
              <div>
                <div className="flex items-center text-sm text-gray-500 mb-1">
                  <FaUsers className="mr-2 h-4 w-4 shrink-0" />
                  Tenant(s)
                </div>
                <p className="font-medium text-gray-900 pl-6">{leaseInfo.tenant_name}</p>
                <p className="text-sm text-gray-600 pl-6">{leaseInfo.tenant_email}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Additional Documents */}
        {additionalDocuments.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Additional Documents</h3>
            <div className="space-y-3">
              {additionalDocuments.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between py-3 px-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <FaFileAlt className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="font-medium text-gray-900">{doc.file_name}</p>
                      <p className="text-sm text-gray-500">
                        Uploaded on {formatDateForDisplay(doc.uploaded_at)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDownloadTenantDocument(doc)}
                    disabled={loadingDocId === `tenant-${doc.id}`}
                    className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    <FaDownload className="mr-2 h-4 w-4" />
                    {loadingDocId === `tenant-${doc.id}` ? 'Loading...' : 'Download'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Other Lease Documents (addendums, notices, etc.) */}
        {leaseDocuments.length > 1 && (
          <div className="bg-white border border-gray-200 rounded-xl p-6 mt-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Lease Addendums & Notices</h3>
            <div className="space-y-3">
              {leaseDocuments
                .filter(doc => doc.id !== mainLeaseDoc?.id)
                .map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between py-3 px-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <FaFileAlt className="h-5 w-5 text-gray-400" />
                      <div>
                        <p className="font-medium text-gray-900">{doc.name}</p>
                        <p className="text-sm text-gray-500">
                          {formatDocumentType(doc.document_type)} - Uploaded on {formatDateForDisplay(doc.upload_date)}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDownloadLeaseDocument(doc)}
                      disabled={loadingDocId === `download-${doc.id}`}
                      className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 transition-colors disabled:opacity-50 cursor-pointer"
                    >
                      <FaDownload className="mr-2 h-4 w-4" />
                      {loadingDocId === `download-${doc.id}` ? 'Loading...' : 'Download'}
                    </button>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Empty state for additional documents */}
        {additionalDocuments.length === 0 && leaseDocuments.length <= 1 && (
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="text-center py-8">
              <FaFileAlt className="mx-auto h-10 w-10 text-gray-300" />
              <h3 className="mt-3 text-sm font-medium text-gray-900">No additional documents</h3>
              <p className="mt-1 text-sm text-gray-500">
                Your landlord hasn't uploaded any additional documents yet.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* File Preview Modal */}
      <FilePreviewModal
        isOpen={previewModalOpen}
        onClose={handleClosePreview}
        fileUrl={previewUrl}
        fileName={previewFileName}
      />
    </div>
  );
};

// Helper function for ordinal suffix
const getOrdinalSuffix = (day: number): string => {
  if (day >= 11 && day <= 13) return `${day}th`;
  switch (day % 10) {
    case 1: return `${day}st`;
    case 2: return `${day}nd`;
    case 3: return `${day}rd`;
    default: return `${day}th`;
  }
};

// Skeleton loading component
const LeaseDocumentsSkeleton: React.FC = () => (
  <div className="bg-white rounded-lg shadow border border-gray-200 animate-pulse">
    <div className="p-6">
      {/* Header skeleton */}
      <div className="mb-6">
        <div className="h-8 bg-gray-200 rounded w-48 mb-2" />
        <div className="h-4 bg-gray-200 rounded w-96" />
      </div>

      {/* Main card skeleton */}
      <div className="bg-gray-100 rounded-xl p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 bg-gray-200 rounded-lg" />
            <div>
              <div className="h-6 bg-gray-200 rounded w-40 mb-2" />
              <div className="h-4 bg-gray-200 rounded w-64" />
            </div>
          </div>
          <div className="flex gap-2">
            <div className="h-10 w-32 bg-gray-200 rounded-lg" />
            <div className="h-10 w-24 bg-gray-200 rounded-lg" />
          </div>
        </div>

        {/* Summary skeleton */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="h-5 bg-gray-200 rounded w-32 mb-4" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i}>
                <div className="h-4 bg-gray-200 rounded w-20 mb-2" />
                <div className="h-5 bg-gray-200 rounded w-32 mb-1" />
                <div className="h-4 bg-gray-200 rounded w-28" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </div>
);

// Error fallback component for Sentry error boundary
function DocumentsErrorFallback({ error }: { error: unknown }): React.ReactElement {
  const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
  return (
    <div className="p-6 bg-red-50 border border-red-200 rounded-xl">
      <h3 className="font-semibold text-red-800">Documents Error</h3>
      <p className="mt-1 text-red-700">{errorMessage}</p>
      <button
        onClick={() => window.location.reload()}
        className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors cursor-pointer"
      >
        Reload Page
      </button>
    </div>
  );
}

// Wrap with Sentry error boundary for error tracking
const LeaseDocumentsContentWithErrorBoundary = Sentry.withErrorBoundary(LeaseDocumentsContent, {
  fallback: DocumentsErrorFallback,
});

export default LeaseDocumentsContentWithErrorBoundary;
