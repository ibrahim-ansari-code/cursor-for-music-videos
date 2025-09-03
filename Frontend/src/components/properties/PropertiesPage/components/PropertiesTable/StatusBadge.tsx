interface StatusBadgeProps {
  status: string;
}

export const StatusBadge = ({ status }: StatusBadgeProps) => {
  const statusStyles: Record<string, string> = {
    ACTIVE: 'bg-green-50 text-green-700',
    INACTIVE: 'bg-gray-50 text-gray-700',
    DRAFT: 'bg-blue-50 text-blue-700',
    ARCHIVED: 'bg-slate-50 text-slate-700',
    RENTED: 'bg-emerald-50 text-emerald-700',
    VACANT: 'bg-yellow-50 text-yellow-700',
    PARTIALLY_RENTED: 'bg-amber-50 text-amber-700',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        statusStyles[status.toUpperCase()] || 'bg-gray-100 text-gray-800'
      }`}
    >
      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current"></span>
      {status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()}
    </span>
  );
};