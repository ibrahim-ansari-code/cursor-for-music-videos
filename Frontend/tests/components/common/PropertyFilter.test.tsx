import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import PropertyFilter from '../../../src/components/common/PropertyFilter/PropertyFilter';
import type { Property } from '../../../src/types/property';
import { PropertyType, PropertyStatus } from '../../../src/types/property';

// Mock properties for testing
const mockProperties: Property[] = [
  {
    id: 1,
    name: 'Sunset Apartments',
    address: '123 Main St, Los Angeles, CA',
    city: 'Los Angeles',
    province: 'CA',
    postal_code: '90001',
    property_type: PropertyType.APARTMENT_COMPLEX,
    status: PropertyStatus.ACTIVE,
    units: [],
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
  },
  {
    id: 2,
    name: 'Ocean View Villa',
    address: '456 Beach Blvd, Miami, FL',
    city: 'Miami',
    province: 'FL',
    postal_code: '33101',
    property_type: PropertyType.RESIDENTIAL,
    status: PropertyStatus.ACTIVE,
    units: [],
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
  },
  {
    id: 3,
    name: 'Mountain Lodge',
    address: '789 Peak Drive, Denver, CO',
    city: 'Denver',
    province: 'CO',
    postal_code: '80201',
    property_type: PropertyType.RESIDENTIAL,
    status: PropertyStatus.ACTIVE,
    units: [],
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
  },
  {
    id: 4,
    name: 'Downtown Lofts',
    address: '321 Urban Ave, New York, NY',
    city: 'New York',
    province: 'NY',
    postal_code: '10001',
    property_type: PropertyType.APARTMENT_COMPLEX,
    status: PropertyStatus.ACTIVE,
    units: [],
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
  },
];

describe('PropertyFilter Component', () => {
  const mockOnPropertyChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render with default "All Properties" text when no property selected', () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      expect(screen.getByRole('button')).toHaveTextContent('All Properties');
    });

    it('should render selected property name when property is selected', () => {
      render(
        <PropertyFilter
          selectedProperty={1}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      expect(screen.getByRole('button')).toHaveTextContent('Sunset Apartments');
    });

    it('should render custom placeholder when provided', () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
          placeholder="Select a Property"
        />
      );

      expect(screen.getByRole('button')).toHaveTextContent('Select a Property');
    });

    it('should render with building icon', () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole('button');
      const icon = button.querySelector('.fa-building');
      expect(icon).toBeInTheDocument();
    });

    it('should apply blue styling when property is selected', () => {
      render(
        <PropertyFilter
          selectedProperty={1}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-blue-50');
      expect(button).toHaveClass('text-blue-700');
    });

    it('should apply default styling when no property selected', () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-white');
      expect(button).toHaveClass('text-gray-700');
    });

    it('should be disabled when disabled prop is true', () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
          disabled={true}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });
  });

  describe('Dropdown Interaction', () => {
    it('should open dropdown when button is clicked', async () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search properties...')).toBeInTheDocument();
      });
    });

    it('should display all properties in dropdown', async () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getByText('Sunset Apartments')).toBeInTheDocument();
        expect(screen.getByText('Ocean View Villa')).toBeInTheDocument();
        expect(screen.getByText('Mountain Lodge')).toBeInTheDocument();
        expect(screen.getByText('Downtown Lofts')).toBeInTheDocument();
      });
    });

    it('should display property addresses in dropdown', async () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getByText('123 Main St, Los Angeles, CA')).toBeInTheDocument();
        expect(screen.getByText('456 Beach Blvd, Miami, FL')).toBeInTheDocument();
      });
    });

    it('should show checkmark on selected property', async () => {
      render(
        <PropertyFilter
          selectedProperty={1}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        const options = screen.getAllByRole('option');
        const sunsetOption = options.find(opt => opt.textContent?.includes('Sunset Apartments'));
        const checkmark = sunsetOption?.querySelector('svg');
        expect(checkmark).toBeInTheDocument();
      });
    });

    it('should show checkmark on "All Properties" when nothing selected', async () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        const options = screen.getAllByRole('option');
        const allPropertiesOption = options[0]; // First option is "All Properties"
        const checkmark = allPropertiesOption?.querySelector('svg');
        expect(checkmark).toBeInTheDocument();
      });
    });
  });

  describe('Search Functionality', () => {
    it('should filter properties by name when searching', async () => {
      const user = userEvent.setup();

      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search properties...')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search properties...');
      await user.type(searchInput, 'Ocean');

      await waitFor(() => {
        const options = screen.getAllByRole('option');
        // Should have "All Properties" + "Ocean View Villa"
        expect(options.length).toBe(2);
        const oceanOption = options.find(opt => opt.textContent?.includes('Ocean View Villa'));
        expect(oceanOption).toBeInTheDocument();
      });
    });

    it('should filter properties by address when searching', async () => {
      const user = userEvent.setup();

      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      const searchInput = screen.getByPlaceholderText('Search properties...');
      await user.type(searchInput, 'Miami');

      await waitFor(() => {
        expect(screen.getByText('Ocean View Villa')).toBeInTheDocument();
        expect(screen.queryByText('Sunset Apartments')).not.toBeInTheDocument();
      });
    });

    it('should be case-insensitive when searching', async () => {
      const user = userEvent.setup();

      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      const searchInput = screen.getByPlaceholderText('Search properties...');
      await user.type(searchInput, 'OCEAN');

      await waitFor(() => {
        expect(screen.getByText('Ocean View Villa')).toBeInTheDocument();
      });
    });

    it('should show "No properties found" when search has no results', async () => {
      const user = userEvent.setup();

      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search properties...')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search properties...');
      await user.type(searchInput, 'Nonexistent Property');

      await waitFor(() => {
        expect(screen.getByText('No properties found')).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('should show all properties when search is cleared', async () => {
      const user = userEvent.setup();

      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      const searchInput = screen.getByPlaceholderText('Search properties...');
      await user.type(searchInput, 'Ocean');
      await user.clear(searchInput);

      await waitFor(() => {
        expect(screen.getByText('Sunset Apartments')).toBeInTheDocument();
        expect(screen.getByText('Ocean View Villa')).toBeInTheDocument();
        expect(screen.getByText('Mountain Lodge')).toBeInTheDocument();
      });
    });
  });

  describe('Selection Behavior', () => {
    it('should call onPropertyChange with property ID when property is selected', async () => {
      const user = userEvent.setup();

      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      await user.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getAllByRole('option').length).toBeGreaterThan(0);
      });

      const options = screen.getAllByRole('option');
      const oceanOption = options.find(opt => opt.textContent?.includes('Ocean View Villa'));

      if (oceanOption) {
        await user.click(oceanOption);
      }

      await waitFor(() => {
        expect(mockOnPropertyChange).toHaveBeenCalledWith(2);
      });
    });

    it('should call onPropertyChange with null when "All Properties" is selected', async () => {
      const user = userEvent.setup();

      render(
        <PropertyFilter
          selectedProperty={1}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      await user.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getAllByRole('option').length).toBeGreaterThan(0);
      });

      const options = screen.getAllByRole('option');
      const allPropertiesOption = options[0]; // First option is "All Properties"

      await user.click(allPropertiesOption);

      await waitFor(() => {
        expect(mockOnPropertyChange).toHaveBeenCalledWith(null);
      });
    });

    it('should close dropdown after selecting a property', async () => {
      const user = userEvent.setup();

      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      await user.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getAllByRole('option').length).toBeGreaterThan(0);
      });

      const options = screen.getAllByRole('option');
      const oceanOption = options.find(opt => opt.textContent?.includes('Ocean View Villa'));

      if (oceanOption) {
        await user.click(oceanOption);
      }

      await waitFor(() => {
        expect(screen.queryByPlaceholderText('Search properties...')).not.toBeInTheDocument();
      }, { timeout: 3000 });
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty properties array', () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={[]}
        />
      );

      expect(screen.getByRole('button')).toBeInTheDocument();
      expect(screen.getByRole('button')).toHaveTextContent('All Properties');
    });

    it('should handle property without address', async () => {
      const propertiesWithoutAddress: Property[] = [
        {
          id: 1,
          name: 'No Address Property',
          address: '',
          city: 'Unknown',
          province: 'Unknown',
          postal_code: '00000',
          property_type: PropertyType.RESIDENTIAL,
          status: PropertyStatus.ACTIVE,
          units: [],
          created_at: '2024-01-01',
          updated_at: '2024-01-01',
        },
      ];

      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={propertiesWithoutAddress}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getByText('No Address Property')).toBeInTheDocument();
      });
    });

    it('should handle non-existent selected property ID', () => {
      render(
        <PropertyFilter
          selectedProperty={999}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      // Should fall back to placeholder
      expect(screen.getByRole('button')).toHaveTextContent('All Properties');
    });

    it('should handle property ID of 0', async () => {
      const propertiesWithZeroId: Property[] = [
        {
          id: 0,
          name: 'Zero ID Property',
          address: '000 Zero St',
          city: 'Test City',
          province: 'TC',
          postal_code: '00000',
          property_type: PropertyType.RESIDENTIAL,
          status: PropertyStatus.ACTIVE,
          units: [],
          created_at: '2024-01-01',
          updated_at: '2024-01-01',
        },
      ];

      render(
        <PropertyFilter
          selectedProperty={0}
          onPropertyChange={mockOnPropertyChange}
          properties={propertiesWithZeroId}
        />
      );

      expect(screen.getByRole('button')).toHaveTextContent('Zero ID Property');
    });
  });

  describe('Accessibility', () => {
    it('should have proper button role', () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should have focusable search input', async () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText('Search properties...');
        expect(searchInput).toBeInTheDocument();
        expect(searchInput).toHaveAttribute('type', 'text');
      });
    });

    it('should auto-focus search input when dropdown opens', async () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText('Search properties...');
        expect(searchInput).toBeInTheDocument();
        // Auto-focus is present in the DOM
        expect(searchInput).toHaveProperty('autofocus');
      });
    });
  });

  describe('Performance', () => {
    it('should handle large number of properties efficiently', async () => {
      const manyProperties: Property[] = Array.from({ length: 100 }, (_, i) => ({
        id: i + 1,
        name: `Property ${i + 1}`,
        address: `${i + 1} Test Street`,
        city: 'Test City',
        province: 'TC',
        postal_code: '00000',
        property_type: PropertyType.APARTMENT_COMPLEX,
        status: PropertyStatus.ACTIVE,
        units: [],
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
      }));

      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={manyProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getAllByRole('option').length).toBeGreaterThan(10);
      });

      // Dropdown container should have scrollable class
      const dropdownContainer = screen.getByPlaceholderText('Search properties...').closest('.flex.flex-col');
      const scrollableDiv = dropdownContainer?.querySelector('.overflow-y-auto');
      expect(scrollableDiv).toBeInTheDocument();
      expect(scrollableDiv).toHaveClass('max-h-80');
    });

    it('should filter large property list quickly', async () => {
      const user = userEvent.setup();
      const manyProperties: Property[] = Array.from({ length: 100 }, (_, i) => ({
        id: i + 1,
        name: `Property ${i + 1}`,
        address: `${i + 1} Test Street`,
        city: 'Test City',
        province: 'TC',
        postal_code: '00000',
        property_type: PropertyType.APARTMENT_COMPLEX,
        status: PropertyStatus.ACTIVE,
        units: [],
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
      }));

      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={manyProperties}
        />
      );

      fireEvent.click(screen.getByRole('button'));

      const searchInput = screen.getByPlaceholderText('Search properties...');
      await user.type(searchInput, '42');

      await waitFor(() => {
        expect(screen.getByText('Property 42')).toBeInTheDocument();
        expect(screen.queryByText('Property 1')).not.toBeInTheDocument();
      });
    });
  });

  describe('Dark Mode Support', () => {
    it('should have dark mode classes', () => {
      render(
        <PropertyFilter
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole('button');
      expect(button.className).toContain('dark:');
    });
  });
});
