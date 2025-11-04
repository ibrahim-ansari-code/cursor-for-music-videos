/**
 * CalendarEventCard Component
 * 
 * Displays a single calendar event in list view with:
 * - Color-coded status indicator
 * - Event details
 * - Quick action buttons
 */

import React from 'react';
import { CalendarEvent, CalendarEventStatus } from '../../utils/api/calendar';
import { format, parseISO } from 'date-fns';
import { 
  CalendarIcon, 
  MapPinIcon, 
  UserIcon, 
  AlertCircleIcon,
  CheckCircleIcon,
  ClockIcon,
} from 'lucide-react';

interface CalendarEventCardProps {
  event: CalendarEvent;
  onQuickAction?: (eventId: string, action: string) => void;
}

export const CalendarEventCard: React.FC<CalendarEventCardProps> = ({ event, onQuickAction }) => {
  const getStatusIcon = () => {
    switch (event.status) {
      case CalendarEventStatus.COMPLETED:
        return <CheckCircleIcon className="w-5 h-5 text-green-600" />;
      case CalendarEventStatus.OVERDUE:
        return <AlertCircleIcon className="w-5 h-5 text-red-600" />;
      case CalendarEventStatus.DUE:
        return <ClockIcon className="w-5 h-5 text-amber-600" />;
      default:
        return <CalendarIcon className="w-5 h-5 text-blue-600" />;
    }
  };

  const getStatusBadge = () => {
    const baseClasses = 'px-2 py-1 text-xs font-semibold rounded-full';
    
    switch (event.status) {
      case CalendarEventStatus.COMPLETED:
        return <span className={`${baseClasses} bg-green-100 text-green-800`}>Completed</span>;
      case CalendarEventStatus.OVERDUE:
        return <span className={`${baseClasses} bg-red-100 text-red-800`}>Overdue</span>;
      case CalendarEventStatus.DUE:
        return <span className={`${baseClasses} bg-amber-100 text-amber-800`}>Due Today</span>;
      default:
        return <span className={`${baseClasses} bg-blue-100 text-blue-800`}>Upcoming</span>;
    }
  };

  const formatEventDate = () => {
    const startDate = parseISO(event.start_at);
    
    if (event.all_day) {
      return format(startDate, 'MMM dd, yyyy');
    }
    
    return format(startDate, 'MMM dd, yyyy h:mm a');
  };

  return (
    <div 
      className="bg-white border-l-4 rounded-lg shadow-sm p-4 hover:shadow-md transition-shadow"
      style={{ borderLeftColor: event.color }}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start space-x-3 flex-1">
          {getStatusIcon()}
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">{event.title}</h3>
            <p className="text-sm text-gray-600 mt-1">{formatEventDate()}</p>
          </div>
        </div>
        {getStatusBadge()}
      </div>

      {/* Description */}
      {event.description && (
        <p className="text-sm text-gray-700 mb-3 ml-8">{event.description}</p>
      )}

      {/* Related Entities */}
      <div className="flex flex-wrap gap-3 ml-8 mb-3 text-sm text-gray-600">
        {event.property && (
          <div className="flex items-center space-x-1">
            <MapPinIcon className="w-4 h-4" />
            <span>{event.property.name}</span>
          </div>
        )}
        {event.tenant && (
          <div className="flex items-center space-x-1">
            <UserIcon className="w-4 h-4" />
            <span>{event.tenant.name}</span>
          </div>
        )}
      </div>

      {/* Quick Actions & Details Link */}
      {((event.quick_actions && event.quick_actions.length > 0) || event.link) && (
        <div className="flex flex-wrap gap-2 ml-8">
          {event.quick_actions && event.quick_actions.map((action) => (
            <button
              key={action}
              onClick={() => onQuickAction?.(event.id, action)}
              className="px-3 py-1 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors"
            >
              {action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </button>
          ))}
          {event.link && (
            <a
              href={event.link}
              className="px-3 py-1 text-sm font-medium text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
            >
              View Details →
            </a>
          )}
        </div>
      )}
    </div>
  );
};

