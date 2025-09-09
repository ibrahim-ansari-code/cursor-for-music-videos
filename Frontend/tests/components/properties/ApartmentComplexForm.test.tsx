import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { FormProvider, useForm } from 'react-hook-form';
import ApartmentComplexForm from '../../../src/components/properties/NewPropertyModal/steps/DetailsStep/typeSpecificForms/ApartmentComplexForm';
import { PropertyFormData } from '../../../src/types/property';

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <div>{children}</div>,
}));

const TestWrapper: React.FC<{ children: React.ReactNode; defaultValues?: any }> = ({ 
  children, 
  defaultValues = {} 
}) => {
  const methods = useForm<PropertyFormData>({
    defaultValues: {
      type_specific_details: {
        complex_style: undefined,
        number_of_buildings: 0,
        total_units: 0,
        unit_mix: {},
        parking_spaces_total: 0,
        elevator_count: 0,
        floor_count: undefined,
        floor_count_custom: undefined,
        elevator_count_custom: undefined,
        shared_amenities: [],
        ...defaultValues
      }
    }
  });

  return (
    <FormProvider {...methods}>
      {children}
    </FormProvider>
  );
};

describe('ApartmentComplexForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Form Rendering', () => {
    it('renders without crashing', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      expect(screen.getByRole('form', { name: /Apartment Complex Details/i })).toBeInTheDocument();
    });

    it('renders complex style selection buttons', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      // Check all complex style options are present (they use radio role)
      expect(screen.getByRole('radio', { name: /Garden Style/i })).toBeInTheDocument();
      expect(screen.getByRole('radio', { name: /High-Rise/i })).toBeInTheDocument();
      expect(screen.getByRole('radio', { name: /Mid-Rise/i })).toBeInTheDocument();
      expect(screen.getByRole('radio', { name: /Townhome/i })).toBeInTheDocument();
      expect(screen.getByRole('radio', { name: /Luxury/i })).toBeInTheDocument();
      expect(screen.getByRole('radio', { name: /Student Housing/i })).toBeInTheDocument();
    });

    it('renders essential form fields', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      // Check for input fields by placeholder since they don't use traditional labels
      expect(screen.getByPlaceholderText('3')).toBeInTheDocument(); // Buildings
      expect(screen.getByPlaceholderText('120')).toBeInTheDocument(); // Total Units
      expect(screen.getByPlaceholderText('180')).toBeInTheDocument(); // Parking Spaces
    });
  });

  describe('Complex Style Selection', () => {
    it('allows selecting complex style without errors', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      const gardenStyleButton = screen.getByRole('radio', { name: /Garden Style/i });
      
      // This should not throw any errors (testing the original issue)
      expect(() => {
        fireEvent.click(gardenStyleButton);
      }).not.toThrow();
      
      // Button should show selected state
      expect(gardenStyleButton).toHaveClass('border-purple-500');
    });

    it('can select different complex styles', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      const gardenStyleButton = screen.getByRole('radio', { name: /Garden Style/i });
      const luxuryButton = screen.getByRole('radio', { name: /Luxury/i });
      
      // Select garden style first
      fireEvent.click(gardenStyleButton);
      expect(gardenStyleButton).toHaveClass('border-purple-500');
      expect(luxuryButton).not.toHaveClass('border-purple-500');
      
      // Switch to luxury style
      fireEvent.click(luxuryButton);
      expect(luxuryButton).toHaveClass('border-purple-500');
      expect(gardenStyleButton).not.toHaveClass('border-purple-500');
    });
  });

  describe('Floor Count Selection - Original Issue Fix', () => {
    it('floor count buttons work on first click (not double-click)', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      // Find floor buttons within the floor count section specifically
      const floorSection = screen.getByRole('group', { name: /floor count selection/i });
      const floorButtons = within(floorSection).getAllByRole('button');
      const floorButton1 = floorButtons[0]; // First button (1)
      const floorButton2 = floorButtons[1]; // Second button (2)
      
      // Single click should work immediately
      fireEvent.click(floorButton1);
      expect(floorButton1).toHaveClass('from-purple-500');
      
      // Switch to another button with single click
      fireEvent.click(floorButton2);
      expect(floorButton2).toHaveClass('from-purple-500');
      expect(floorButton1).not.toHaveClass('from-purple-500');
    });

    it('custom floor count input works immediately', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      const customInput = screen.getByPlaceholderText('4+');
      
      // Should not cause any errors when typing
      expect(() => {
        fireEvent.change(customInput, { target: { value: '10' } });
      }).not.toThrow();
    });
  });

  describe('Elevator Count Selection - Original Issue Fix', () => {
    it('elevator count buttons work on first click', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      // Use the elevator count section specifically
      const elevatorSection = screen.getByRole('group', { name: /elevator count selection/i });
      const elevatorButtons = elevatorSection.querySelectorAll('button');
      const elevatorButton0 = elevatorButtons[0]; // First button (0)
      const elevatorButton2 = elevatorButtons[2]; // Third button (2)
      
      // Single click should work immediately
      fireEvent.click(elevatorButton0);
      expect(elevatorButton0).toHaveClass('from-indigo-500');
      
      // Switch to another button with single click
      fireEvent.click(elevatorButton2);
      expect(elevatorButton2).toHaveClass('from-indigo-500');
      expect(elevatorButton0).not.toHaveClass('from-indigo-500');
    });

    it('custom elevator count input works immediately', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      const customInput = screen.getByPlaceholderText('5+');
      
      // Should not cause any errors when typing
      expect(() => {
        fireEvent.change(customInput, { target: { value: '8' } });
      }).not.toThrow();
    });
  });

  describe('Unit Mix Validation', () => {
    it('shows unit mix validation feedback', async () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      // Set total units using placeholder
      const totalUnitsInput = screen.getByPlaceholderText('120');
      fireEvent.change(totalUnitsInput, { target: { value: '100' } });
      
      // Check that validation feedback appears (more flexible pattern)
      await waitFor(() => {
        expect(screen.getByText(/0\s*\/\s*100\s*units/)).toBeInTheDocument();
      });
    });
  });

  describe('Form Integration', () => {
    it('integrates with React Hook Form properly', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      // Test form field registration works using placeholders
      const buildingsInput = screen.getByPlaceholderText('3');
      const unitsInput = screen.getByPlaceholderText('120');
      
      expect(buildingsInput).toBeInTheDocument();
      expect(unitsInput).toBeInTheDocument();
      
      // Should be able to input values without errors
      expect(() => {
        fireEvent.change(buildingsInput, { target: { value: '5' } });
        fireEvent.change(unitsInput, { target: { value: '200' } });
      }).not.toThrow();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      // Form should have proper role
      expect(screen.getByRole('form')).toBeInTheDocument();
      
      // Complex style buttons should have radio role
      const styleButtons = screen.getAllByRole('radio');
      expect(styleButtons.length).toBeGreaterThan(0);
      
      // Floor and elevator buttons should have proper group roles
      expect(screen.getByRole('group', { name: /floor count selection/i })).toBeInTheDocument();
      expect(screen.getByRole('group', { name: /elevator count selection/i })).toBeInTheDocument();
    });
  });

  describe('Edge Cases - Bulletproof Testing', () => {
    it('handles undefined values gracefully', () => {
      render(
        <TestWrapper defaultValues={{
          complex_style: undefined,
          floor_count_custom: undefined,
          elevator_count_custom: undefined,
        }}>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      // Should render without crashing with undefined values
      expect(screen.getByRole('form')).toBeInTheDocument();
    });

    it('handles empty values gracefully', () => {
      render(
        <TestWrapper defaultValues={{
          complex_style: '',
          number_of_buildings: 0,
          total_units: 0,
        }}>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      // Should render without crashing with empty values
      expect(screen.getByRole('form')).toBeInTheDocument();
    });

    it('handles rapid clicking without errors', () => {
      render(
        <TestWrapper>
          <ApartmentComplexForm />
        </TestWrapper>
      );
      
      // Use the floor count section specifically to avoid ambiguity
      const floorSection = screen.getByRole('group', { name: /floor count selection/i });
      const floorButtons = floorSection.querySelectorAll('button');
      const floorButton1 = floorButtons[0]; // First button (1)
      const floorButton2 = floorButtons[1]; // Second button (2)
      const floorButton3 = floorButtons[2]; // Third button (3)
      
      // Rapid clicking should not cause errors
      expect(() => {
        fireEvent.click(floorButton1);
        fireEvent.click(floorButton2);
        fireEvent.click(floorButton3);
        fireEvent.click(floorButton1);
        fireEvent.click(floorButton2);
      }).not.toThrow();
    });
  });
});