import React, { useState } from 'react';
import { EnrichedTenant, TenantStatus, MaintenancePriority, MaintenanceStatus } from '../../../types/tenant';
import { getInitials } from '../../../utils/tenantUtils';

interface TenantProfileHeaderProps {
  tenant: EnrichedTenant;
  onEdit: () => void;
  onDelete: () => void;
  onRefresh: () => void;
  onNewTicket?: (initialData: any) => void;
  onRecordPayment?: (initialData: any) => void;
  onUploadDocument?: () => void;
}

const TenantProfileHeader: React.FC<TenantProfileHeaderProps> = ({
  tenant,
  onEdit,
  onDelete,
  onRefresh,
  onNewTicket,
  onRecordPayment,
  onUploadDocument,
}) => {
  const [showMoreMenu, setShowMoreMenu] = useState(false);

  const getDisplayName = () => {
    if (tenant.tenant_type === 'Company') {
      return tenant.company_name || 'Company Tenant';
    }
    return `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim() || 'Individual Tenant';
  };

  const getStatusBadgeClass = (status: TenantStatus) => {
    const baseClasses = 'inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold';

    switch (status.toLowerCase()) {
      case 'active':
        return `${baseClasses} bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200`;
      case 'pending':
        return `${baseClasses} bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200`;
      case 'inactive':
        return `${baseClasses} bg-gray-100 dark:bg-gray-900/30 text-gray-800 dark:text-gray-200`;
      case 'evicted':
        return `${baseClasses} bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200`;
      case 'moved out':
        return `${baseClasses} bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200`;
      default:
        return `${baseClasses} bg-gray-100 dark:bg-gray-900/30 text-gray-800 dark:text-gray-200`;
    }
  };

  const getPropertyInfo = () => {
    const property = tenant.property?.name;
    const unit = tenant.unit?.name;
    if (property && unit) return `${property} • Unit ${unit}`;
    if (property) return property;
    return null;
  };

  const handleMessage = () => {
    // TODO: Implement messaging
    console.log('Message tenant');
  };

  const handleNewTicket = () => {
    if (!onNewTicket) return;
    
    // Get active lease to extract property and unit info
    const activeLease = tenant.leases?.find(lease => lease.status === 'ACTIVE');
    
    // Ensure all IDs are strings (modal expects strings for select inputs)
    const propertyId = activeLease?.property_id || tenant.current_property_id;
    const unitId = activeLease?.unit_id || tenant.unit?.id;
    
    const initialData = {
      tenant_id: tenant.id,
      property_id: propertyId ? String(propertyId) : '',
      unit_id: unitId ? String(unitId) : '',
      priority: MaintenancePriority.MEDIUM,  // Uses enum for type safety
      status: MaintenanceStatus.PENDING,     // Uses enum for type safety
    };

    onNewTicket(initialData);
  };

  const handleUpload = () => {
    if (onUploadDocument) {
      onUploadDocument();
    }
  };

  const handlePayment = () => {
    if (!onRecordPayment) return;
    
    // Get active lease to extract property and payment info
    const activeLease = tenant.leases?.find(lease => lease.status === 'ACTIVE');
    
    if (!activeLease) {
      // Could show a toast here, but button should be disabled if no active lease
      return;
    }

    const tenantName = tenant.tenant_type === 'Company'
      ? tenant.company_name || 'Company Tenant'
      : `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim();

    const propertyName = activeLease.property?.name || tenant.property?.name || '';
    const propertyId = activeLease.property?.id || tenant.current_property_id;

    const initialData = {
      tenant_id: tenant.id,
      tenant_name: tenantName,
      property_id: propertyId?.toString() || '',
      property_name: propertyName,
      lease_id: activeLease.id,
      amount: activeLease.monthly_rent?.toString() || '',
      payment_date: new Date().toISOString().split('T')[0],
      payment_method: 'Other',
      status: 'Paid',
    };

    onRecordPayment(initialData);
  };

  return (
    <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-6">
      <div className="flex items-start justify-between gap-6">
        {/* Left: Avatar and Info */}
        <div className="flex items-center gap-4 flex-1">
          {/* Avatar */}
          <div className="relative flex-shrink-0">
            {tenant.profile_image_url ? (
              <img
                src={tenant.profile_image_url}
                alt={getDisplayName()}
                className="w-20 h-20 rounded-full object-cover ring-4 ring-gray-100 dark:ring-gray-700"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center ring-4 ring-gray-100 dark:ring-gray-700">
                <span className="text-white font-bold text-2xl">
                  {getInitials({ full_name: getDisplayName() })}
                </span>
              </div>
            )}
            {tenant.tenant_type === 'Company' && (
              <div className="absolute -bottom-1 -right-1 bg-blue-500 rounded-full p-1.5 ring-2 ring-white dark:ring-gray-800">
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a1 1 0 110 2h-3a1 1 0 01-1-1v-2a1 1 0 00-1-1H9a1 1 0 00-1 1v2a1 1 0 01-1 1H4a1 1 0 110-2V4zm3 1h2v2H7V5zm2 4H7v2h2V9zm2-4h2v2h-2V5zm2 4h-2v2h2V9z" clipRule="evenodd" />
                </svg>
              </div>
            )}
          </div>

          {/* Name, Contact, and Property Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                {getDisplayName()}
              </h1>
              <span className={getStatusBadgeClass(tenant.status)}>
                <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5"></span>
                {tenant.status}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-gray-600 dark:text-gray-400">
              {tenant.email && (
                <a
                  href={`mailto:${tenant.email}`}
                  className="flex items-center gap-1.5 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  {tenant.email}
                </a>
              )}
              {tenant.phone && (
                <a
                  href={`tel:${tenant.phone}`}
                  className="flex items-center gap-1.5 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                  {tenant.phone}
                </a>
              )}
              {getPropertyInfo() && (
                <div className="flex items-center gap-1.5">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                  {getPropertyInfo()}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Action Buttons */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={handleMessage}
            disabled
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-400 dark:text-gray-500 cursor-not-allowed opacity-50 relative group"
            title="Coming Soon"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            Message
            <span className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
              Coming Soon
            </span>
          </button>

          <button
            onClick={handleNewTicket}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            New Ticket
          </button>

          <button
            onClick={handleUpload}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Upload
          </button>

          <button
            onClick={handlePayment}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Payment
          </button>

          {/* More Menu */}
          <div className="relative">
            <button
              onClick={() => setShowMoreMenu(!showMoreMenu)}
              className="p-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </button>

            {showMoreMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowMoreMenu(false)}
                />
                <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-700 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 z-20">
                  <button
                    onClick={() => {
                      onEdit();
                      setShowMoreMenu(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 first:rounded-t-lg"
                  >
                    Edit Tenant
                  </button>
                  <button
                    onClick={() => {
                      onRefresh();
                      setShowMoreMenu(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600"
                  >
                    Refresh
                  </button>
                  <button
                    onClick={() => {
                      onDelete();
                      setShowMoreMenu(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-600 last:rounded-b-lg"
                  >
                    Delete Tenant
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TenantProfileHeader;
