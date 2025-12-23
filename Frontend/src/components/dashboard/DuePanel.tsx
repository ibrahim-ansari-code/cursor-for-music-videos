import React, { useState } from "react";
import { createPortal } from "react-dom";
import { toast } from "react-toastify";
import * as Sentry from "@sentry/react";
import { formatCurrency, getAvatarColor as utilAvatarColor, getInitials } from "../../utils/formatters";
import { DuePanelSkeleton } from "../ui/skeletons";
import type { PaymentDue } from "../../utils/api/dashboard";
import ReminderMethodModal, { type ReminderMethod } from "../tenants/TenantProfile/ReminderMethodModal";
import ReminderConfirmationModal from "../tenants/TenantProfile/ReminderConfirmationModal";
import { sendTenantReminder, fetchTenant, type TenantReminderRequest } from "../../utils/api/tenants";
import type { UpcomingEvent } from "../../utils/tenantMetrics";
import type { EnrichedTenant } from "../../types/tenant";

interface RentData {
  lease_id: number | string;
  tenant_id?: number | null;
  tenant_name: string;
  remaining_due: number;
  monthly_rent?: number;
  status: string;
  due_date?: string | null;
  days_overdue?: number | null;
  has_portal_access?: boolean;
  tenant_email?: string | null;
}

interface InvoiceData extends Partial<PaymentDue> {
  id: number;
  tenant?: {
    full_name?: string;
    first_name?: string;
    last_name?: string;
    company_name?: string;
    tenant_type?: string;
  };
  property?: {
    name?: string;
  };
  invoice_number?: string;
  amount: number | string;
  due_date?: string;
  status?: string;
}

interface DuePanelProps {
  activeTab: string;
  onChangeTab: (tab: string) => void;
  rentLoading: boolean;
  rentData: RentData[];
  getAvatarColor?: (name: string) => string;
  getTenantInitials?: (name: string) => string;
  isLoading?: boolean;
  invoicesLoading?: boolean;
  invoicesData?: InvoiceData[];
}

const DuePanel: React.FC<DuePanelProps> = ({
  activeTab,
  onChangeTab,
  rentLoading,
  rentData,
  getAvatarColor = utilAvatarColor,
  getTenantInitials = getInitials,
  isLoading = false,
  invoicesLoading = false,
  invoicesData = [],
}) => {
  // Modal state
  const [methodModalOpen, setMethodModalOpen] = useState(false);
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [selectedRent, setSelectedRent] = useState<RentData | null>(null);
  const [sendingReminder, setSendingReminder] = useState(false);
  const [loadingTenantForEmail, setLoadingTenantForEmail] = useState(false);
  const [eventForModal, setEventForModal] = useState<UpcomingEvent | null>(null);
  const [tenantForModal, setTenantForModal] = useState<EnrichedTenant | null>(null);

  // Helper function to get tenant display name
  const getTenantName = (tenant?: InvoiceData['tenant']): string => {
    if (!tenant) return '';
    if (tenant.tenant_type === 'COMPANY') {
      return tenant.company_name || '';
    }
    return `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim() || tenant.full_name || '';
  };

  // Calculate days remaining from due date
  // Use explicit UTC parsing to avoid timezone-related off-by-one errors
  const calculateDaysRemaining = (dueDate: string | null | undefined): number | null => {
    if (!dueDate) return null;

    // Create UTC date for today (midnight UTC)
    const today = new Date();
    const todayUTC = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));

    // Parse date as UTC explicitly (format: 'YYYY-MM-DD')
    const [year, month, day] = dueDate.split('-').map(Number);
    const due = new Date(Date.UTC(year, month - 1, day));

    const diffTime = due.getTime() - todayUTC.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  // Helper function to close modals and reset all related state
  const closeAndResetModal = () => {
    setMethodModalOpen(false);
    setEmailModalOpen(false);
    setSelectedRent(null);
    setEventForModal(null);
    setTenantForModal(null);
  };

  // Handle reminder button click - show modal immediately (no API fetch needed)
  const handleReminderClick = (rent: RentData) => {
    if (!rent.tenant_id || sendingReminder) return;

    setSelectedRent(rent);

    const daysRemaining = calculateDaysRemaining(rent.due_date);
    const dueDate = rent.due_date ? new Date(rent.due_date) : new Date();
    const amount = rent.monthly_rent || rent.remaining_due;

    // Create UpcomingEvent for the modal
    const event: UpcomingEvent = {
      id: `rent-${rent.lease_id}`,
      type: 'rent',
      title: 'Rent Due',
      subtitle: `$${Number(amount).toLocaleString()} • ${daysRemaining !== null ? (daysRemaining < 0 ? `${Math.abs(daysRemaining)}d overdue` : `${daysRemaining}d remaining`) : 'Due'}`,
      date: dueDate,
      daysRemaining: daysRemaining ?? 0,
      amount: amount,
      urgency: daysRemaining !== null && daysRemaining < 0 ? 'critical' : daysRemaining !== null && daysRemaining <= 7 ? 'high' : 'medium',
      icon: 'money',
      color: daysRemaining !== null && daysRemaining < 0 ? 'text-red-600 dark:text-red-400' : 'text-blue-600 dark:text-blue-400',
      bgColor: daysRemaining !== null && daysRemaining < 0 ? 'bg-red-100 dark:bg-red-900/30' : 'bg-blue-100 dark:bg-blue-900/30',
    };

    setEventForModal(event);
    setMethodModalOpen(true);
  };

  // Handle method selection from ReminderMethodModal
  const handleMethodSelect = async (method: ReminderMethod) => {
    if (!selectedRent || !selectedRent.tenant_id || !eventForModal) return;

    setMethodModalOpen(false);

    if (method === 'portal') {
      // Send portal notification directly (no customization needed)
      setSendingReminder(true);
      try {
        const daysRemaining = calculateDaysRemaining(selectedRent.due_date);

        const reminderData: TenantReminderRequest = {
          event_type: 'rent',
          event_title: eventForModal.title,
          event_subtitle: eventForModal.subtitle,
          event_date: selectedRent.due_date || null,
          event_amount: eventForModal.amount,
          days_remaining: daysRemaining,
          delivery_method: 'portal',
        };

        const response = await sendTenantReminder(selectedRent.tenant_id, reminderData);

        if (response.success) {
          toast.success(response.message);
          closeAndResetModal();
        } else {
          toast.error('Failed to send reminder');
        }
      } catch (error: any) {
        Sentry.captureException(error, {
          tags: { component: 'DuePanel', action: 'send_portal_reminder' },
          contexts: { reminder: { tenant_id: selectedRent?.tenant_id } },
        });
        toast.error(error?.message || 'Failed to send reminder. Please try again.');
      } finally {
        setSendingReminder(false);
      }
    } else {
      // For email, we need to fetch tenant for the email modal (ReminderConfirmationModal needs full tenant)
      setLoadingTenantForEmail(true);
      try {
        const tenant = await fetchTenant(selectedRent.tenant_id);
        setTenantForModal(tenant);
        setEmailModalOpen(true);
      } catch (error: any) {
        Sentry.captureException(error, {
          tags: { component: 'DuePanel', action: 'fetch_tenant_for_email' },
          contexts: { reminder: { tenant_id: selectedRent?.tenant_id } },
        });
        toast.error('Could not load tenant details. Please try again.');
      } finally {
        setLoadingTenantForEmail(false);
      }
    }
  };

  // Handle sending reminder (called from modal)
  const handleSendReminder = async (customSubject: string | null, customMessage: string | null) => {
    if (!selectedRent || !selectedRent.tenant_id || !eventForModal) {
      return;
    }

    // TypeScript guard: tenant_id is guaranteed to be a number at this point
    const tenantId = selectedRent.tenant_id;
    if (typeof tenantId !== 'number') {
      return;
    }

    setSendingReminder(true);
    try {
      const daysRemaining = calculateDaysRemaining(selectedRent.due_date);
      const dueDate = selectedRent.due_date ? new Date(selectedRent.due_date) : null;
      
      const reminderData: TenantReminderRequest = {
        event_type: 'rent',
        event_title: eventForModal.title,
        event_subtitle: eventForModal.subtitle,
        event_date: dueDate ? dueDate.toISOString().split('T')[0] : null,
        event_amount: eventForModal.amount,
        days_remaining: daysRemaining,
        custom_subject: customSubject,
        custom_message: customMessage,
        delivery_method: 'email',
      };

      // API call with Sentry performance tracing
      const response = await Sentry.startSpan(
        {
          op: "http.client",
          name: `POST /api/tenants/${tenantId}/send-reminder`,
        },
        async () => {
          return await sendTenantReminder(tenantId, reminderData);
        }
      );

      if (response.success) {
        // Log successful reminder send with business context
        Sentry.logger.info('Reminder email sent successfully', {
          tenantId: selectedRent.tenant_id,
          eventType: eventForModal.type,
          eventAmount: eventForModal.amount,
          daysRemaining: daysRemaining,
          hasCustomMessage: !!customMessage,
        });

        toast.success(`Reminder email sent successfully`);
        closeAndResetModal();
      } else {
        toast.error('Failed to send reminder email');
      }
    } catch (error: any) {
      // Report to Sentry with context
      Sentry.captureException(error, {
        tags: {
          component: 'DuePanel',
          action: 'send_reminder',
        },
        contexts: {
          reminder: {
            tenant_id: selectedRent?.tenant_id,
            event_type: eventForModal?.type,
            event_id: eventForModal?.id,
          },
        },
      });

      toast.error(error?.message || 'Failed to send reminder email. Please try again.');
    } finally {
      setSendingReminder(false);
    }
  };

  if (isLoading) {
    return <DuePanelSkeleton />;
  }

  return (
    <div className="kpi-card h-full flex flex-col">
      <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-3">Due</h2>

      <div className="dark-divider border-b">
        <nav className="-mb-px flex space-x-6">
          <button
            className={`py-2 px-1 border-b-2 transition-colors duration-200 ${
              activeTab === "rent"
                ? "border-blue-500 dark:border-blue-400 font-medium text-sm text-blue-600 dark:text-blue-400"
                : "border-transparent font-medium text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600"
            }`}
            onClick={() => onChangeTab("rent")}
          >
            Rent
          </button>
          <button
            className={`py-2 px-1 border-b-2 transition-colors duration-200 ${
              activeTab === "invoices"
                ? "border-blue-500 dark:border-blue-400 font-medium text-sm text-blue-600 dark:text-blue-400"
                : "border-transparent font-medium text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600"
            }`}
            onClick={() => onChangeTab("invoices")}
          >
            Invoices
          </button>
        </nav>
      </div>

      <div className="mt-3 overflow-hidden flex-1">
        <div className="max-h-48 overflow-y-auto scrollbar-thin">
          <table className="w-full">
            <thead className="sticky top-0 z-10">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" style={{width: '40%'}}>
                  Tenant
                </th>
                <th className="px-3 py-2 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" style={{width: '20%'}}>
                  Amount
                </th>
                <th className="px-3 py-2 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" style={{width: '20%'}}>
                  Date
                </th>
                {activeTab === 'rent' && (
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" style={{width: '20%'}}>
                    Action
                  </th>
                )}
                {activeTab === 'invoices' && (
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" style={{width: '15%'}}>
                    Status
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {activeTab === "rent" ? (
                rentLoading ? (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-4 py-4 text-center text-sm text-gray-500 dark:text-gray-400"
                    >
                      <div className="spinner mx-auto mb-2 w-5 h-5" />
                      <p>Loading...</p>
                    </td>
                  </tr>
                ) : rentData?.length > 0 ? (
                  rentData.map((rent) => (
                    <tr key={rent.lease_id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/40">
                      <td className="px-4 py-3 whitespace-nowrap" style={{width: '40%'}}>
                        <div className="flex items-center">
                          <div
                            className={`flex-shrink-0 h-8 w-8 rounded-full ${getAvatarColor(
                              rent.tenant_name
                            )} flex items-center justify-center text-white font-medium`}
                          >
                            {getTenantInitials(rent.tenant_name)}
                          </div>
                          <div className="ml-3">
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {rent.tenant_name}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100 text-center" style={{width: '20%'}}>
                        {formatCurrency(rent.remaining_due > 0 ? rent.remaining_due : 0)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-center" style={{width: '20%'}}>
                        {rent.days_overdue && rent.days_overdue > 0 ? (
                          <span className="text-red-600 dark:text-red-400">
                            {rent.days_overdue}d overdue
                          </span>
                        ) : rent.due_date ? (
                          <span className="text-gray-900 dark:text-gray-100">
                            {new Date(rent.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </span>
                        ) : (
                          <span className="text-gray-500 dark:text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center" style={{width: '20%'}}>
                        {rent.tenant_id && (
                          <button
                            onClick={() => handleReminderClick(rent)}
                            disabled={loadingTenantForEmail || sendingReminder}
                            className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Send reminder"
                            aria-label="Send reminder email"
                          >
                            {sendingReminder ? 'Sending...' : loadingTenantForEmail ? 'Loading...' : 'Remind'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="px-4 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                      No pending payments
                    </td>
                  </tr>
                )
              ) : invoicesLoading ? (
                <tr>
                  <td colSpan={4} className="px-4 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                    <div className="spinner mx-auto mb-2 w-5 h-5" />
                    <p>Loading...</p>
                  </td>
                </tr>
              ) : invoicesData?.length > 0 ? (
                invoicesData.map((inv) => (
                  <tr key={inv.id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/40">
                    <td className="px-4 py-3 whitespace-nowrap overflow-hidden" style={{width: '40%'}}>
                      <div className="flex items-center min-w-0">
                        <div className={`flex-shrink-0 h-8 w-8 rounded-full ${getAvatarColor(getTenantName(inv.tenant) || inv.property?.name || "-")} flex items-center justify-center text-white font-medium`}>
                          {getTenantInitials(getTenantName(inv.tenant) || inv.property?.name || "-")}
                        </div>
                        <div className="ml-3 min-w-0 flex-1">
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                            {getTenantName(inv.tenant) || inv.property?.name || "Invoice"}
                          </p>
                          {inv.invoice_number && (
                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">#{inv.invoice_number}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100 text-center overflow-hidden" style={{width: '25%'}}>
                      <span className="truncate block">{formatCurrency(inv.amount)}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100 text-center overflow-hidden" style={{width: '20%'}}>
                      <span className="truncate block">{inv.due_date ? new Date(inv.due_date).toLocaleDateString() : "—"}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-center" style={{width: '15%'}}>
                      <span className={`status-pill ${
                        (inv.status || "").toLowerCase() === "overdue" ? "status-pill-overdue" : "status-pill-pending"
                      }`}>
                        {(inv.status || "Pending").toString()}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-4 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                    No pending invoices
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Reminder Method Selection Modal - rendered via portal to avoid container constraints */}
      {eventForModal && selectedRent && methodModalOpen && typeof document !== 'undefined' && createPortal(
        <ReminderMethodModal
          isOpen={methodModalOpen}
          onClose={closeAndResetModal}
          onSelect={handleMethodSelect}
          tenantName={selectedRent.tenant_name || 'Tenant'}
          hasPortalAccess={selectedRent.has_portal_access ?? false}
        />,
        document.body
      )}

      {/* Email Reminder Confirmation Modal - rendered via portal */}
      {eventForModal && tenantForModal && emailModalOpen && typeof document !== 'undefined' && createPortal(
        <ReminderConfirmationModal
          isOpen={emailModalOpen}
          onClose={closeAndResetModal}
          onConfirm={handleSendReminder}
          tenant={tenantForModal}
          event={eventForModal}
          isLoading={sendingReminder}
        />,
        document.body
      )}
    </div>
  );
};

export default DuePanel;

