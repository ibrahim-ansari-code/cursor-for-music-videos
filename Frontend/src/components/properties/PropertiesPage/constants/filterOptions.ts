export const PROPERTY_TYPES = [
  'Residential',
  'Commercial',
  'Industrial',
  'Mixed-Use',
  'Apartment Complex',
  'Land',
  'Special Purpose',
  'Other',
] as const;

export const PROPERTY_STATUSES = ['ACTIVE', 'INACTIVE', 'DRAFT', 'ARCHIVED', 'RENTED', 'VACANT', 'PARTIALLY_RENTED'] as const;

export const DATE_FILTER_OPTIONS = [
  { id: 'last-week', label: 'Last Week' },
  { id: 'last-month', label: 'Last Month' },
  { id: 'last-year', label: 'Last Year' },
] as const;

export type PropertyTypeFilter = typeof PROPERTY_TYPES[number];
export type PropertyStatusFilter = typeof PROPERTY_STATUSES[number];
export type DateFilterOption = typeof DATE_FILTER_OPTIONS[number]['id'];