/**
 * Calendar Page
 * 
 * Main calendar view with:
 * - Month view (react-big-calendar)
 * - List/Agenda view
 * - Filter sidebar
 * - Create reminder button
 */

import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar as BigCalendar, dateFnsLocalizer, View } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay, parseISO } from 'date-fns';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { useCalendar } from '../hooks/useCalendar';
import { CalendarEventCard } from '../components/calendar/CalendarEventCard';
import { CalendarFilters } from '../components/calendar/CalendarFilters';
import { CreateReminderModal } from '../components/calendar/CreateReminderModal';
import NewPaymentModal from '../components/accounting/modals/NewPaymentModal';
import ViewInvoiceModal from '../components/accounting/modals/ViewInvoiceModal';
import ViewLeaseModal from '../components/leases/modals/ViewLeaseModal';
import EditMaintenanceModal from '../components/maintenance/EditMaintenanceModal';
import RescheduleMaintenanceModal from '../components/calendar/RescheduleMaintenanceModal';
import ConfirmCompleteMaintenanceModal from '../components/calendar/ConfirmCompleteMaintenanceModal';
import ConfirmCompleteReminderModal from '../components/calendar/ConfirmCompleteReminderModal';
import ConfirmDeleteReminderModal from '../components/calendar/ConfirmDeleteReminderModal';
import { EventPreviewPopover } from '../components/calendar/EventPreviewPopover';
import { NotifyVendorModal } from '../components/calendar/NotifyVendorModal';
import { CalendarEvent, updateCustomReminder, deleteCustomReminder } from '../utils/api/calendar';
import { fetchInvoice } from '../utils/api/accounting';
import { fetchLease } from '../utils/api/leases';
import { getMaintenanceRequest, updateMaintenanceRequest, notifyVendor } from '../utils/api/maintenance';
import type { Invoice } from '../types/accounting';
import type { Lease } from '../types/lease';
import { MaintenanceStatus, type MaintenanceRequest } from '../types/tenant';
import { formatDateToYYYYMMDD } from '../utils/dateHelpers';
import {
  CalendarIcon,
  ListIcon,
  PlusIcon,
  FilterIcon,
} from 'lucide-react';
import { toast } from 'react-toastify';

// Setup date-fns localizer for react-big-calendar
const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales: {},
});

type ViewMode = 'month' | 'list';

interface ReschedulingMaintenanceState {
  id: number;
  title: string;
  currentDate?: string;
}

interface CompletingMaintenanceState {
  id: number;
  title: string;
  scheduledDate?: string;
}

interface CompletingReminderState {
  id: string;
  title: string;
  reminderDate?: string;
}

interface DeletingReminderState {
  id: string;
  title: string;
  reminderDate?: string;
}

const CalendarPage: React.FC = () => {
  const navigate = useNavigate();
  const { events, loading, error, filters, updateFilters, refetch } = useCalendar();
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [reminderModalOpen, setReminderModalOpen] = useState(false);
  const [editingReminder, setEditingReminder] = useState<any>(null);
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [paymentModalData, setPaymentModalData] = useState<any>(null);
  const [viewInvoiceModalOpen, setViewInvoiceModalOpen] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [viewLeaseModalOpen, setViewLeaseModalOpen] = useState(false);
  const [selectedLease, setSelectedLease] = useState<Lease | null>(null);
  const [maintenanceModalOpen, setMaintenanceModalOpen] = useState(false);
  const [viewingMaintenanceRequest, setViewingMaintenanceRequest] = useState<MaintenanceRequest | null>(null);
  const [rescheduleModalOpen, setRescheduleModalOpen] = useState(false);
  const [reschedulingMaintenance, setReschedulingMaintenance] = useState<ReschedulingMaintenanceState | null>(null);
  const [confirmCompleteModalOpen, setConfirmCompleteModalOpen] = useState(false);
  const [completingMaintenance, setCompletingMaintenance] = useState<CompletingMaintenanceState | null>(null);
  const [isCompletingMaintenance, setIsCompletingMaintenance] = useState(false);
  const [notifyVendorModalOpen, setNotifyVendorModalOpen] = useState(false);
  const [notifyingMaintenanceRequest, setNotifyingMaintenanceRequest] = useState<MaintenanceRequest | null>(null);
  const [isNotifyingVendor, setIsNotifyingVendor] = useState(false);
  const [confirmCompleteReminderModalOpen, setConfirmCompleteReminderModalOpen] = useState(false);
  const [completingReminder, setCompletingReminder] = useState<CompletingReminderState | null>(null);
  const [isCompletingReminder, setIsCompletingReminder] = useState(false);
  const [confirmDeleteReminderModalOpen, setConfirmDeleteReminderModalOpen] = useState(false);
  const [deletingReminder, setDeletingReminder] = useState<DeletingReminderState | null>(null);
  const [isDeletingReminder, setIsDeletingReminder] = useState(false);
  
  // Event preview popover state
  const [previewEvent, setPreviewEvent] = useState<CalendarEvent | null>(null);
  const [previewPosition, setPreviewPosition] = useState<{ x: number; y: number } | null>(null);

  // Transform calendar events to react-big-calendar format
  const calendarEvents = useMemo(() => {
    return events.map((event: CalendarEvent) => ({
      id: event.id,
      title: event.title,
      start: parseISO(event.start_at),
      end: event.end_at ? parseISO(event.end_at) : parseISO(event.start_at),
      allDay: event.all_day,
      resource: event, // Store the full event data
    }));
  }, [events]);

  // Custom event style getter for color coding
  const eventStyleGetter = (event: any) => {
    const calendarEvent = event.resource as CalendarEvent;
    return {
      style: {
        backgroundColor: calendarEvent.color,
        borderColor: calendarEvent.color,
        color: '#ffffff',
      },
    };
  };

  const handleQuickAction = async (eventId: string, action: string) => {
    const event = events.find(e => e.id === eventId);
    if (!event) return;

    try {
      switch (action) {
        case 'view_invoice':
          // Fetch and display invoice in modal
          if (event.source_type !== 'invoice') {
            toast.error('This action is only available for invoice events.');
            return;
          }
          try {
            const invoiceId = parseInt(event.source_id);
            const invoice = await fetchInvoice(invoiceId);
            setSelectedInvoice(invoice);
            setViewInvoiceModalOpen(true);
          } catch (error: any) {
            console.error('Failed to load invoice:', error);
            toast.error('Failed to load invoice details');
          }
          break;

        case 'send_invoice':
          // Navigate to send invoice page
          if (event.metadata?.invoice_id) {
            navigate(`/accounting/invoices/${event.metadata.invoice_id}/send`);
          }
          break;

        case 'record_payment':
          // Open payment modal with pre-filled data from calendar event
          if (event.source_type !== 'invoice') {
            toast.error('This action is only available for invoice events.');
            return;
          }
          setPaymentModalData({
            property_id: event.property_id?.toString() || "",
            property_name: event.property_name || "",
            tenant_id: event.tenant_id?.toString() || "",
            tenant_name: event.tenant_name || "",
            invoice_id: event.source_id || null,  // Invoice ID for payment allocation
            amount: event.metadata?.amount?.toString() || "",
            payment_date: new Date().toISOString().split("T")[0],
            notes: event.metadata?.invoice_number
              ? `Payment for Invoice #${event.metadata.invoice_number}`
              : "",
          });
          setPaymentModalOpen(true);
          break;

        case 'view_lease':
          // Fetch and display lease in modal
          if (!event.source_id) {
            toast.error('Lease information not available.');
            return;
          }
          try {
            const leaseId = parseInt(event.source_id);
            const lease = await fetchLease(leaseId);
            setSelectedLease(lease);
            setViewLeaseModalOpen(true);
          } catch (error: any) {
            console.error('Failed to load lease:', error);
            toast.error('Failed to load lease details');
          }
          break;

        case 'view_maintenance':
          // Fetch and display maintenance request in modal
          if (event.source_type !== 'maintenance') {
            toast.error('This action is only available for maintenance events.');
            return;
          }
          try {
            const maintenanceId = parseInt(event.source_id);
            const maintenanceRequest = await getMaintenanceRequest(maintenanceId);
            setViewingMaintenanceRequest(maintenanceRequest);
            setMaintenanceModalOpen(true);
          } catch (error: any) {
            console.error('Failed to load maintenance request:', error);
            toast.error('Failed to load maintenance request details');
          }
          break;

        case 'mark_complete':
          // Mark maintenance as complete with secure confirmation modal
          if (event.source_type !== 'maintenance') {
            toast.error('This action is only available for maintenance events.');
            return;
          }

          setCompletingMaintenance({
            id: parseInt(event.source_id),
            title: event.title,
            scheduledDate: event.metadata?.scheduled_date || event.start_at.split('T')[0],
          });
          setConfirmCompleteModalOpen(true);
          break;

        case 'reschedule':
          // Open reschedule modal for maintenance
          if (event.source_type !== 'maintenance') {
            toast.error('This action is only available for maintenance events.');
            return;
          }

          setReschedulingMaintenance({
            id: parseInt(event.source_id),
            title: event.title,
            currentDate: event.metadata?.scheduled_date || event.start_at.split('T')[0],
          });
          setRescheduleModalOpen(true);
          break;

        case 'notify_vendor':
          // Open notify vendor modal
          if (event.source_type !== 'maintenance') {
            toast.error('This action is only available for maintenance events.');
            return;
          }
          try {
            const maintenanceId = parseInt(event.source_id);
            const maintenanceRequest = await getMaintenanceRequest(maintenanceId);
            
            if (!maintenanceRequest.vendor_id) {
              toast.error('No vendor is assigned to this maintenance request.');
              return;
            }
            
            setNotifyingMaintenanceRequest(maintenanceRequest);
            setNotifyVendorModalOpen(true);
          } catch (error: any) {
            console.error('Failed to load maintenance request:', error);
            toast.error('Failed to load maintenance request details');
          }
          break;

        case 'view_property':
          // Navigate to property page
          if (event.metadata?.property_id) {
            navigate(`/properties/${event.metadata.property_id}`);
          }
          break;

        case 'edit_reminder':
          // Open edit modal for custom reminder
          if (event.source_type !== 'custom') {
            toast.error('This action is only available for custom reminders.');
            return;
          }
          const reminderData = {
            id: event.source_id,
            title: event.title,
            description: event.description,
            reminder_date: event.start_at.split('T')[0], // Format to YYYY-MM-DD
            all_day: event.all_day,
            property_id: event.metadata?.property_id,
            unit_id: event.metadata?.unit_id,
            tenant_id: event.metadata?.tenant_id,
            notify_before_hours: event.metadata?.notify_before_hours || 24,
          };
          setEditingReminder(reminderData);
          setReminderModalOpen(true);
          break;

        case 'complete_reminder':
          // Open confirmation modal to mark reminder as complete
          if (event.source_type !== 'custom') {
            toast.error('This action is only available for custom reminders.');
            return;
          }

          setCompletingReminder({
            id: event.source_id,
            title: event.title,
            reminderDate: event.start_at.split('T')[0],
          });
          setConfirmCompleteReminderModalOpen(true);
          break;

        case 'delete_reminder':
          // Open confirmation modal to delete reminder
          if (event.source_type !== 'custom') {
            toast.error('This action is only available for custom reminders.');
            return;
          }

          setDeletingReminder({
            id: event.source_id,
            title: event.title,
            reminderDate: event.start_at.split('T')[0],
          });
          setConfirmDeleteReminderModalOpen(true);
          break;

        default:
          toast.info(`Action "${action}" not yet implemented`);
      }
    } catch (error: any) {
      console.error('Quick action error:', error);
      toast.error(error.message || 'Failed to perform action');
    }
  };

  const handleCreateReminder = () => {
    setEditingReminder(null);
    setReminderModalOpen(true);
  };

  const handleReminderSuccess = () => {
    refetch();
  };

  const handleNavigate = (date: Date, _view: View) => {
    setSelectedDate(date);
    // Update date range based on view
    // For now, keep existing date range
  };

  const handleEventClick = (calendarEvent: any, e: React.SyntheticEvent) => {
    const event = calendarEvent.resource as CalendarEvent;
    const mouseEvent = e.nativeEvent as MouseEvent;
    
    // Show preview popover at click position
    setPreviewEvent(event);
    setPreviewPosition({ x: mouseEvent.clientX, y: mouseEvent.clientY });
  };
  
  const closePreviewPopover = () => {
    setPreviewEvent(null);
    setPreviewPosition(null);
  };

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">Failed to load calendar: {error.message}</p>
          <button
            onClick={refetch}
            className="mt-2 text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 underline"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Dark mode calendar overrides */}
      <style>{`
        .dark .rbc-calendar {
          background: #1f2937;
          color: #f3f4f6;
        }
        .dark .rbc-day-bg, .dark .rbc-month-view {
          background: #374151;
          border-color: #4b5563;
        }
        .dark .rbc-header {
          color: #f3f4f6;
          border-color: #4b5563;
        }
        .dark .rbc-off-range-bg {
          background: #1f2937;
        }
        .dark .rbc-today {
          background: #1e3a5f;
        }
        .dark .rbc-show-more {
          color: #60a5fa;
          font-weight: 600;
        }
        .dark .rbc-date-cell {
          color: #9ca3af;
        }
        .dark .rbc-overlay {
          background: #1f2937;
          border-color: #4b5563;
        }
        .dark .rbc-overlay-header {
          background: #374151;
          border-color: #4b5563;
          color: #f3f4f6;
        }
      `}</style>
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Calendar</h1>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
              Track all your property events in one place
            </p>
          </div>

          <div className="flex items-center space-x-3">
            {/* View Toggle */}
            <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setViewMode('list')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center space-x-2 ${
                  viewMode === 'list'
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
                }`}
              >
                <ListIcon className="w-4 h-4" />
                <span>List</span>
              </button>
              <button
                onClick={() => setViewMode('month')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center space-x-2 ${
                  viewMode === 'month'
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
                }`}
              >
                <CalendarIcon className="w-4 h-4" />
                <span>Month</span>
              </button>
            </div>

            {/* Filter Toggle (Mobile) */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="lg:hidden px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors flex items-center space-x-2"
            >
              <FilterIcon className="w-4 h-4" />
              <span>Filters</span>
            </button>

            {/* Create Reminder Button */}
            <button
              onClick={handleCreateReminder}
              className="px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors flex items-center space-x-2"
            >
              <PlusIcon className="w-4 h-4" />
              <span>Add Reminder</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Filters Sidebar */}
        <div
          className={`${
            showFilters ? 'block' : 'hidden'
          } lg:block w-full lg:w-60 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 overflow-y-auto`}
        >
          <CalendarFilters
            filters={filters}
            onFilterChange={updateFilters}
            onClose={() => setShowFilters(false)}
          />
        </div>

        {/* Calendar View */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-gray-200 dark:border-gray-700 border-t-green-600 dark:border-t-green-400"></div>
            </div>
          ) : (
            <>
              {viewMode === 'list' ? (
                /* List View */
                <div className="space-y-4">
                  {events.length === 0 ? (
                    <div className="text-center py-12">
                      <CalendarIcon className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                      <p className="text-gray-500 dark:text-gray-400">No events found for the selected period</p>
                      <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
                        Try adjusting your filters or date range
                      </p>
                    </div>
                  ) : (
                    events.map((event) => (
                      <CalendarEventCard
                        key={event.id}
                        event={event}
                        onQuickAction={handleQuickAction}
                      />
                    ))
                  )}
                </div>
              ) : (
                /* Month View */
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-3 h-full">
                  <BigCalendar
                    localizer={localizer}
                    events={calendarEvents}
                    startAccessor="start"
                    endAccessor="end"
                    style={{ height: '100%', minHeight: '700px' }}
                    eventPropGetter={eventStyleGetter}
                    onNavigate={handleNavigate}
                    onSelectEvent={handleEventClick}
                    date={selectedDate}
                    views={['month']}
                    defaultView="month"
                    popup
                    tooltipAccessor={(event: any) => {
                      const calEvent = event.resource as CalendarEvent;
                      return calEvent.description || calEvent.title;
                    }}
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Create/Edit Reminder Modal */}
      <CreateReminderModal
        isOpen={reminderModalOpen}
        onClose={() => {
          setReminderModalOpen(false);
          setEditingReminder(null);
        }}
        onSuccess={handleReminderSuccess}
        editReminder={editingReminder}
      />

      {/* Payment Modal */}
      <NewPaymentModal
        isOpen={paymentModalOpen}
        onClose={() => {
          setPaymentModalOpen(false);
          setPaymentModalData(null);
        }}
        onSuccess={() => {
          refetch(); // Refresh calendar events
          toast.success('Payment recorded successfully');
        }}
        initialData={paymentModalData}
      />

      {/* View Invoice Modal */}
      <ViewInvoiceModal
        isOpen={viewInvoiceModalOpen}
        onClose={() => {
          setViewInvoiceModalOpen(false);
          setSelectedInvoice(null);
        }}
        invoice={selectedInvoice}
      />

      {/* View Lease Modal */}
      <ViewLeaseModal
        isOpen={viewLeaseModalOpen}
        onClose={() => {
          setViewLeaseModalOpen(false);
          setSelectedLease(null);
        }}
        lease={selectedLease}
      />

      {/* View Maintenance Request Modal */}
      {maintenanceModalOpen && viewingMaintenanceRequest && (
        <EditMaintenanceModal
          isOpen={maintenanceModalOpen}
          onClose={() => {
            setMaintenanceModalOpen(false);
            setViewingMaintenanceRequest(null);
          }}
          onSubmit={async () => {}} // No-op for view mode
          request={viewingMaintenanceRequest}
          isViewing={true}
        />
      )}

      {/* Reschedule Maintenance Modal */}
      <RescheduleMaintenanceModal
        isOpen={rescheduleModalOpen}
        onClose={() => {
          setRescheduleModalOpen(false);
          setReschedulingMaintenance(null);
        }}
        onReschedule={async (newDate: string) => {
          if (!reschedulingMaintenance) return;

          try {
            await updateMaintenanceRequest(reschedulingMaintenance.id, {
              scheduled_date: newDate,
            });
            toast.success('Maintenance rescheduled successfully');
            refetch();
            setRescheduleModalOpen(false);
            setReschedulingMaintenance(null);
          } catch (error: any) {
            console.error('Failed to reschedule maintenance:', error);
            throw error; // Let modal handle error display
          }
        }}
        currentDate={reschedulingMaintenance?.currentDate}
        maintenanceTitle={reschedulingMaintenance?.title || ''}
      />

      {/* Confirm Complete Maintenance Modal */}
      <ConfirmCompleteMaintenanceModal
        isOpen={confirmCompleteModalOpen}
        onClose={() => {
          setConfirmCompleteModalOpen(false);
          setCompletingMaintenance(null);
          setIsCompletingMaintenance(false);
        }}
        onConfirm={async () => {
          if (!completingMaintenance) return;

          setIsCompletingMaintenance(true);
          try {
            await updateMaintenanceRequest(completingMaintenance.id, {
              status: MaintenanceStatus.COMPLETED,
              completed_date: formatDateToYYYYMMDD(new Date()),
            });
            toast.success('Maintenance marked as complete');
            refetch();
          } catch (error: any) {
            console.error('Failed to complete maintenance request:', error);
            toast.error('Failed to mark maintenance as complete. Please try again.');
          } finally {
            setIsCompletingMaintenance(false);
            setConfirmCompleteModalOpen(false);
            setCompletingMaintenance(null);
          }
        }}
        maintenanceTitle={completingMaintenance?.title || ''}
        scheduledDate={completingMaintenance?.scheduledDate}
        isSubmitting={isCompletingMaintenance}
      />

      {/* Confirm Complete Reminder Modal */}
      <ConfirmCompleteReminderModal
        isOpen={confirmCompleteReminderModalOpen}
        onClose={() => {
          setConfirmCompleteReminderModalOpen(false);
          setCompletingReminder(null);
          setIsCompletingReminder(false);
        }}
        onConfirm={async () => {
          if (!completingReminder) return;

          setIsCompletingReminder(true);
          try {
            await updateCustomReminder(completingReminder.id, { is_completed: true });
            toast.success('Reminder marked as complete');
            refetch();
          } catch (error: any) {
            console.error('Failed to complete reminder:', error);
            toast.error('Failed to mark reminder as complete. Please try again.');
          } finally {
            setIsCompletingReminder(false);
            setConfirmCompleteReminderModalOpen(false);
            setCompletingReminder(null);
          }
        }}
        reminderTitle={completingReminder?.title || ''}
        reminderDate={completingReminder?.reminderDate}
        isSubmitting={isCompletingReminder}
      />

      {/* Notify Vendor Modal */}
      {notifyingMaintenanceRequest && (
        <NotifyVendorModal
          isOpen={notifyVendorModalOpen}
          onClose={() => {
            setNotifyVendorModalOpen(false);
            setNotifyingMaintenanceRequest(null);
            setIsNotifyingVendor(false);
          }}
          onConfirm={async (customMessage: string) => {
            if (!notifyingMaintenanceRequest) return;

            setIsNotifyingVendor(true);
            try {
              const result = await notifyVendor(
                notifyingMaintenanceRequest.id,
                customMessage || undefined
              );
              
              if (result.success) {
                toast.success(
                  `Notification sent successfully to ${result.vendor_email || 'vendor'}`
                );
              } else {
                toast.error(result.message || 'Failed to send notification');
              }
              
              setNotifyVendorModalOpen(false);
              setNotifyingMaintenanceRequest(null);
            } catch (error: any) {
              console.error('Failed to notify vendor:', error);
              toast.error('Failed to send vendor notification. Please try again.');
            } finally {
              setIsNotifyingVendor(false);
            }
          }}
          maintenanceRequest={notifyingMaintenanceRequest}
          isSubmitting={isNotifyingVendor}
        />
      )}

      {/* Confirm Delete Reminder Modal */}
      <ConfirmDeleteReminderModal
        isOpen={confirmDeleteReminderModalOpen}
        onClose={() => {
          setConfirmDeleteReminderModalOpen(false);
          setDeletingReminder(null);
          setIsDeletingReminder(false);
        }}
        onConfirm={async () => {
          if (!deletingReminder) return;

          setIsDeletingReminder(true);
          try {
            await deleteCustomReminder(deletingReminder.id);
            toast.success('Reminder deleted successfully');
            refetch();
          } catch (error: any) {
            console.error('Failed to delete reminder:', error);
            toast.error('Failed to delete reminder. Please try again.');
          } finally {
            setIsDeletingReminder(false);
            setConfirmDeleteReminderModalOpen(false);
            setDeletingReminder(null);
          }
        }}
        reminderTitle={deletingReminder?.title || ''}
        reminderDate={deletingReminder?.reminderDate}
        isSubmitting={isDeletingReminder}
      />

      {/* Event Preview Popover */}
      <EventPreviewPopover
        event={previewEvent}
        anchorPosition={previewPosition}
        onClose={closePreviewPopover}
        onQuickAction={handleQuickAction}
      />
    </div>
  );
};

export default CalendarPage;

