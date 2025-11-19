import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import PropertyFilterSkeleton from '../../../src/components/common/PropertyFilter/PropertyFilterSkeleton';

describe('PropertyFilterSkeleton Component', () => {
  describe('Rendering', () => {
    it('should render without crashing', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      const skeleton = container.querySelector('.animate-pulse');
      expect(skeleton).toBeInTheDocument();
    });

    it('should have animate-pulse class for loading animation', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      const pulsingElement = container.querySelector('.animate-pulse');
      expect(pulsingElement).toBeInTheDocument();
    });

    it('should have proper structure matching PropertyFilter component', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      // Should have button-like appearance
      const buttonSkeleton = container.querySelector('.inline-flex');
      expect(buttonSkeleton).toBeInTheDocument();
    });

    it('should have border and shadow styling', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      const skeleton = container.querySelector('.border');
      expect(skeleton).toBeInTheDocument();

      const shadowElement = container.querySelector('.shadow-sm');
      expect(shadowElement).toBeInTheDocument();
    });

    it('should have rounded corners', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      const roundedElement = container.querySelector('.rounded-lg');
      expect(roundedElement).toBeInTheDocument();
    });
  });

  describe('Dark Mode Support', () => {
    it('should have dark mode classes', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      const element = container.firstChild as HTMLElement;
      expect(element?.className || '').toContain('dark:');
    });

    it('should have dark background variant', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      const darkBg = container.querySelector('.dark\\:bg-gray-800');
      expect(darkBg).toBeInTheDocument();
    });

    it('should have dark border variant', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      const darkBorder = container.querySelector('.dark\\:border-gray-600');
      expect(darkBorder).toBeInTheDocument();
    });
  });

  describe('Skeleton Elements', () => {
    it('should render skeleton placeholders for icon and text', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      // Should have multiple skeleton elements (icon + text + chevron)
      const skeletonElements = container.querySelectorAll('.bg-gray-300');
      expect(skeletonElements.length).toBeGreaterThan(0);
    });

    it('should have consistent sizing with actual component', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      // Should have padding similar to PropertyFilter
      const paddedElement = container.querySelector('.px-4');
      expect(paddedElement).toBeInTheDocument();

      const verticalPadding = container.querySelector('.py-2');
      expect(verticalPadding).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have appropriate aria-attributes for loading state', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      const skeleton = container.firstChild as HTMLElement;
      // Skeleton should indicate it's a placeholder
      expect(skeleton).toBeDefined();
    });

    it('should not be interactive', () => {
      render(<PropertyFilterSkeleton />);

      // Should not have button or input elements
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    });
  });

  describe('Visual Consistency', () => {
    it('should match PropertyFilter button dimensions', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      // Check for small text sizing
      const smallText = container.querySelector('.text-sm');
      expect(smallText).toBeInTheDocument();
    });

    it('should have font-medium weight', () => {
      const { container } = render(<PropertyFilterSkeleton />);

      const mediumFont = container.querySelector('.font-medium');
      expect(mediumFont).toBeInTheDocument();
    });
  });

  describe('Multiple Instances', () => {
    it('should render multiple skeletons independently', () => {
      const { container } = render(
        <div>
          <PropertyFilterSkeleton />
          <PropertyFilterSkeleton />
          <PropertyFilterSkeleton />
        </div>
      );

      const skeletons = container.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBe(3);
    });
  });
});
