import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import PropertyFilterDropdown from "../../../src/components/maintenance/PropertyFilter/PropertyFilterDropdown";
import type { Property } from "../../../src/types/property";
import { PropertyType, PropertyStatus } from "../../../src/types/property";

describe("PropertyFilterDropdown", () => {
  const mockProperties: Property[] = [
    {
      id: 1,
      name: "Sunset Apartments",
      address: "123 Main St",
      city: "San Francisco",
      province: "CA",
      postal_code: "94102",
      property_type: PropertyType.APARTMENT_COMPLEX,
      status: PropertyStatus.ACTIVE,
      user_id: "user-123",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    },
    {
      id: 2,
      name: "Ocean View Complex",
      address: "456 Beach Blvd",
      city: "Santa Monica",
      province: "CA",
      postal_code: "90401",
      property_type: PropertyType.APARTMENT_COMPLEX,
      status: PropertyStatus.ACTIVE,
      user_id: "user-123",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    },
    {
      id: 3,
      name: "Downtown Office",
      address: "789 Business Ave",
      city: "Los Angeles",
      province: "CA",
      postal_code: "90001",
      property_type: PropertyType.COMMERCIAL,
      status: PropertyStatus.ACTIVE,
      user_id: "user-123",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    },
  ];

  const mockOnPropertyChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it('renders the dropdown button with "All Properties" by default', () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      expect(screen.getByText("All Properties")).toBeInTheDocument();
      expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("renders the dropdown button with selected property name", () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={1}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      expect(screen.getByText("Sunset Apartments")).toBeInTheDocument();
    });

    it("applies blue styling when a property is selected (filtered state)", () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={1}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole("button");
      expect(button).toHaveClass("bg-blue-50", "text-blue-700");
    });

    it("applies default styling when no property is selected", () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole("button");
      expect(button).toHaveClass("bg-white", "text-gray-700");
    });
  });

  describe("Dropdown Interaction", () => {
    it("opens dropdown menu when button is clicked", () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      // Check for "All Properties" option in dropdown
      const allPropertiesOptions = screen.getAllByText("All Properties");
      expect(allPropertiesOptions.length).toBeGreaterThan(1); // Button + dropdown option
    });

    it("closes dropdown when button is clicked again", async () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole("button");

      // Open dropdown
      fireEvent.click(button);
      let allPropertiesOptions = screen.getAllByText("All Properties");
      expect(allPropertiesOptions.length).toBeGreaterThan(1);

      // Close dropdown
      fireEvent.click(button);
      await waitFor(() => {
        allPropertiesOptions = screen.getAllByText("All Properties");
        expect(allPropertiesOptions.length).toBe(1); // Only button text remains
      });
    });

    it("displays all properties in the dropdown", () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      expect(screen.getByText("Sunset Apartments")).toBeInTheDocument();
      expect(screen.getByText("Ocean View Complex")).toBeInTheDocument();
      expect(screen.getByText("Downtown Office")).toBeInTheDocument();
    });

    it("displays property addresses in the dropdown", () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      expect(screen.getByText("123 Main St")).toBeInTheDocument();
      expect(screen.getByText("456 Beach Blvd")).toBeInTheDocument();
      expect(screen.getByText("789 Business Ave")).toBeInTheDocument();
    });

    it("shows checkmark on selected property", () => {
      const { container } = render(
        <PropertyFilterDropdown
          selectedProperty={1}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      // Check for SVG checkmark (by checking for path element with specific d attribute)
      const svgIcons = container.querySelectorAll("svg path");
      const checkmarkPath = Array.from(svgIcons).find((path) =>
        path.getAttribute("d")?.includes("M16.707 5.293")
      );
      expect(checkmarkPath).toBeTruthy();
    });
  });

  describe("Property Selection", () => {
    it("calls onPropertyChange with property ID when property is clicked", () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      const sunsetApartments = screen.getByText("Sunset Apartments");
      fireEvent.click(sunsetApartments);

      expect(mockOnPropertyChange).toHaveBeenCalledWith(1);
    });

    it('calls onPropertyChange with null when "All Properties" is clicked', () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={1}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      // Get all buttons and find the "All Properties" option in the dropdown
      const buttons = screen.getAllByRole("button");
      const allPropertiesButton = buttons.find(
        (btn) => btn.textContent?.includes("All Properties") && btn !== button
      );

      if (allPropertiesButton) {
        fireEvent.click(allPropertiesButton);
      }

      expect(mockOnPropertyChange).toHaveBeenCalledWith(null);
    });

    it("closes dropdown after selecting a property", async () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      const oceanView = screen.getByText("Ocean View Complex");
      fireEvent.click(oceanView);

      await waitFor(() => {
        // Dropdown should close, so property names should not be in document
        expect(screen.queryByText("Downtown Office")).not.toBeInTheDocument();
      });
    });
  });

  describe("Edge Cases", () => {
    it("handles empty properties list gracefully", () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={[]}
        />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      expect(screen.getByText("No properties found")).toBeInTheDocument();
    });

    it("handles property without address", () => {
      const propertiesWithoutAddress: Property[] = [
        {
          ...mockProperties[0],
          address: undefined as any,
        },
      ];

      render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={propertiesWithoutAddress}
        />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      expect(screen.getByText("Sunset Apartments")).toBeInTheDocument();
      // Address should not throw error even if undefined
    });

    it("handles selecting a property that no longer exists in the list", () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={999} // Non-existent property ID
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      // Button should still render (even though property name is undefined)
      const button = screen.getByRole("button");
      expect(button).toBeInTheDocument();

      // The span will be empty because property doesn't exist
      // This is acceptable behavior - in real app, this shouldn't happen
      // because selectedProperty should always match a property in the list
    });
  });

  describe("Accessibility", () => {
    it("has proper button role", () => {
      render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={mockProperties}
        />
      );

      expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("dropdown closes when clicking outside", async () => {
      render(
        <div>
          <PropertyFilterDropdown
            selectedProperty={null}
            onPropertyChange={mockOnPropertyChange}
            properties={mockProperties}
          />
          <div data-testid="outside">Outside element</div>
        </div>
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      // Dropdown should be open
      expect(screen.getByText("Sunset Apartments")).toBeInTheDocument();

      // Click outside
      const outsideElement = screen.getByTestId("outside");
      fireEvent.mouseDown(outsideElement);

      await waitFor(() => {
        // Dropdown should close
        expect(screen.queryByText("Downtown Office")).not.toBeInTheDocument();
      });
    });
  });

  describe("Performance", () => {
    it("handles large number of properties efficiently", () => {
      const manyProperties: Property[] = Array.from(
        { length: 100 },
        (_, i) => ({
          ...mockProperties[0],
          id: i + 1,
          name: `Property ${i + 1}`,
        })
      );

      const startTime = performance.now();

      const { container } = render(
        <PropertyFilterDropdown
          selectedProperty={null}
          onPropertyChange={mockOnPropertyChange}
          properties={manyProperties}
        />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Render should complete in less than 1 second even with 100 properties
      expect(renderTime).toBeLessThan(1000);

      // Should have scrollable dropdown container
      const dropdownContainer = container.querySelector(
        ".max-h-96.overflow-y-auto"
      );
      expect(dropdownContainer).toBeInTheDocument();

      // Verify properties are rendered
      expect(screen.getByText("Property 1")).toBeInTheDocument();
      expect(screen.getByText("Property 50")).toBeInTheDocument();
      expect(screen.getByText("Property 100")).toBeInTheDocument();
    });
  });
});
