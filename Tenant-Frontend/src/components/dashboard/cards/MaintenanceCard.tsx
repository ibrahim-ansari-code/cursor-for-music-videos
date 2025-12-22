import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FaWrench } from 'react-icons/fa';
import { InfoCard, type CardStatus } from '@/components/ui/InfoCard';
import { formatDateForDisplay } from '@/utils/dateHelpers';
import type { MaintenanceCardProps } from '../types';

/**
 * MaintenanceCard Component
 * Displays open maintenance requests count with status indicator
 */
const MaintenanceCard: React.FC<MaintenanceCardProps> = ({ data }) => {
  const navigate = useNavigate();

  const getStatus = (): CardStatus | undefined => {
    if (data && data.open_requests > 0) return 'active';
    return undefined;
  };

  const getValue = (): string => {
    if (data && typeof data.open_requests === 'number') {
      if (data.open_requests === 0) return 'No open requests';
      return `${data.open_requests} open`;
    }
    return 'No data';
  };

  const getSubtitle = () => {
    if (!data?.last_updated) {
      return 'No recent activity';
    }

    return (
      <div className="text-gray-700">
        Last updated: {formatDateForDisplay(data.last_updated)}
      </div>
    );
  };

  return (
    <InfoCard
      title="Maintenance Requests"
      value={getValue()}
      subtitle={getSubtitle()}
      icon={{ component: FaWrench }}
      status={getStatus()}
      action={{
        label: 'View All Requests',
        onClick: () => navigate('/maintenance'),
      }}
    />
  );
};

export default MaintenanceCard;
