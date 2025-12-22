import React, { useMemo, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { toast } from 'react-toastify';
import * as Sentry from '@sentry/react';
import { EnrichedTenant } from '../../../../types/tenant';
import { formatDate } from '../../../../utils/tenantUtils';
import { getSecureDocumentUrl } from '../../../../utils/api/leases';
import { updateTenant, sendTenantReminder, TenantReminderRequest } from '../../../../utils/api/tenants';
import AIAuditTrail from '../AIAuditTrail';
import ReminderConfirmationModal from '../ReminderConfirmationModal';
import QuickActions from '../QuickActions';
import ViewLeaseModal from '../../../leases/modals/ViewLeaseModal';
import type { Lease } from '../../../../types/lease';
import {
  calculatePaymentPerformance,
  calculateOpenBalance,
  calculateTicketResolution,
  generateUpcomingEvents,
  getPaymentPerformanceColor,
  getOpenBalanceColor,
  getTicketResolutionColor,
  getEventIcon,
  UpcomingEvent
} from '../../../../utils/tenantMetrics.tsx';

interface OutletContext {
  tenant: EnrichedTenant;
  refetch: () => void;
  openFilePreviewModal: (url: string, name: string) => void;
  closeFilePreviewModal: () => void;
  openPaymentModal: (initialData: any) => void;
  openEmergencyContactModal: (contact?: any) => void;
  openMaintenanceModal: (initialData?: any) => void;
  openDocumentUploadModal: () => void;
}

const OverviewTab: React.FC = () => {
  const context = useOutletContext<OutletContext>();

  // State for delete confirmation and loading
  // Using array index instead of contactId for more reliable deletion
  const [deletingContactIndex, setDeletingContactIndex] = useState<number | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [contactIndexToDelete, setContactIndexToDelete] = useState<number | null>(null);
  
  // State for reminder sending
  const [sendingReminder, setSendingReminder] = useState<string | null>(null); // event.id
  const [showReminderModal, setShowReminderModal] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<UpcomingEvent | null>(null);

  // State for lease details modal (fallback when document preview fails)
  const [showLeaseModal, setShowLeaseModal] = useState(false);

  // Guard: Handle undefined context gracefully (occurs during refetch or initial load)
  // Parent TenantProfile handles the loading spinner, so we just return null briefly
  if (!context || !context.tenant) {
    return null;
  }

  const { tenant, refetch, openFilePreviewModal, openPaymentModal, openEmergencyContactModal, openMaintenanceModal, openDocumentUploadModal } = context;

  // Helper function to safely format currency
  const formatCurrency = (value: number | string | undefined | null): string => {
    if (value === undefined || value === null) return 'N/A';
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(numValue)) return 'N/A';
    return `$${numValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  // Get active lease
  const activeLease = tenant.leases?.find(lease => lease.status === 'ACTIVE');

  // Calculate total payments
  const totalPayments = tenant.payments?.reduce((sum, payment) => sum + payment.amount, 0) || 0;

  // Calculate all metrics from tenant data
  const metrics = useMemo(() => {
    return {
      paymentPerformance: calculatePaymentPerformance(tenant, activeLease),
      openBalance: calculateOpenBalance(tenant, activeLease),
      ticketResolution: calculateTicketResolution(tenant),
      upcomingEvents: generateUpcomingEvents(tenant, activeLease, calculateOpenBalance(tenant, activeLease))
    };
  }, [tenant, activeLease]);

  // Count overdue invoices

  // Get day suffix
  const getDaySuffix = (day: number): string => {
    if (day >= 11 && day <= 13) return 'th';
    switch (day % 10) {
      case 1: return 'st';
      case 2: return 'nd';
      case 3: return 'rd';
      default: return 'th';
    }
  };

  // Handle clicking Remind button - opens confirmation modal
  const handleRemindClick = (event: UpcomingEvent) => {
    if (!tenant || !tenant.email) {
      toast.error('Cannot send reminder: tenant does not have an email address');
      return;
    }
    setSelectedEvent(event);
    setShowReminderModal(true);
  };

  // Handle confirming reminder email
  const handleConfirmReminder = async (customSubject: string | null, customMessage: string | null) => {
    if (!selectedEvent || !tenant || !tenant.email) {
      toast.error('Cannot send reminder: missing information');
      setShowReminderModal(false);
      setSelectedEvent(null);
      return;
    }

    setSendingReminder(selectedEvent.id);

    try {
      // Prepare reminder data
      const reminderData: TenantReminderRequest = {
        event_type: selectedEvent.type as TenantReminderRequest['event_type'],
        event_title: selectedEvent.title,
        event_subtitle: selectedEvent.subtitle,
        event_date: selectedEvent.date ? selectedEvent.date.toISOString() : null,
        event_amount: selectedEvent.amount ?? null,
        days_remaining: selectedEvent.daysRemaining ?? null,
        custom_subject: customSubject,
        custom_message: customMessage,
      };

      // Send reminder via API
      const response = await sendTenantReminder(tenant.id, reminderData);

      if (response.success) {
        toast.success(`Reminder email sent to ${tenant.email}`);
        setShowReminderModal(false);
        setSelectedEvent(null);
      } else {
        toast.error('Failed to send reminder email');
      }
    } catch (error: any) {
      console.error('Failed to send reminder:', error);
      
      // Report to Sentry
      Sentry.captureException(error, {
        tags: {
          component: 'OverviewTab',
          action: 'send_reminder',
        },
        contexts: {
          tenant: { id: tenant?.id },
          event: { type: selectedEvent.type, id: selectedEvent.id },
        },
      });

      toast.error(error?.message || 'Failed to send reminder email. Please try again.');
    } finally {
      setSendingReminder(null);
    }
  };

  // Handle closing reminder modal
  const handleCloseReminderModal = () => {
    if (sendingReminder) return; // Prevent closing while sending
    setShowReminderModal(false);
    setSelectedEvent(null);
  };

  // Handle View Lease button
  const handleViewLease = async () => {
    if (!activeLease) {
      toast.error('No active lease found.');
      return;
    }

    const leaseDocument = activeLease.documents?.[0];

    // If no document attached, show lease details modal as fallback
    if (!leaseDocument || !leaseDocument.id) {
      setShowLeaseModal(true);
      return;
    }

    try {
      // Show loading toast
      const loadingToast = toast.info('Generating secure preview link...', {
        autoClose: false,
      });

      // Always fetch a fresh secure, time-limited URL with SAS token
      // This ensures we never use expired tokens
      const { secure_url, expires_at } = await getSecureDocumentUrl(
        activeLease.id,
        leaseDocument.id
      );

      // Dismiss loading toast
      toast.dismiss(loadingToast);

      // Log expiration for debugging
      console.log(`[DocumentPreview] Generated SAS URL, expires at: ${expires_at}`);

      // Open the preview modal with the secure URL
      const tenantName = tenant.tenant_type === 'Company'
        ? tenant.company_name
        : `${tenant.first_name} ${tenant.last_name}`;
      const propertyName = activeLease.property?.name || tenant.property?.name || 'Property';
      const fileName = `Lease: ${tenantName} - ${propertyName}`;
      openFilePreviewModal(secure_url, fileName);
    } catch (error: unknown) {
      console.error('[handleViewLease] Failed to generate secure URL:', error);

      // Show lease details modal as fallback when document preview fails
      setShowLeaseModal(true);

      // Show info toast explaining the fallback
      toast.info('Document preview unavailable. Showing lease details instead.');

      // Report to Sentry for monitoring
      Sentry.captureException(error, {
        tags: {
          component: 'OverviewTab',
          action: 'view_lease_document',
        },
        contexts: {
          lease: { id: activeLease.id },
          document: { id: leaseDocument.id },
        },
      });
    }
  };

  // Handle Record Payment button
  const handleRecordPayment = () => {
    if (!activeLease) {
      toast.error('No active lease found for this tenant.');
      return;
    }

    // Get initial data for payment modal
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

    // Open modal at page level with fresh initial data
    openPaymentModal(initialData);
  };

  // Emergency Contact Handlers
  const handleAddEmergencyContact = () => {
    openEmergencyContactModal();
  };

  const handleEditEmergencyContact = (contact: any) => {
    openEmergencyContactModal(contact);
  };

  /**
   * Handles the initiation of emergency contact deletion
   * Security: Uses state-based confirmation instead of window.confirm for better UX
   * and to prevent CSRF-like issues with browser-level dialogs
   *
   * Using array index instead of optional contactId to prevent
   * silent deletion failures when ID field is missing
   *
   * @param contactIndex - The array index of the contact to delete
   */
  const handleDeleteEmergencyContact = (contactIndex: number) => {
    setContactIndexToDelete(contactIndex);
    setShowDeleteConfirm(true);
  };

  /**
   * Confirms and executes emergency contact deletion
   * Security considerations:
   * - Validates tenant.id and contact existence before API call
   * - Disables UI during operation to prevent race conditions
   * - Tracks errors in Sentry for security monitoring
   * - Backend validates the operation with Pydantic schemas
   *
   * Uses array index for reliable deletion, preventing silent
   * failures when optional ID field is missing
   */
  const confirmDeleteContact = async () => {
    if (contactIndexToDelete === null || !tenant.id) {
      toast.error('Invalid operation');
      setShowDeleteConfirm(false);
      setContactIndexToDelete(null);
      return;
    }

    // Set loading state to prevent duplicate submissions
    setDeletingContactIndex(contactIndexToDelete);

    try {
      // Filter out the contact at the specified index
      // Using index-based filtering instead of ID-based
      const updatedContacts = tenant.emergency_contacts?.filter((_c, index) => index !== contactIndexToDelete) || [];

      // Update tenant with new contacts list
      await updateTenant(tenant.id, { emergency_contacts: updatedContacts });

      // Refetch tenant data to ensure consistency
      await refetch();

      toast.success('Emergency contact removed successfully');

      // Track successful deletion in Sentry for audit purposes
      Sentry.addBreadcrumb({
        category: 'emergency_contact',
        message: 'Emergency contact deleted',
        level: 'info',
        data: {
          tenant_id: tenant.id,
          contact_index: contactIndexToDelete,
        },
      });
    } catch (error: any) {
      console.error('Failed to delete emergency contact:', error);

      // Track deletion failure in Sentry with full context
      Sentry.captureException(error, {
        tags: {
          component: 'tenant_profile',
          action: 'delete_emergency_contact',
          tenant_id: tenant.id.toString(),
        },
        contexts: {
          emergency_contact: {
            contact_index: contactIndexToDelete,
            tenant_id: tenant.id,
            total_contacts: tenant.emergency_contacts?.length || 0,
          },
        },
      });

      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to remove emergency contact. Please try again.';
      toast.error(errorMessage);
    } finally {
      // Reset state
      setDeletingContactIndex(null);
      setShowDeleteConfirm(false);
      setContactIndexToDelete(null);
    }
  };

  /**
   * Cancels the delete confirmation
   */
  const cancelDeleteContact = () => {
    setShowDeleteConfirm(false);
    setContactIndexToDelete(null);
  };

  return (
    <div className="space-y-6">
      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - 2/3 width */}
        <div className="lg:col-span-2 space-y-6">
          {/* 3 Metric Cards Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Payment Performance */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Payment Performance</h4>
                <div className={`w-8 h-8 rounded-lg ${getPaymentPerformanceColor(metrics.paymentPerformance).bg} flex items-center justify-center flex-shrink-0`}>
                  <svg className={`w-4 h-4 ${getPaymentPerformanceColor(metrics.paymentPerformance).icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
              </div>
              <div className="mb-1">
                <span className={`text-3xl font-bold ${metrics.paymentPerformance.rate !== null ? 'text-gray-900 dark:text-gray-100' : 'text-gray-400 dark:text-gray-600'}`}>
                  {metrics.paymentPerformance.rate !== null ? `${metrics.paymentPerformance.rate}%` : '—'}
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {metrics.paymentPerformance.totalCount > 0 
                  ? `${metrics.paymentPerformance.onTimeCount}/${metrics.paymentPerformance.totalCount} on-time payments`
                  : 'No payment history yet'}
              </p>
            </div>

            {/* Ticket Resolution */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Ticket Resolution</h4>
                <div className={`w-8 h-8 rounded-lg ${getTicketResolutionColor(metrics.ticketResolution).bg} flex items-center justify-center flex-shrink-0`}>
                  <svg className={`w-4 h-4 ${getTicketResolutionColor(metrics.ticketResolution).icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <div className="mb-1">
                <span className={`text-3xl font-bold ${metrics.ticketResolution.avgDays !== null ? 'text-gray-900 dark:text-gray-100' : 'text-gray-400 dark:text-gray-600'}`}>
                  {metrics.ticketResolution.avgDays !== null ? metrics.ticketResolution.avgDays : '—'}
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {metrics.ticketResolution.totalCount > 0
                  ? `${metrics.ticketResolution.completedCount} completed, ${metrics.ticketResolution.pendingCount} pending`
                  : 'No maintenance requests'}
              </p>
            </div>

            {/* Total Outstanding */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Total Outstanding</h4>
                <div className={`w-8 h-8 rounded-lg ${getOpenBalanceColor(metrics.openBalance.totalBalance, metrics.openBalance.isOverdue, activeLease?.monthly_rent ? Number(activeLease.monthly_rent) : 0).bg} flex items-center justify-center flex-shrink-0`}>
                  <svg className={`w-4 h-4 ${getOpenBalanceColor(metrics.openBalance.totalBalance, metrics.openBalance.isOverdue, activeLease?.monthly_rent ? Number(activeLease.monthly_rent) : 0).icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <div className="mb-1">
                <span className={`text-3xl font-bold ${getOpenBalanceColor(metrics.openBalance.totalBalance, metrics.openBalance.isOverdue, activeLease?.monthly_rent ? Number(activeLease.monthly_rent) : 0).text}`}>
                  ${metrics.openBalance.totalBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {metrics.openBalance.totalBalance === 0
                  ? 'No outstanding balance'
                  : metrics.openBalance.isOverdue
                    ? `$${metrics.openBalance.overdueBalance.toLocaleString()} overdue`
                    : 'Current balance'}
              </p>
            </div>
          </div>

          {/* Current Lease and Payment Summary Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Current Lease Card */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                  <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Current Lease
                </h3>
                {activeLease && (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
                    Active
                  </span>
                )}
              </div>

              {activeLease ? (
                <div className="space-y-5">
                  <div className="grid grid-cols-2 gap-x-6 gap-y-4">
                    <div>
                      <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">Property</div>
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {activeLease.property?.name || tenant.property?.name || 'N/A'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">Unit</div>
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {activeLease.unit?.name || tenant.unit?.name || 'N/A'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">Monthly Rent</div>
                      <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {formatCurrency(activeLease.monthly_rent)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">Balance</div>
                      <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        $0.00
                      </div>
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t border-gray-100 dark:border-gray-700">
                    <div className="grid grid-cols-2 gap-x-6 gap-y-4">
                      <div>
                        <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">Term</div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {formatDate(activeLease.start_date)} - {formatDate(activeLease.end_date)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">Due Day</div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {activeLease.rent_due_day ? `${activeLease.rent_due_day}${getDaySuffix(activeLease.rent_due_day)} of month` : 'N/A'}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="pt-5 border-t border-gray-100 dark:border-gray-700">
                    <button
                      onClick={handleViewLease}
                      className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors w-full"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      View Lease
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="mx-auto w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center mb-3">
                    <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">No active lease</p>
                </div>
              )}
            </div>

            {/* Payment Summary Card */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 h-full flex flex-col">
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-5 flex items-center gap-2">
                <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Payment Summary
              </h3>
              <div className="flex flex-col flex-1 justify-between">
                <div className="grid grid-cols-2 gap-x-6 gap-y-5">
                  <div>
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-1.5">Total Paid</span>
                    <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(totalPayments)}</span>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-1.5">Outstanding</span>
                    <span className={`text-lg font-semibold ${metrics.openBalance.totalBalance > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-gray-100'}`}>
                      ${metrics.openBalance.totalBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-1.5">Next Due</span>
                    {metrics.openBalance.nextDueAmount && metrics.openBalance.nextDueDate ? (
                      <>
                        <span className="text-lg font-semibold text-gray-900 dark:text-gray-100 block">
                          ${metrics.openBalance.nextDueAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 block">
                          {metrics.openBalance.nextDueDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </span>
                      </>
                    ) : (
                      <span className="text-lg font-semibold text-gray-400 dark:text-gray-600">N/A</span>
                    )}
                  </div>
                  <div>
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-1.5">Security Deposit</span>
                    <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      {activeLease ? formatCurrency(activeLease.security_deposit) : 'N/A'}
                    </span>
                  </div>
                </div>
                
                <div className="pt-6 border-t border-gray-100 dark:border-gray-700 mt-6">
                  <button
                    onClick={handleRecordPayment}
                    disabled={!activeLease}
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Record Payment
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Insurance Card */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 relative opacity-50">
            {/* Coming Soon Overlay */}
            <div className="absolute inset-0 bg-gray-900/5 dark:bg-gray-900/20 backdrop-blur-[2px] rounded-lg flex items-center justify-center z-10">
              <span className="px-4 py-2 bg-white dark:bg-gray-800 border-2 border-gray-300 dark:border-gray-600 rounded-lg text-sm font-semibold text-gray-600 dark:text-gray-400 shadow-sm">
                Coming Soon
              </span>
            </div>

            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                <svg className="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                Insurance
              </h3>
              <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
                Verified
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div>
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">Provider</div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">State Farm</div>
              </div>
              <div>
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">Policy #</div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">SF-2024-001</div>
              </div>
              <div>
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">Expiry Date</div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">Dec 31, 2025</div>
              </div>
            </div>
          </div>

          {/* AI Audit Trail */}
          <div className="relative">
            {/* Coming Soon Overlay */}
            <div className="absolute inset-0 bg-gray-900/5 dark:bg-gray-900/20 backdrop-blur-[2px] rounded-lg flex items-center justify-center z-10">
              <span className="px-4 py-2 bg-white dark:bg-gray-800 border-2 border-gray-300 dark:border-gray-600 rounded-lg text-sm font-semibold text-gray-600 dark:text-gray-400 shadow-sm">
                Coming Soon
              </span>
            </div>
            <div className="opacity-50">
              <AIAuditTrail tenant={tenant} />
            </div>
          </div>
        </div>

        {/* Right Column - 1/3 width (Sidebar) */}
        <div className="space-y-5">
          {/* Upcoming Section */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
              <svg className="w-4 h-4 text-orange-600 dark:text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Upcoming
            </h3>
            <div className="space-y-3">
              {metrics.upcomingEvents.length > 0 ? (
                metrics.upcomingEvents.map((event, index) => (
                  <div 
                    key={event.id} 
                    className={`flex items-center gap-3 ${index < metrics.upcomingEvents.length - 1 ? 'pb-3 border-b border-gray-100 dark:border-gray-700' : ''}`}
                  >
                    <div className={`flex-shrink-0 w-9 h-9 ${event.bgColor} rounded-lg flex items-center justify-center`}>
                      <div className={event.color}>
                        {getEventIcon(event.icon)}
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{event.title}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{event.subtitle}</div>
                    </div>
                    <button 
                      onClick={() => handleRemindClick(event)}
                      disabled={sendingReminder === event.id || !tenant.email}
                      className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {sendingReminder === event.id ? 'Sending...' : 'Remind'}
                    </button>
                  </div>
                ))
              ) : (
                <div className="text-center py-6">
                  <div className="mx-auto w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center mb-3">
                    <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">All caught up!</p>
                  <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">No upcoming events</p>
                </div>
              )}
            </div>
          </div>

          {/* Contacts Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
            <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            Contacts
          </h3>
          <div className="space-y-4">
            {/* Tenant Contact - Always shown */}
            <div>
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                Tenant Contact
              </div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                {tenant.tenant_type === 'Company' ? tenant.company_name : `${tenant.first_name} ${tenant.last_name}`}
              </div>
              {tenant.email && (
                <a href={`mailto:${tenant.email}`} className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 block mb-1">
                  {tenant.email}
                </a>
              )}
              {tenant.phone && (
                <a href={`tel:${tenant.phone}`} className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 block">
                  {tenant.phone}
                </a>
              )}
            </div>

            {/* Emergency Contacts Section */}
            {tenant.emergency_contacts && tenant.emergency_contacts.length > 0 ? (
              <div className="pt-4 border-t border-gray-100 dark:border-gray-700">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    Emergency Contacts
                  </div>
                  <button
                    onClick={handleAddEmergencyContact}
                    className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                  >
                    + Add
                  </button>
                </div>

                <div className="space-y-3">
                  {tenant.emergency_contacts.map((contact, index) => (
                    <div key={contact.id || index} className="relative group">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1 flex items-center gap-2">
                        {contact.name}
                        {contact.is_primary && (
                          <span className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-md font-medium">
                            Primary
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                        {contact.relationship}
                      </div>
                      <a href={`tel:${contact.phone}`} className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 block mb-1">
                        {contact.phone}
                      </a>
                      {contact.email && (
                        <a href={`mailto:${contact.email}`} className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 block">
                          {contact.email}
                        </a>
                      )}
                      {contact.notes && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 italic">
                          {contact.notes}
                        </p>
                      )}

                      {/* Edit/Delete buttons on hover */}
                      <div className="absolute top-0 right-0 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                        <button
                          onClick={() => handleEditEmergencyContact(contact)}
                          className="text-xs text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 font-medium"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteEmergencyContact(index)}
                          className="text-xs text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 font-medium"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="pt-4 border-t border-gray-100 dark:border-gray-700">
                <div className="text-center py-4">
                  <div className="mx-auto w-10 h-10 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center mb-2">
                    <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">No emergency contacts</p>
                  <button
                    onClick={handleAddEmergencyContact}
                    className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                  >
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Add Emergency Contact
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <QuickActions
          tenant={tenant}
          onNewTicket={(initialData) => openMaintenanceModal(initialData)}
          onUploadDocument={() => openDocumentUploadModal()}
          onRecordPayment={handleRecordPayment}
        />

        {/* Compliance */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5 relative opacity-50">
          {/* Coming Soon Overlay */}
          <div className="absolute inset-0 bg-gray-900/5 dark:bg-gray-900/20 backdrop-blur-[2px] rounded-lg flex items-center justify-center z-10">
            <span className="px-4 py-2 bg-white dark:bg-gray-800 border-2 border-gray-300 dark:border-gray-600 rounded-lg text-sm font-semibold text-gray-600 dark:text-gray-400 shadow-sm">
              Coming Soon
            </span>
          </div>

          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Compliance</h3>
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0 w-9 h-9 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">All compliant</div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Last checked 2 days ago</div>
            </div>
          </div>
        </div>
        </div>
      </div>

      {/* Reminder Confirmation Modal */}
      {selectedEvent && (
        <ReminderConfirmationModal
          isOpen={showReminderModal}
          onClose={handleCloseReminderModal}
          onConfirm={handleConfirmReminder}
          tenant={tenant}
          event={selectedEvent}
          isLoading={sendingReminder === selectedEvent.id}
        />
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-shrink-0 w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Delete Emergency Contact
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Are you sure you want to delete this emergency contact? This action cannot be undone.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 mt-6">
              <button
                onClick={cancelDeleteContact}
                disabled={deletingContactIndex !== null}
                className="flex-1 px-4 py-2.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteContact}
                disabled={deletingContactIndex !== null}
                className="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {deletingContactIndex !== null ? (
                  <>
                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Deleting...
                  </>
                ) : (
                  'Delete'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Lease Modal (fallback when document preview fails) */}
      <ViewLeaseModal
        isOpen={showLeaseModal}
        onClose={() => setShowLeaseModal(false)}
        lease={activeLease as Lease | null}
      />
    </div>
  );
};

export default OverviewTab;
