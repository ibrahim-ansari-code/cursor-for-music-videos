import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FaCreditCard } from 'react-icons/fa';
import { InfoCard } from '@/components/ui/InfoCard';
import { formatDateForDisplay } from '@/utils/dateHelpers';
import type { MonthlyRentCardProps } from '../types';

const MonthlyRentCard: React.FC<MonthlyRentCardProps> = ({ data }) => {
  const navigate = useNavigate();

  const getValue = () => {
    if (data?.has_active_lease && Number(data.amount) > 0) {
      return `$${Number(data.amount).toLocaleString()}`;
    }
    return 'Not set';
  };

  const getSubtitle = () => {
    if (!data?.has_active_lease) return 'No active lease found';

    return (
      <div>
        <div className="text-gray-700 line-clamp-2">
          {data.rent_due_day > 0
            ? `Rent due on day ${data.rent_due_day} of each month`
            : 'Based on your active lease'}
        </div>
        {data.last_payment_date && (
          <div className="mt-1 text-xs text-gray-500 shrink-0 line-clamp-1">
            Last payment: {formatDateForDisplay(data.last_payment_date)}
          </div>
        )}
      </div>
    );
  };

  return (
    <InfoCard
      title="Monthly Rent"
      value={getValue()}
      subtitle={getSubtitle()}
      icon={{ component: FaCreditCard }}
      action={{
        label: 'Pay Now',
        onClick: () => navigate('/payments'),
        align: 'right',
        variant: 'link',
      }}
    />
  );
};

export default MonthlyRentCard;
