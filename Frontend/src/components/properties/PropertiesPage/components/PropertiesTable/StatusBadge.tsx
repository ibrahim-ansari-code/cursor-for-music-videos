interface StatusBadgeProps {
  status: string;
}

export const StatusBadge = ({ status }: StatusBadgeProps) => {
  const statusStyles: Record<string, string> = {
    ACTIVE: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 border border-green-200 dark:border-green-700',
    INACTIVE: 'bg-gray-100 dark:bg-gray-900/30 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700',
    DRAFT: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 border border-blue-200 dark:border-blue-700',
    ARCHIVED: 'bg-slate-100 dark:bg-slate-900/30 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700',
    RENTED: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 border border-green-200 dark:border-green-700',
    VACANT: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 border border-yellow-200 dark:border-yellow-700',
    PARTIALLY_RENTED: 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-700',
  };

  const dotColors: Record<string, string> = {
    ACTIVE: 'bg-green-500 dark:bg-green-400',
    INACTIVE: 'bg-gray-500 dark:bg-gray-400',
    DRAFT: 'bg-blue-500 dark:bg-blue-400',
    ARCHIVED: 'bg-slate-500 dark:bg-slate-400',
    RENTED: 'bg-green-500 dark:bg-green-400',
    VACANT: 'bg-yellow-500 dark:bg-yellow-400',
    PARTIALLY_RENTED: 'bg-amber-500 dark:bg-amber-400',
  };

  const statusLabels: Record<string, string> = {
    ACTIVE: 'Active',
    INACTIVE: 'Inactive',
    DRAFT: 'Draft',
    ARCHIVED: 'Archived',
    RENTED: 'Rented',
    VACANT: 'Vacant',
    PARTIALLY_RENTED: 'Partially Rented',
  };

  const normalizedStatus = status.toUpperCase();

  return (
    <span
      className={`inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold shadow-sm transition-all duration-200 ${
        statusStyles[normalizedStatus] || 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700'
      }`}
    >
      <span className={`w-2 h-2 mr-2 rounded-full ${
        dotColors[normalizedStatus] || 'bg-gray-500 dark:bg-gray-400'
      }`}></span>
      {statusLabels[normalizedStatus] || status}
    </span>
  );
};