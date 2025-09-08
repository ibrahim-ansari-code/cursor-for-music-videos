import { FC } from 'react';

interface SkeletonProps {
  className?: string;
  rowCount?: number;
}

// Primitives
export const SkeletonLine: FC<{
  width?: string;
  height?: string;
  rounded?: string;
  className?: string;
}>;

export const SkeletonCircle: FC<{
  size?: string;
  className?: string;
}>;

export const SkeletonPill: FC<SkeletonProps>;
export const SkeletonBlock: FC<SkeletonProps>;
export const SkeletonText: FC<SkeletonProps>;

// Table skeletons
export const TableSkeleton: FC<SkeletonProps>;
export const PropertiesTableSkeleton: FC<SkeletonProps>;
export const LeasesTableSkeleton: FC<SkeletonProps>;
export const TenantsTableSkeleton: FC<SkeletonProps>;

// Accounting table skeletons
export const AccountingTableSkeleton: FC<SkeletonProps>;
export const PaymentsTableSkeleton: FC<SkeletonProps>;
export const ExpensesTableSkeleton: FC<SkeletonProps>;
export const InvoicesTableSkeleton: FC<SkeletonProps>;

// Other skeletons
export const RentTrackerSkeleton: FC<SkeletonProps>;
export const CardSkeleton: FC<SkeletonProps>;
export const FinancialCardSkeleton: FC<SkeletonProps>;
export const PortfolioCardSkeleton: FC<SkeletonProps>;
export const DuePanelSkeleton: FC<SkeletonProps>;
export const StatusCardSkeleton: FC<SkeletonProps>;
export const ChartSkeleton: FC<SkeletonProps>;
export const MaintenanceSkeleton: FC<SkeletonProps>;
export const PropertyDetailSkeleton: FC<SkeletonProps>;
export const IntegrationsSkeleton: FC<SkeletonProps>;
export const SettingsSkeleton: FC<SkeletonProps>;

// Theme with proper interface
export interface SkeletonTheme {
  baseClass: string;
  animateClass: string;
  colorClass: string;
  rounded: string;
  height: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  width: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
    full: string;
  };
}

export const SKELETON_THEME: SkeletonTheme;