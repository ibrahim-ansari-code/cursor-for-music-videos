import { Property, PropertyStatus } from '../../../../types/property';
import { FilterOptions } from '../types.js';
import { subDays, subMonths, subYears } from 'date-fns';

export const filterProperties = (
  properties: Property[],
  statusFilter: string | null,
  searchTerm: string,
  filterOptions: FilterOptions
): Property[] => {
  if (!properties.length) return [];

  let result = [...properties];

  // Apply status filter (now consolidated into filterOptions.status)
  if (statusFilter) {
    result = result.filter(
      (p) =>
        (p.status || PropertyStatus.ACTIVE).toUpperCase() === statusFilter.toUpperCase()
    );
  }

  // Apply search term filter
  if (searchTerm.trim()) {
    const term = searchTerm.toLowerCase();
    result = result.filter(
      (p) =>
        p.name.toLowerCase().includes(term) ||
        p.address.toLowerCase().includes(term) ||
        p.city.toLowerCase().includes(term) ||
        p.property_type.toLowerCase().includes(term)
    );
  }

  // Apply property type filter
  if (filterOptions.propertyType) {
    result = result.filter(
      (p) => p.property_type === filterOptions.propertyType
    );
  }

  // Apply date filter
  if (filterOptions.dateAdded) {
    const now = new Date();
    let cutoffDate: Date;

    switch (filterOptions.dateAdded) {
      case 'last-week':
        cutoffDate = subDays(now, 7);
        break;
      case 'last-month':
        cutoffDate = subMonths(now, 1);
        break;
      case 'last-year':
        cutoffDate = subYears(now, 1);
        break;
      default:
        cutoffDate = now;
        break;
    }

    result = result.filter((p) => 
      p.created_at && new Date(p.created_at) >= cutoffDate
    );
  }

  return result;
};