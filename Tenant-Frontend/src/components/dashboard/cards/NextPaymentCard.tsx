import React from 'react';
import { FaCalendar, FaSync } from 'react-icons/fa';
import { InfoCard, type CardStatus } from '@/components/ui/InfoCard';
import { formatDateForDisplay } from '@/utils/dateHelpers';
import type { NextPaymentCardProps } from '../types';

const NextPaymentCard: React.FC<NextPaymentCardProps> = ({ data }) => {

  const getStatus = (): CardStatus | undefined => {
    if (!data?.due_date) return undefined;
    if (data.is_overdue) return 'overdue';
    if (data.is_paid || data.current_balance === '0.00') return 'paid';
    return 'unpaid';
  };

  const getValue = () => {
    if (data?.current_balance && data.current_balance !== '0.00') {
      return `$${Number(data.current_balance).toLocaleString()}`;
    }
    return 'No balance due';
  };

  const getDaysText = () => {
    if (data.is_paid || data.current_balance === '0.00') return 'All caught up!';
    if (data.days_remaining === 0) return 'Due today';
    if (data.is_overdue) {
      const days = Math.abs(data.days_remaining);
      return `Overdue by ${days} day${days === 1 ? '' : 's'}`;
    }
    return `Due in ${data.days_remaining} day${data.days_remaining === 1 ? '' : 's'}`;
  };

  const getSubtitle = () => {
    if (!data?.due_date) return 'No upcoming payment';

    return (
      <div>
        <div className="text-gray-700 line-clamp-1">
          {data.is_paid ? 'Paid in full' : `Due on ${formatDateForDisplay(data.due_date)}`}
        </div>
        <div className={`mt-1 text-xs shrink-0 line-clamp-1 ${data.is_overdue ? 'text-red-600' : 'text-gray-500'}`}>
          {getDaysText()}
        </div>
        {data.has_autopay && (
          <div className="mt-1 flex items-center gap-1 text-xs text-gray-600">
            <FaSync className="w-3 h-3" />
            <span>Autopay {data.next_autopay_date ? `on ${formatDateForDisplay(data.next_autopay_date)}` : 'enabled'}</span>
          </div>
        )}
      </div>
    );
  };

  return (
    <InfoCard
      title="Current Balance"
      value={getValue()}
      subtitle={getSubtitle()}
      icon={{ component: FaCalendar }}
      status={getStatus()}
    />
  );
};

export default NextPaymentCard;
