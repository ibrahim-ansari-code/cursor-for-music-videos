import React, { useState } from 'react';
import { useParams, Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import {
  fetchTenant,
  addEmergencyContact,
  updateEmergencyContact
} from '../utils/api/tenants';
import { EnrichedTenant, EmergencyContact } from '../types/tenant';
import { QUERY_KEYS } from '../hooks/queryKeys';
import TenantProfileHeader from '../components/tenants/TenantProfile/ProfileHeader';
import FilePreviewModal from '../components/FilePreviewModal';
import NewPaymentModal from '../components/accounting/modals/NewPaymentModal';
import ViewLeaseModal from '../components/leases/modals/ViewLeaseModal';
import EmergencyContactModal from '../components/tenants/modals/EmergencyContactModal';
import CreateMaintenanceModal from '../components/maintenance/CreateMaintenanceModal/index';
import EditMaintenanceModal from '../components/maintenance/EditMaintenanceModal';
import DocumentUploadModal from '../components/tenants/TenantProfile/tabs/DocumentsTab/DocumentUploadModal';
import DocumentEditModal from '../components/tenants/TenantProfile/tabs/DocumentsTab/DocumentEditModal';
import { TenantDocument } from '../types/tenantDocument';
import UpdateTenantModal from '../components/tenants/UpdateTenantModal';
import DeleteTenantConfirmationModal from '../components/tenants/DeleteTenantConfirmationModal';
import { createMaintenanceRequest, deleteTenant } from '../utils/api';
import { updateMaintenanceRequest } from '../utils/api/maintenance';
import { fetchLease } from '../utils/api/leases';
import type { Lease } from '../types/lease';
import { TenantProfileSkeleton } from '../components/ui/skeletons';

const TenantProfile: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const navigate = useNavigate();

  // File preview modal state (lifted to this level for proper fixed positioning)
  const [showFilePreviewModal, setShowFilePreviewModal] = useState(false);
  const [fileToPreviewUrl, setFileToPreviewUrl] = useState<string | null>(null);
  const [filePreviewName, setFilePreviewName] = useState('');

  // Payment modal state (lifted to this level for proper fixed positioning and z-index)
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentModalInitialData, setPaymentModalInitialData] = useState<any>({});

  // Emergency Contact modal state (lifted to this level for proper fixed positioning and z-index)
  const [showEmergencyContactModal, setShowEmergencyContactModal] = useState(false);
  const [editingContact, setEditingContact] = useState<any>(undefined);

  // Maintenance Request modal state (lifted to this level for proper fixed positioning and z-index)
  const [showMaintenanceModal, setShowMaintenanceModal] = useState(false);
  const [maintenanceModalData, setMaintenanceModalData] = useState<any>(null);
  const [isViewingMaintenance, setIsViewingMaintenance] = useState(false);
  const [isSubmittingMaintenance, setIsSubmittingMaintenance] = useState(false);

  // Document Upload modal state (lifted to this level for proper fixed positioning and z-index)
  const [showDocumentUploadModal, setShowDocumentUploadModal] = useState(false);

  // Document Edit modal state (lifted to this level for proper fixed positioning and z-index)
  const [showDocumentEditModal, setShowDocumentEditModal] = useState(false);
  const [editingDocument, setEditingDocument] = useState<TenantDocument | null>(null);

  // Lease modal state (lifted to this level for proper fixed positioning and z-index)
  const [showLeaseModal, setShowLeaseModal] = useState(false);
  const [selectedLease, setSelectedLease] = useState<Lease | null>(null);

  // Edit Tenant modal state
  const [showEditTenantModal, setShowEditTenantModal] = useState(false);

  // Delete Tenant confirmation modal state
  const [showDeleteTenantModal, setShowDeleteTenantModal] = useState(false);

  // Fetch tenant data with optimized caching strategy
  // - staleTime: 2 minutes (allows tab switching without refetch)
  // - refetchOnMount: false (don't refetch if data is fresh)
  // - refetchOnWindowFocus: false (don't refetch on window focus)
  // This prevents "Loading..." states during tab navigation while still
  // allowing mutations to invalidate and refetch immediately
  const { data: tenant, isLoading, isFetching, error, refetch } = useQuery<EnrichedTenant>({
    queryKey: QUERY_KEYS.tenants.detail(Number(id)),
    queryFn: () => fetchTenant(Number(id)),
    enabled: !!id,
    staleTime: 2 * 60 * 1000, // 2 minutes - optimized for tab switching without refetch
    gcTime: 10 * 60 * 1000, // 10 minutes - keep in memory for back/forward navigation
    refetchOnMount: false, // Don't refetch if data is still fresh
    refetchOnWindowFocus: false, // Don't refetch on window focus (prevents loading states)
  });

  // Determine active tab from URL
  const getActiveTab = () => {
    const path = location.pathname;
    if (path.includes('/leases')) return 'leases';
    if (path.includes('/documents')) return 'documents';
    if (path.includes('/maintenance')) return 'maintenance';
    if (path.includes('/payments')) return 'payments';
    if (path.includes('/messaging')) return 'messaging';
    if (path.includes('/background')) return 'background';
    if (path.includes('/assets')) return 'assets';
    if (path.includes('/settings')) return 'settings';
    return 'overview';
  };

  const activeTab = getActiveTab();

  // Tab configuration
  const tabs = [
    { id: 'overview', label: 'Overview', path: '' },
    { id: 'leases', label: 'Leases', path: 'leases' },
    { id: 'documents', label: 'Documents', path: 'documents' },
    { id: 'maintenance', label: 'Maintenance', path: 'maintenance' },
    { id: 'payments', label: 'Payments', path: 'payments' },
    { id: 'messaging', label: 'Messaging', path: 'messaging' },
    { id: 'background', label: 'Background', path: 'background' },
    { id: 'assets', label: 'Assets', path: 'assets' },
    { id: 'settings', label: 'Settings', path: 'settings' },
  ];

  const handleEdit = () => {
    setShowEditTenantModal(true);
  };

  const handleEditTenantSave = () => {
    // Refetch tenant data after successful update
    refetch();
    toast.success('Tenant updated successfully!');
  };

  const handleDelete = () => {
    setShowDeleteTenantModal(true);
  };

  const handleConfirmDeleteTenant = async () => {
    if (!tenant) return;
    
    try {
      await deleteTenant(tenant.id);
      toast.success('Tenant deleted successfully!');
      // Navigate back to tenants list after deletion
      navigate('/tenants');
    } catch (error) {
      console.error('Failed to delete tenant:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete tenant';
      toast.error(errorMessage);
      // Re-throw to let the modal handle the error state
      return Promise.reject(error);
    }
  };

  const handleRefresh = () => {
    refetch();
  };

  // Modal handlers to be passed to child components
  const openFilePreviewModal = (url: string, name: string) => {
    setFileToPreviewUrl(url);
    setFilePreviewName(name);
    setShowFilePreviewModal(true);
  };

  const closeFilePreviewModal = () => {
    setShowFilePreviewModal(false);
    setFileToPreviewUrl(null);
    setFilePreviewName('');
  };

  const openPaymentModal = (initialData: any = {}) => {
    setPaymentModalInitialData(initialData);
    setShowPaymentModal(true);
  };

  const closePaymentModal = () => {
    setShowPaymentModal(false);
    setPaymentModalInitialData({});
  };

  const openEmergencyContactModal = (contact?: any) => {
    setEditingContact(contact);
    setShowEmergencyContactModal(true);
  };

  const closeEmergencyContactModal = () => {
    setShowEmergencyContactModal(false);
    setEditingContact(undefined);
  };

  const handleSaveEmergencyContact = async (contact: EmergencyContact) => {
    if (!tenant) return;

    try {
      // Use atomic backend endpoints instead of full tenant update
      // This prevents race conditions and handles primary contact logic atomically on backend
      if (editingContact) {
        // Update existing contact atomically
        await updateEmergencyContact(tenant.id, contact.id!, contact);
        toast.success('Emergency contact updated');
      } else {
        // Add new contact atomically
        await addEmergencyContact(tenant.id, contact);
        toast.success('Emergency contact added');
      }

      // Refetch tenant data to get updated emergency contacts
      await refetch();
      closeEmergencyContactModal();
    } catch (error: any) {
      console.error('Failed to save emergency contact:', error);
      toast.error('Failed to save emergency contact. Please try again.');
      throw error; // Re-throw to let modal handle it
    }
  };

  const openMaintenanceModal = (initialData: any = null) => {
    // Check if this is a view-only request
    const isViewing = initialData?.isViewing === true;
    
    // Remove isViewing from the data object so it doesn't persist in state
    const { isViewing: _removed, ...dataWithoutFlag } = initialData || {};
    
    setMaintenanceModalData(dataWithoutFlag);
    setIsViewingMaintenance(isViewing);
    setShowMaintenanceModal(true);
  };

  const closeMaintenanceModal = () => {
    setShowMaintenanceModal(false);
    setMaintenanceModalData(null);
    setIsViewingMaintenance(false);
  };

  const handleSubmitMaintenanceRequest = async (requestData: any) => {
    setIsSubmittingMaintenance(true);
    try {
      // Check if we're updating an existing request or creating a new one
      if (maintenanceModalData?.id) {
        // Update existing request
        await updateMaintenanceRequest(maintenanceModalData.id, requestData);
        await refetch();
        closeMaintenanceModal();
        toast.success('Maintenance request updated successfully!');
      } else {
        // Create new request
        await createMaintenanceRequest(requestData);
        await refetch();
        closeMaintenanceModal();
        toast.success('Maintenance request created successfully!');
      }
    } catch (error: any) {
      console.error('Failed to save maintenance request:', error);
      toast.error(error?.message || 'Failed to save maintenance request');
      throw error; // Let modal handle error display
    } finally {
      setIsSubmittingMaintenance(false);
    }
  };

  const openDocumentUploadModal = () => {
    setShowDocumentUploadModal(true);
  };

  const closeDocumentUploadModal = () => {
    setShowDocumentUploadModal(false);
  };

  const openDocumentEditModal = (document: TenantDocument) => {
    setEditingDocument(document);
    setShowDocumentEditModal(true);
  };

  const closeDocumentEditModal = () => {
    setShowDocumentEditModal(false);
    setEditingDocument(null);
  };

  const openLeaseModal = async (leaseId: number) => {
    try {
      const lease = await fetchLease(leaseId);
      setSelectedLease(lease);
      setShowLeaseModal(true);
    } catch (error: any) {
      console.error('Failed to load lease:', error);
      toast.error('Failed to load lease details');
    }
  };

  const closeLeaseModal = () => {
    setShowLeaseModal(false);
    setSelectedLease(null);
  };

  // Show skeleton while loading - provides seamless transition from Suspense fallback
  if (isLoading) {
    return <TenantProfileSkeleton />;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white dark:bg-gray-900 p-6 transition-colors duration-300">
        <div className="max-w-md mx-auto text-center">
          <div className="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Failed to Load Tenant</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {error instanceof Error ? error.message : 'An error occurred while loading the tenant profile.'}
          </p>
          <button
            onClick={() => navigate('/tenants')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Back to Tenants
          </button>
        </div>
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="min-h-screen bg-white dark:bg-gray-900 p-6 transition-colors duration-300">
        <div className="text-center">
          <p className="text-gray-600 dark:text-gray-400">Tenant not found.</p>
          <button
            onClick={() => navigate('/tenants')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Back to Tenants
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
      {/* Header */}
      <TenantProfileHeader
        tenant={tenant}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onRefresh={handleRefresh}
        onNewTicket={openMaintenanceModal}
        onRecordPayment={openPaymentModal}
        onUploadDocument={openDocumentUploadModal}
      />

      {/* Fetching Indicator - Subtle loading bar when refetching in background */}
      {isFetching && (
        <div className="h-1 bg-gradient-to-r from-green-500 via-green-600 to-green-500 animate-pulse" />
      )}

      {/* Tab Navigation */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="px-6">
          <nav className="flex space-x-8" aria-label="Tabs">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <Link
                  key={tab.id}
                  to={tab.path}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm transition-colors
                    ${isActive
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                    }
                  `}
                >
                  {tab.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6 max-w-[1600px] mx-auto">
        <Outlet context={{ tenant, refetch, openFilePreviewModal, closeFilePreviewModal, openPaymentModal, openEmergencyContactModal, openMaintenanceModal, openDocumentUploadModal, openDocumentEditModal, openLeaseModal }} />
      </div>

      {/* File Preview Modal - Rendered at root level for proper fixed positioning */}
      <FilePreviewModal
        isOpen={showFilePreviewModal}
        onClose={closeFilePreviewModal}
        fileUrl={fileToPreviewUrl}
        fileName={filePreviewName}
      />

      {/* Payment Modal - Rendered at root level for proper fixed positioning and z-index */}
      <NewPaymentModal
        isOpen={showPaymentModal}
        onClose={closePaymentModal}
        onSuccess={() => {
          refetch();
          closePaymentModal();
          toast.success('Payment recorded successfully!');
        }}
        initialData={paymentModalInitialData}
      />

      {/* Emergency Contact Modal - Rendered at root level for proper fixed positioning and z-index */}
      {tenant && (
        <EmergencyContactModal
          isOpen={showEmergencyContactModal}
          onClose={closeEmergencyContactModal}
          onSave={handleSaveEmergencyContact}
          existingContact={editingContact}
          existingContacts={tenant.emergency_contacts || []}
        />
      )}

      {/* Maintenance Request Modal - Rendered at root level for proper fixed positioning and z-index */}
      {/* Create Modal - shown when no existing request id (maintenanceModalData may have initial values for pre-fill) */}
      {showMaintenanceModal && !maintenanceModalData?.id && (
        <CreateMaintenanceModal
          isOpen={showMaintenanceModal}
          onClose={closeMaintenanceModal}
          onSubmit={handleSubmitMaintenanceRequest}
          isSubmitting={isSubmittingMaintenance}
          initialData={maintenanceModalData}
        />
      )}

      {/* Edit/View Modal - shown when editing an existing request (has id) */}
      {showMaintenanceModal && maintenanceModalData?.id && (
        <EditMaintenanceModal
          isOpen={showMaintenanceModal}
          onClose={closeMaintenanceModal}
          onSubmit={handleSubmitMaintenanceRequest}
          request={maintenanceModalData}
          isViewing={isViewingMaintenance}
          isSubmitting={isSubmittingMaintenance}
        />
      )}

      {/* Document Upload Modal - Rendered at root level for proper fixed positioning and z-index */}
      {tenant && (
        <DocumentUploadModal
          isOpen={showDocumentUploadModal}
          onClose={closeDocumentUploadModal}
          tenantId={tenant.id?.toString() || ''}
          tenantName={
            tenant.tenant_type === 'Company'
              ? tenant.company_name || tenant.contact_person || 'Company'
              : `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim() || 'Tenant'
          }
        />
      )}

      {/* Document Edit Modal - Rendered at root level for proper fixed positioning and z-index */}
      {tenant?.id && (
        <DocumentEditModal
          isOpen={showDocumentEditModal}
          onClose={closeDocumentEditModal}
          document={editingDocument}
          tenantId={tenant.id.toString()}
        />
      )}

      {/* View Lease Modal - Rendered at root level for proper fixed positioning and z-index */}
      <ViewLeaseModal
        isOpen={showLeaseModal}
        onClose={closeLeaseModal}
        lease={selectedLease}
      />

      {/* Edit Tenant Modal - Rendered at root level for proper fixed positioning and z-index */}
      {tenant && (
        <UpdateTenantModal
          isOpen={showEditTenantModal}
          onClose={() => setShowEditTenantModal(false)}
          tenant={tenant}
          onSave={handleEditTenantSave}
        />
      )}

      {/* Delete Tenant Confirmation Modal - Rendered at root level for proper fixed positioning and z-index */}
      <DeleteTenantConfirmationModal
        isOpen={showDeleteTenantModal}
        onClose={() => setShowDeleteTenantModal(false)}
        tenant={tenant ?? null}
        onConfirm={handleConfirmDeleteTenant}
      />
    </div>
  );
};

export default TenantProfile;
