import { Property, PropertyStatus } from '../../../../types/property';

export interface StatusCounts {
  ACTIVE: number;
  INACTIVE: number;
  VACANT: number;
  total: number;
  [key: string]: number;
}

export const calculateStatusCounts = (properties: Property[]): StatusCounts => {
  return properties.reduce<StatusCounts>(
    (acc, property) => {
      acc.total++;
      const status = (property.status || PropertyStatus.ACTIVE).toUpperCase();
      acc[status] = (acc[status] || 0) + 1;
      return acc;
    },
    {
      ACTIVE: 0,
      INACTIVE: 0,
      VACANT: 0,
      total: 0,
    }
  );
};