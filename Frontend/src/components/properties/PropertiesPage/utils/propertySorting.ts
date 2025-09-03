import { Property, PropertyStatus } from '../../../../types/property';

export const sortProperties = (properties: Property[], sortOption: string | null): Property[] => {
  if (!sortOption) return properties;

  const result = [...properties];

  result.sort((a, b) => {
    switch (sortOption) {
      case 'name-asc':
        return a.name.localeCompare(b.name);
      case 'name-desc':
        return b.name.localeCompare(a.name);
      case 'type-asc':
        return a.property_type.localeCompare(b.property_type);
      case 'type-desc':
        return b.property_type.localeCompare(a.property_type);
      case 'status-asc':
        return (a.status || PropertyStatus.ACTIVE)
          .toUpperCase()
          .localeCompare((b.status || PropertyStatus.ACTIVE).toUpperCase());
      case 'status-desc':
        return (b.status || PropertyStatus.ACTIVE)
          .toUpperCase()
          .localeCompare((a.status || PropertyStatus.ACTIVE).toUpperCase());
      case 'date-asc':
        return (a.created_at ? new Date(a.created_at).getTime() : 0) - 
               (b.created_at ? new Date(b.created_at).getTime() : 0);
      case 'date-desc':
        return (b.created_at ? new Date(b.created_at).getTime() : 0) - 
               (a.created_at ? new Date(a.created_at).getTime() : 0);
      default:
        return 0;
    }
  });

  return result;
};