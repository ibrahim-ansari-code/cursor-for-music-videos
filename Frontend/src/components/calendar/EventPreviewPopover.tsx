/**
 * EventPreviewPopover Component
 *
 * A lightweight popover that appears when clicking calendar events.
 * Shows event details and quick actions without opening a full modal.
 *
 * Industry standard pattern used by Google Calendar, Outlook, etc.
 */

import React, { useRef, useEffect, useLayoutEffect, useState, useMemo } from "react";
import { createPortal } from "react-dom";
import { format, parseISO } from "date-fns";
import {
  CalendarIcon,
  MapPinIcon,
  UserIcon,
  XIcon,
  ClockIcon,
  AlertCircleIcon,
  CheckCircleIcon,
  WrenchIcon,
  FileTextIcon,
  HomeIcon,
  BellIcon,
  DollarSignIcon,
} from "lucide-react";
import { CalendarEvent, CalendarEventStatus } from "../../utils/api/calendar";

interface EventPreviewPopoverProps {
  event: CalendarEvent | null;
  anchorPosition: { x: number; y: number } | null;
  onClose: () => void;
  onQuickAction: (eventId: string, action: string) => void;
}

export const EventPreviewPopover: React.FC<EventPreviewPopoverProps> = ({
  event,
  anchorPosition,
  onClose,
  onQuickAction,
}) => {
  const popoverRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  // Calculate position to keep popover in viewport
  // Use useLayoutEffect to prevent visible repositioning flash
  useLayoutEffect(() => {
    if (!anchorPosition || !popoverRef.current) return;

    const popover = popoverRef.current;
    const popoverRect = popover.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let top = anchorPosition.y + 8;
    let left = anchorPosition.x;

    // Adjust if popover would overflow right edge
    if (left + popoverRect.width > viewportWidth - 16) {
      left = viewportWidth - popoverRect.width - 16;
    }

    // Adjust if popover would overflow bottom edge
    if (top + popoverRect.height > viewportHeight - 16) {
      top = anchorPosition.y - popoverRect.height - 8;
    }

    // Ensure minimum left position
    if (left < 16) left = 16;

    setPosition({ top, left });
  }, [anchorPosition]);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node)
      ) {
        onClose();
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [onClose]);

  // Memoize action labels config to avoid recreating on each render
  const actionLabels: Record<string, { label: string; primary?: boolean }> = useMemo(() => ({
    view_invoice: { label: "View Invoice", primary: true },
    record_payment: { label: "Record Payment", primary: true },
    send_invoice: { label: "Send Invoice" },
    view_lease: { label: "View Lease", primary: true },
    start_renewal: { label: "Start Renewal", primary: true },
    generate_notice: { label: "Generate Notice" },
    view_maintenance: { label: "View Details", primary: true },
    mark_complete: { label: "Mark Complete", primary: true },
    reschedule: { label: "Reschedule" },
    notify_vendor: { label: "Notify Vendor" },
    view_property: { label: "View Property" },
    edit_reminder: { label: "Edit" },
    complete_reminder: { label: "Mark Done", primary: true },
    delete_reminder: { label: "Delete" },
  }), []);

  // Memoize sorted quick actions to avoid recalculation on each render
  const displayActions = useMemo(() => {
    if (!event?.quick_actions || event.quick_actions.length === 0) return [];

    // Sort by primary status and take top 3
    return [...event.quick_actions]
      .sort((a, b) => {
        const aIsPrimary = actionLabels[a]?.primary ? 1 : 0;
        const bIsPrimary = actionLabels[b]?.primary ? 1 : 0;
        return bIsPrimary - aIsPrimary;
      })
      .slice(0, 3);
  }, [event?.quick_actions, actionLabels]);

  if (!event || !anchorPosition) return null;

  const getEventTypeIcon = () => {
    switch (event.type) {
      case "invoice_due":
        return <DollarSignIcon className="w-5 h-5" />;
      case "lease_start":
      case "lease_expiring":
        return <FileTextIcon className="w-5 h-5" />;
      case "maintenance_scheduled":
        return <WrenchIcon className="w-5 h-5" />;
      case "insurance_expiry":
      case "mortgage_renewal":
        return <HomeIcon className="w-5 h-5" />;
      case "custom_reminder":
        return <BellIcon className="w-5 h-5" />;
      default:
        return <CalendarIcon className="w-5 h-5" />;
    }
  };

  const getStatusBadge = () => {
    const baseClasses = "px-2 py-0.5 text-xs font-medium rounded-full";

    switch (event.status) {
      case CalendarEventStatus.COMPLETED:
        return (
          <span
            className={`${baseClasses} bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300`}
          >
            <CheckCircleIcon className="w-3 h-3 inline mr-1" />
            Completed
          </span>
        );
      case CalendarEventStatus.OVERDUE:
        return (
          <span
            className={`${baseClasses} bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300`}
          >
            <AlertCircleIcon className="w-3 h-3 inline mr-1" />
            Overdue
          </span>
        );
      case CalendarEventStatus.DUE:
        return (
          <span
            className={`${baseClasses} bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300`}
          >
            <ClockIcon className="w-3 h-3 inline mr-1" />
            Due Today
          </span>
        );
      default:
        return (
          <span
            className={`${baseClasses} bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300`}
          >
            <CalendarIcon className="w-3 h-3 inline mr-1" />
            Upcoming
          </span>
        );
    }
  };

  const formatEventDate = () => {
    const startDate = parseISO(event.start_at);

    if (event.all_day) {
      return format(startDate, "EEEE, MMMM d, yyyy");
    }

    return format(startDate, "EEEE, MMMM d, yyyy 'at' h:mm a");
  };

  const getEventTypeLabel = () => {
    switch (event.type) {
      case "invoice_due":
        return "Invoice Due";
      case "lease_start":
        return "Lease Start";
      case "lease_expiring":
        return "Lease Expiring";
      case "maintenance_scheduled":
        return "Maintenance";
      case "insurance_expiry":
        return "Insurance Expiry";
      case "mortgage_renewal":
        return "Mortgage Renewal";
      case "custom_reminder":
        return "Reminder";
      default:
        return "Event";
    }
  };

  const getQuickActionButtons = () => {
    if (displayActions.length === 0) return null;

    return (
      <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
        {displayActions.map((action) => {
          const config = actionLabels[action];
          if (!config) return null;

          return (
            <button
              key={action}
              onClick={() => {
                onQuickAction(event.id, action);
                onClose();
              }}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                config.primary
                  ? "bg-blue-600 hover:bg-blue-700 text-white"
                  : "bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300"
              }`}
            >
              {config.label}
            </button>
          );
        })}
      </div>
    );
  };

  const popoverContent = (
    <div
      ref={popoverRef}
      className="fixed z-[9999] w-80 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden transition-all duration-150 ease-out"
      style={{
        top: position.top,
        left: position.left,
      }}
    >
      {/* Color bar at top */}
      <div className="h-1.5" style={{ backgroundColor: event.color }} />

      {/* Header */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div
              className="p-2 rounded-lg flex-shrink-0"
              style={{ backgroundColor: `${event.color}20` }}
            >
              <div style={{ color: event.color }}>{getEventTypeIcon()}</div>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                {getEventTypeLabel()}
              </p>
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 leading-tight">
                {event.title}
              </h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors flex-shrink-0"
          >
            <XIcon className="w-4 h-4" />
          </button>
        </div>

        {/* Status badge */}
        <div className="mt-3">{getStatusBadge()}</div>
      </div>

      {/* Details */}
      <div className="px-4 pb-4 space-y-2.5">
        {/* Date/Time */}
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <ClockIcon className="w-4 h-4 flex-shrink-0" />
          <span>{formatEventDate()}</span>
        </div>

        {/* Property */}
        {event.property_name && (
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <MapPinIcon className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{event.property_name}</span>
          </div>
        )}

        {/* Tenant */}
        {event.tenant_name && (
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <UserIcon className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{event.tenant_name}</span>
          </div>
        )}

        {/* Amount (for invoices) */}
        {event.metadata?.amount && (
          <div className="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-gray-100">
            <DollarSignIcon className="w-4 h-4 flex-shrink-0 text-gray-400" />
            <span>
              {new Intl.NumberFormat("en-CA", {
                style: "currency",
                currency: "CAD",
              }).format(event.metadata.amount)}
            </span>
          </div>
        )}

        {/* Description */}
        {event.description && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 line-clamp-2">
            {event.description}
          </p>
        )}

        {/* Quick Actions */}
        {getQuickActionButtons()}
      </div>
    </div>
  );

  return createPortal(popoverContent, document.body);
};

export default EventPreviewPopover;

