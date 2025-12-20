import { useState } from "react";
import {
  MaintenanceRequest,
  MaintenanceStatus,
  MaintenanceRequestCreate,
} from "../../utils/api/maintenance/types";
import {
  useMaintenanceRequests,
  useCreateMaintenanceRequest,
} from "../../hooks/useMaintenance";
import MaintenanceFilters from "./MaintenanceFilters";
import MaintenanceTable from "./MaintenanceTable";
import MaintenanceRequestForm from "./MaintenanceRequestForm";
import SkeletonMaintenanceLoading from "./ui/SkeletonMaintenanceLoading";
import MaintenanceViewDetailsModal from "./MaintenanceViewDetailsModal";
import { Plus, AlertCircle } from "lucide-react";

const MaintenanceDashboard = () => {
  const [activeFilter, setActiveFilter] = useState<MaintenanceStatus | "ALL">("ALL");
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [viewingRequest, setViewingRequest] = useState<MaintenanceRequest | null>(null);

  // Prepare filters for query
  const filters = activeFilter === "ALL" ? undefined : { status: activeFilter as MaintenanceStatus };
  
  // Fetch requests using TanStack Query
  const { data: requests = [], isLoading, isFetching, error, refetch } = useMaintenanceRequests(filters);
  const createMutation = useCreateMaintenanceRequest();

  const handleFilterChange = (filter: MaintenanceStatus | "ALL") => {
    setActiveFilter(filter);
  };

  const handleCreateRequest = async (data: MaintenanceRequestCreate) => {
    await createMutation.mutateAsync(data);
    setIsFormOpen(false);
  };

  // Only show skeleton on initial load (no data yet)
  if (isLoading && !requests.length) {
    return <SkeletonMaintenanceLoading />;
  }

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200">
      <div className="p-6">
        {/* Page Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-800">Maintenance Requests</h1>
            <p className="text-gray-600">Submit and track maintenance issues for your unit.</p>
          </div>
          <button
            onClick={() => setIsFormOpen(true)}
            className="bg-gray-900 text-white px-4 py-2 rounded-md hover:bg-gray-800 transition-all duration-200 font-medium cursor-pointer flex items-center"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Request
          </button>
        </div>

        <div className="space-y-6">
          <div className="bg-gray-50 flex items-center justify-between p-4 rounded-lg">
            <div className="flex items-center gap-3">
              <p className="text-xl font-semibold text-gray-800">
                Your Requests
              </p>
              {isFetching && (
                <div className="flex items-center text-sm text-gray-500">
                  <svg className="animate-spin h-4 w-4 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
              )}
            </div>
            {/* Filters */}
            <MaintenanceFilters
              activeFilter={activeFilter}
              onFilterChange={handleFilterChange}
            />
          </div>

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
                <p className="text-red-800">Failed to load maintenance requests. Please try again.</p>
              </div>
              <button
                onClick={() => refetch()}
                className="mt-2 text-red-600 hover:text-red-700 text-sm font-medium"
              >
                Try again
              </button>
            </div>
          )}

          {/* Requests Table */}
          <MaintenanceTable
            requests={requests}
            onViewDetails={(request) => setViewingRequest(request)}
            onCreateRequest={() => setIsFormOpen(true)}
          />
        </div>
      </div>

      {/* Create Request Modal */}
      <MaintenanceRequestForm
        isOpen={isFormOpen}
        onClose={() => setIsFormOpen(false)}
        onSubmit={handleCreateRequest}
        isLoading={createMutation.isPending}
      />

      {/* View Details Modal */}
      {viewingRequest && (
        <MaintenanceViewDetailsModal
          request={viewingRequest}
          onClose={() => setViewingRequest(null)}
        />
      )}
    </div>
  );
};

export default MaintenanceDashboard;
