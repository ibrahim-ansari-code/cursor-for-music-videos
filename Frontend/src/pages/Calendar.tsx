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
import { CalendarEvent, updateCustomReminder, deleteCustomReminder } from '../utils/api/calendar';
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

const CalendarPage: React.FC = () => {
  const navigate = useNavigate();
  const { events, loading, error, filters, updateFilters, refetch } = useCalendar();
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [reminderModalOpen, setReminderModalOpen] = useState(false);
  const [editingReminder, setEditingReminder] = useState<any>(null);

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
          // Navigate to invoice page
          if (event.metadata?.invoice_id) {
            navigate(`/accounting/invoices/${event.metadata.invoice_id}`);
          }
          break;

        case 'send_invoice':
          // Navigate to send invoice page
          if (event.metadata?.invoice_id) {
            navigate(`/accounting/invoices/${event.metadata.invoice_id}/send`);
          }
          break;

        case 'record_payment':
          // Navigate to payments page with invoice pre-selected
          if (event.metadata?.invoice_id) {
            navigate(`/accounting/payments/new?invoice_id=${event.metadata.invoice_id}`);
          }
          break;

        case 'view_lease':
          // Navigate to lease details
          if (event.metadata?.lease_id) {
            navigate(`/leases/${event.metadata.lease_id}`);
          }
          break;

        case 'view_maintenance':
          // Navigate to maintenance request
          if (event.metadata?.maintenance_id) {
            navigate(`/maintenance/${event.metadata.maintenance_id}`);
          }
          break;

        case 'complete_maintenance':
          // Mark maintenance as complete
          toast.info('Complete maintenance feature coming soon');
          break;

        case 'view_property':
          // Navigate to property page
          if (event.metadata?.property_id) {
            navigate(`/properties/${event.metadata.property_id}`);
          }
          break;

        case 'edit_reminder':
          // Open edit modal for custom reminder
          if (event.type === 'custom_reminder') {
            const reminderData = {
              id: event.metadata?.reminder_id || eventId.replace('custom_reminder_', ''),
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
          }
          break;

        case 'complete_reminder':
          // Mark reminder as complete
          if (event.type === 'custom_reminder') {
            const reminderId = event.metadata?.reminder_id || eventId.replace('custom_reminder_', '');
            await updateCustomReminder(reminderId, { is_completed: true });
            toast.success('Reminder marked as complete');
            refetch();
          }
          break;

        case 'delete_reminder':
          // Delete custom reminder
          if (event.type === 'custom_reminder') {
            if (window.confirm('Are you sure you want to delete this reminder?')) {
              const reminderId = event.metadata?.reminder_id || eventId.replace('custom_reminder_', '');
              await deleteCustomReminder(reminderId);
              toast.success('Reminder deleted');
              refetch();
            }
          }
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

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Failed to load calendar: {error.message}</p>
          <button
            onClick={refetch}
            className="mt-2 text-sm text-red-600 hover:text-red-700 underline"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Calendar</h1>
            <p className="text-xs text-gray-600 mt-0.5">
              Track all your property events in one place
            </p>
          </div>

          <div className="flex items-center space-x-3">
            {/* View Toggle */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setViewMode('list')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center space-x-2 ${
                  viewMode === 'list'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <ListIcon className="w-4 h-4" />
                <span>List</span>
              </button>
              <button
                onClick={() => setViewMode('month')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center space-x-2 ${
                  viewMode === 'month'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <CalendarIcon className="w-4 h-4" />
                <span>Month</span>
              </button>
            </div>

            {/* Filter Toggle (Mobile) */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="lg:hidden px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center space-x-2"
            >
              <FilterIcon className="w-4 h-4" />
              <span>Filters</span>
            </button>

            {/* Create Reminder Button */}
            <button
              onClick={handleCreateReminder}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
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
          } lg:block w-full lg:w-60 bg-white border-r border-gray-200 overflow-y-auto`}
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
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <>
              {viewMode === 'list' ? (
                /* List View */
                <div className="space-y-4">
                  {events.length === 0 ? (
                    <div className="text-center py-12">
                      <CalendarIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                      <p className="text-gray-500">No events found for the selected period</p>
                      <p className="text-sm text-gray-400 mt-2">
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
                <div className="bg-white rounded-lg shadow-sm p-3 h-full">
                  <BigCalendar
                    localizer={localizer}
                    events={calendarEvents}
                    startAccessor="start"
                    endAccessor="end"
                    style={{ height: '100%', minHeight: '700px' }}
                    eventPropGetter={eventStyleGetter}
                    onNavigate={handleNavigate}
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
    </div>
  );
};

export default CalendarPage;

