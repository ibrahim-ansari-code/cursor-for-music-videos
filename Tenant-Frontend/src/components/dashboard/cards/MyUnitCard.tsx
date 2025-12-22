import React from 'react';
import { FaHome } from 'react-icons/fa';
import { InfoCard } from '@/components/ui/InfoCard';
import { formatDateForDisplay } from '@/utils/dateHelpers';
import type { MyUnitCardProps } from '../types';

const MyUnitCard: React.FC<MyUnitCardProps> = ({ data }) => {
  return (
    <InfoCard
      title="My Unit"
      value={data.unit_name || 'No unit assigned'}
      subtitle={
        <div>
          <div className="text-gray-700 line-clamp-2" title={data.full_address}>
            {data.full_address}
          </div>
          <div className="mt-1 text-xs text-gray-500 shrink-0 line-clamp-1">
            Lease: {formatDateForDisplay(data.lease_start)} – {formatDateForDisplay(data.lease_end)}
          </div>
        </div>
      }
      icon={{ component: FaHome }}
    />
  );
};

export default MyUnitCard;
