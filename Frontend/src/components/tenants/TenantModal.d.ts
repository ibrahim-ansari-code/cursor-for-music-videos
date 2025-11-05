import React from 'react';
import type { EnrichedTenant } from '../../types/tenant';

export interface TenantModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (tenant: EnrichedTenant) => void;
  source: string;
  tenant?: Partial<EnrichedTenant>;
  propertyId?: number | null;
  unitId?: number | null;
  unitName?: string;
}

declare const TenantModal: React.FC<TenantModalProps>;
export default TenantModal;

