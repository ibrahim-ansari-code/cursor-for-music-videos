import { MaintenanceStatus } from "../../utils/api/maintenance/types";

interface MaintenanceFiltersProps {
  activeFilter: MaintenanceStatus | "ALL";
  onFilterChange: (filter: MaintenanceStatus | "ALL") => void;
}

const MaintenanceFilters = ({
  activeFilter,
  onFilterChange,
}: MaintenanceFiltersProps) => {
  const filters = [
    { key: "ALL" as const, label: "All" },
    { key: MaintenanceStatus.NEW, label: "New" },
    { key: MaintenanceStatus.PENDING, label: "Open" },
    { key: MaintenanceStatus.IN_PROGRESS, label: "In Progress" },
    { key: MaintenanceStatus.SCHEDULED, label: "Scheduled" },
    { key: MaintenanceStatus.COMPLETED, label: "Completed" },
    { key: MaintenanceStatus.CANCELLED, label: "Cancelled" },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {filters.map((filter) => (
        <button
          key={filter.key}
          onClick={() => onFilterChange(filter.key)}
          className={`px-4 py-2 rounded-md font-medium text-sm transition-colors cursor-pointer ${
            activeFilter === filter.key
              ? "bg-gray-900 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
};

export default MaintenanceFilters;
