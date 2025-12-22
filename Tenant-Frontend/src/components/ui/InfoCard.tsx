import React from 'react';
import { FaChevronRight } from 'react-icons/fa';
import type { IconType } from 'react-icons';

export type CardStatus = 'active' | 'warning' | 'paid' | 'overdue' | 'unpaid';

export interface InfoCardProps {
  title: string;
  value: string;
  subtitle?: React.ReactNode;
  icon?: {
    component: IconType;
  };
  status?: CardStatus;
  action?: {
    label: string;
    onClick: () => void;
    align?: 'left' | 'right';
    variant?: 'link' | 'teal';
  };
  headerAction?: {
    label: string;
    onClick: () => void;
    variant?: 'button' | 'link';
  };
}

/**
 * InfoCard Component
 * Reusable card component for displaying dashboard metrics
 * Supports status pills, header actions, and bottom action links
 */
export const InfoCard: React.FC<InfoCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  status,
  action,
  headerAction
}) => {
  // Get icon background color based on status (default to brand teal)
  const getIconBgColor = (): string => {
    if (!status) return 'bg-brand-teal/10';
    switch (status) {
      case 'active':
        return 'bg-green-100';
      case 'warning':
      case 'unpaid':
        return 'bg-yellow-100';
      case 'paid':
        return 'bg-green-100';
      case 'overdue':
        return 'bg-red-100';
      default:
        return 'bg-brand-teal/10';
    }
  };

  // Get icon text color based on status (default to brand teal)
  const getIconTextColor = (): string => {
    if (!status) return 'text-brand-teal';
    switch (status) {
      case 'active':
        return 'text-green-600';
      case 'warning':
      case 'unpaid':
        return 'text-yellow-600';
      case 'paid':
        return 'text-green-600';
      case 'overdue':
        return 'text-red-600';
      default:
        return 'text-brand-teal';
    }
  };

  // Get status pill styles
  const getStatusStyles = (s: CardStatus): string => {
    switch (s) {
      case 'paid':
        return 'bg-green-100 text-green-700';
      case 'overdue':
        return 'bg-red-100 text-red-700';
      case 'unpaid':
        return 'bg-yellow-100 text-yellow-700';
      case 'warning':
        return 'bg-yellow-100 text-yellow-700';
      case 'active':
      default:
        return 'bg-blue-100 text-blue-700';
    }
  };

  const getStatusLabel = (s: CardStatus): string => {
    switch (s) {
      case 'paid':
        return 'Paid';
      case 'overdue':
        return 'Overdue';
      case 'unpaid':
        return 'Unpaid';
      case 'warning':
        return 'Warning';
      case 'active':
      default:
        return 'Active';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow min-h-[180px] flex flex-col">
      {/* Header row: Title + Status/HeaderAction/Icon */}
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-gray-600">{title}</p>

        <div className="flex items-center gap-2 shrink-0">
          {/* Status pill - inline with icon */}
          {status && (
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${getStatusStyles(status)}`}
            >
              {getStatusLabel(status)}
            </span>
          )}

          {/* Header action - supports button (default) or link variant */}
          {headerAction && (
            <button
              onClick={headerAction.onClick}
              className={
                headerAction.variant === 'link'
                  ? 'text-sm font-medium text-gray-900 hover:text-gray-600 cursor-pointer transition-colors'
                  : 'px-3 py-1.5 rounded-lg bg-brand-teal text-white text-xs font-semibold hover:bg-brand-green cursor-pointer transition-colors'
              }
            >
              {headerAction.label}
            </button>
          )}

          {/* Icon with status-based coloring */}
          {icon && (
            <div className={`p-2.5 rounded-lg ${getIconBgColor()}`}>
              <icon.component className={`text-base ${getIconTextColor()}`} />
            </div>
          )}
        </div>
      </div>

      {/* Value */}
      <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>

      {/* Subtitle */}
      {subtitle && (
        <div className="mt-1 text-sm text-gray-500 grow">{subtitle}</div>
      )}

      {/* Bottom action - pushed to bottom */}
      {action && (
        <button
          onClick={action.onClick}
          className={`mt-auto pt-3 text-sm font-medium cursor-pointer transition-colors flex items-center ${
            action.align === 'right' ? 'ml-auto' : ''
          } ${
            action.variant === 'link'
              ? 'text-gray-900 hover:text-gray-600'
              : 'text-gray-900 hover:text-gray-700'
          }`}
        >
          {action.label}
          <FaChevronRight className="ml-1" />
        </button>
      )}
    </div>
  );
};

export default InfoCard;
