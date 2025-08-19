import React, { useState, useEffect, useCallback, useMemo } from "react";
import MaintenanceTable from "../components/maintenance/MaintenanceTable";
import MaintenanceRequestModal from "../components/maintenance/MaintenanceRequestModal";
import StatusCard from "../components/maintenance/StatusCard";
import MaintenanceSkeleton, { MaintenanceTableSkeleton } from "../components/ui/skeletons/MaintenanceSkeleton";
import {
  useMaintenanceSummary,
  useMaintenanceRequests,
  useCreateMaintenanceRequest,
  useUpdateMaintenanceRequest,
  useDeleteMaintenanceRequest,
} from "../hooks/useMaintenanceQueries";

const Maintenance = () => {
  // Local UI state
  const [statusFilter, setStatusFilter] = useState("All Requests");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRequest, setEditingRequest] = useState(null);
  const [viewingRequest, setViewingRequest] = useState(null);

  // Build query parameters
  const queryParams = useMemo(() => {
    const params = {
      limit: pageSize,
      offset: (currentPage - 1) * pageSize,
    };

    // Add status filter if not "All Requests"
    if (statusFilter !== "All Requests") {
      const statusMap = {
        Pending: "pending",
        "In Progress": "in_progress", 
        Completed: "completed",
      };
      params.req_status = statusMap[statusFilter] ?? statusFilter;
    }

    return params;
  }, [statusFilter, currentPage, pageSize]);

  // TanStack Query hooks
  const { data: summary, isLoading: summaryLoading, error: summaryError } = useMaintenanceSummary();
  const { data: requestsData, isLoading: requestsLoading, error: requestsError, refetch } = useMaintenanceRequests(queryParams);
  
  // Mutation hooks
  const createRequestMutation = useCreateMaintenanceRequest();
  const updateRequestMutation = useUpdateMaintenanceRequest();
  const deleteRequestMutation = useDeleteMaintenanceRequest();

  // Extract data from query response
  const requests = useMemo(() => requestsData?.results || requestsData || [], [requestsData]);
  const hasMore = useMemo(() => {
    if (typeof requestsData?.total === "number") {
      return currentPage * pageSize < requestsData.total;
    }
    return (requestsData?.results || requestsData || []).length === pageSize;
  }, [requestsData, currentPage, pageSize]);
  const totalCount = useMemo(() => {
    return requestsData?.total ?? (requestsData?.results ? requestsData.results.length : requestsData?.length || 0);
  }, [requestsData]);

  // Combined loading and error states
  const loading = summaryLoading || requestsLoading;
  const error = summaryError || requestsError;

  // Reset to first page when status filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter]);

  const handleModalSubmit = async (formData) => {
    try {
      const payload = {
        ...formData,
        property_id: formData.property_id
          ? Number(formData.property_id)
          : undefined,
        unit_id:
          formData.unit_id && formData.unit_id !== ""
            ? Number.parseInt(formData.unit_id, 10)
            : null,
        tenant_id: formData.tenant_id
          ? Number.parseInt(formData.tenant_id, 10)
          : null,
        estimated_cost: formData.estimated_cost
          ? Number.parseFloat(formData.estimated_cost)
          : null,
      };

      if (editingRequest) {
        await updateRequestMutation.mutateAsync({ 
          requestId: editingRequest.id, 
          requestData: payload 
        });
      } else {
        await createRequestMutation.mutateAsync(payload);
      }
      closeModal();
      setCurrentPage(1); // Reset to first page after creating/editing
    } catch (error) {
      console.error("Failed to save request:", error);
      throw error; // Let the modal handle the error
    }
  };

  const handleEdit = (request) => {
    setEditingRequest(request);
    setViewingRequest(null);
    setIsModalOpen(true);
  };

  const handleView = (request) => {
    setViewingRequest(request);
    setEditingRequest(null);
    setIsModalOpen(true);
  };

  const handleDelete = async (requestId) => {
    if (window.confirm("Are you sure you want to delete this request?")) {
      try {
        await deleteRequestMutation.mutateAsync(requestId);
      } catch (error) {
        console.error("Failed to delete request:", error);
      }
    }
  };

  const handleStatusFilterChange = (newStatus) => {
    setStatusFilter(newStatus);
    setCurrentPage(1); // Reset to first page when changing filters
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  const handleLoadMore = () => {
    setCurrentPage(prev => prev + 1);
  };

  const openModalForNew = () => {
    setEditingRequest(null);
    setViewingRequest(null);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingRequest(null);
    setViewingRequest(null);
  };

  const TABS = ["All Requests", "Pending", "In Progress", "Completed"];

  if (loading && !summary)
    return <MaintenanceSkeleton />;
  if (error && !summary)
    return <div className="p-6 text-center text-red-500">Error: {error}</div>;

  return (
    <div className="p-6">
      {error && (
        <div className="p-4 mb-4 text-center bg-red-100 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatusCard
          title="Total Requests"
          count={summary?.total_requests ?? (loading ? "..." : 0)}
          icon="fa-tools"
          color="gray"
          onClick={() => handleStatusFilterChange("All Requests")}
          active={statusFilter === "All Requests"}
        />
        <StatusCard
          title="Pending"
          count={summary?.pending ?? (loading ? "..." : 0)}
          icon="fa-hourglass-start"
          color="yellow"
          onClick={() => handleStatusFilterChange("Pending")}
          active={statusFilter === "Pending"}
        />
        <StatusCard
          title="In Progress"
          count={summary?.in_progress ?? (loading ? "..." : 0)}
          icon="fa-tasks"
          color="blue"
          onClick={() => handleStatusFilterChange("In Progress")}
          active={statusFilter === "In Progress"}
        />
        <StatusCard
          title="Completed"
          count={summary?.completed ?? (loading ? "..." : 0)}
          icon="fa-check-circle"
          color="green"
          onClick={() => handleStatusFilterChange("Completed")}
          active={statusFilter === "Completed"}
        />
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="flex justify-between items-center px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center">
            {TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => handleStatusFilterChange(tab)}
                className={`px-4 py-2 mr-1 rounded-md text-sm font-medium transition-colors duration-150 ${
                  statusFilter === tab
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                }`}
              >
                {tab} (
                {tab === "All Requests"
                  ? summary?.total_requests ?? 0
                  : tab === "Pending"
                  ? summary?.pending ?? 0
                  : tab === "In Progress"
                  ? summary?.in_progress ?? 0
                  : tab === "Completed"
                  ? summary?.completed ?? 0
                  : 0}
                )
              </button>
            ))}
          </div>
          <div className="flex items-center">
            <button
              type="button"
              onClick={openModalForNew}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-150"
            >
              <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Maintenance Request
            </button>
          </div>
        </div>

        {loading && currentPage === 1 ? (
          <MaintenanceTableSkeleton />
        ) : (
          <>
            <MaintenanceTable
              requests={requests}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onView={handleView}
              currentPage={currentPage}
              pageSize={pageSize}
            />

            {/* Pagination Controls */}
            <div className="px-6 py-4 flex items-center justify-between border-t border-gray-200">
              <div className="text-sm text-gray-700">
                Showing page {currentPage} ({requests.length} items)
                {typeof totalCount === "number" && totalCount > 0 && (
                  <span className="ml-2">of {totalCount} total</span>
                )}
                {statusFilter !== "All Requests" && (
                  <span className="ml-2 text-blue-600">
                    Filtered by: {statusFilter}
                  </span>
                )}
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage <= 1}
                  className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md">
                  Page {currentPage}
                </span>
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={!hasMore || loading}
                  className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
                {hasMore && (
                  <button
                    onClick={handleLoadMore}
                    disabled={loading}
                    className="ml-4 px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-300 rounded-md hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? "Loading..." : "Load More"}
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>

      {isModalOpen && (
        <MaintenanceRequestModal
          isOpen={isModalOpen}
          onClose={closeModal}
          onSubmit={handleModalSubmit}
          request={editingRequest || viewingRequest}
          isViewing={!!viewingRequest}
          isSubmitting={createRequestMutation.isPending || updateRequestMutation.isPending}
        />
      )}
    </div>
  );
};

export default Maintenance;
