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
import EmergencyContactModal from '../components/tenants/modals/EmergencyContactModal';

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

  // Fetch tenant data
  const { data: tenant, isLoading, error, refetch } = useQuery<EnrichedTenant>({
    queryKey: QUERY_KEYS.tenants.detail(Number(id)),
    queryFn: () => fetchTenant(Number(id)),
    enabled: !!id,
    staleTime: 1 * 60 * 1000, // 1 minute
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
    // TODO: Implement edit modal
    console.log('Edit tenant:', tenant);
  };

  const handleDelete = () => {
    // TODO: Implement delete with confirmation
    console.log('Delete tenant:', tenant);
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

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors duration-300">
        <div className="flex items-center justify-center h-96">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-blue-200 dark:border-blue-800 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading tenant profile...</p>
          </div>
        </div>
      </div>
    );
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
      />

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
        <Outlet context={{ tenant, refetch, openFilePreviewModal, closeFilePreviewModal, openPaymentModal, openEmergencyContactModal }} />
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
    </div>
  );
};

export default TenantProfile;
