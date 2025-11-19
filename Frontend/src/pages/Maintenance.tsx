import React, { useState, useEffect, useMemo } from "react";
import { toast } from "react-toastify";
import * as Sentry from "@sentry/react";
import MaintenanceTable from "../components/maintenance/MaintenanceTable";
import CreateMaintenanceModal from "../components/maintenance/CreateMaintenanceModal/index";
import EditMaintenanceModal from "../components/maintenance/EditMaintenanceModal";
import StatusCard from "../components/maintenance/StatusCard";
import MaintenanceSkeleton, {
  MaintenanceTableSkeleton,
} from "../components/ui/skeletons/MaintenanceSkeleton";
import PropertyFilterSkeleton from "../components/maintenance/PropertyFilter/PropertyFilterSkeleton";
import PropertyFilterDropdown from "../components/maintenance/PropertyFilter/PropertyFilterDropdown";
import {
  useMaintenanceSummary,
  useMaintenanceRequests,
  useCreateMaintenanceRequest,
  useUpdateMaintenanceRequest,
  useDeleteMaintenanceRequest,
  useBulkDeleteMaintenanceRequests,
} from "../hooks/useMaintenanceQueries";
import useProperties from "../hooks/useProperties";
import type { MaintenanceRequest } from "../types/tenant";

const Maintenance: React.FC = () => {
  // Fetch properties for filter
  const {
    properties,
    loading: propertiesLoading,
    error: propertiesError,
  } = useProperties();

  // Filter state management
  const [propertyFilter, setPropertyFilter] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("All Requests");

  // Helper functions for filter management
  const clearAllFilters = () => {
    setPropertyFilter(null);
    setStatusFilter("All Requests");
  };

  const hasActiveFilters = propertyFilter !== null || statusFilter !== "All Requests";

  // Local UI state
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(20);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingRequest, setEditingRequest] =
    useState<MaintenanceRequest | null>(null);
  const [viewingRequest, setViewingRequest] =
    useState<MaintenanceRequest | null>(null);
  const [selectedRequests, setSelectedRequests] = useState<Set<number>>(
    new Set()
  );

  // Build query parameters for requests
  const queryParams = useMemo(() => {
    const params: Record<string, any> = {
      limit: pageSize,
      offset: (currentPage - 1) * pageSize,
    };

    // Add property filter if selected
    if (propertyFilter) {
      params.property_id = propertyFilter;
    }

    // Add status filter if not "All Requests"
    if (statusFilter !== "All Requests") {
      const statusMap: Record<string, string> = {
        Pending: "pending",
        "In Progress": "in_progress",
        Completed: "completed",
      };
      params.req_status =
        statusMap[statusFilter] ?? statusFilter;
    }

    return params;
  }, [
    propertyFilter,
    statusFilter,
    currentPage,
    pageSize,
  ]);

  // Build query parameters for summary (property filter only, not status)
  const summaryParams = useMemo(() => {
    const params: Record<string, any> = {};

    // Add property filter if selected
    if (propertyFilter) {
      params.property_id = propertyFilter;
    }

    return params;
  }, [propertyFilter]);

  // TanStack Query hooks
  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
  } = useMaintenanceSummary(summaryParams);
  const {
    data: requestsData,
    isLoading: requestsLoading,
    error: requestsError,
    refetch: _refetch,
  } = useMaintenanceRequests(queryParams);

  // Mutation hooks
  const createRequestMutation = useCreateMaintenanceRequest();
  const updateRequestMutation = useUpdateMaintenanceRequest();
  const deleteRequestMutation = useDeleteMaintenanceRequest();
  const bulkDeleteRequestMutation = useBulkDeleteMaintenanceRequests();

  // Extract data from query response
  const requests = useMemo(
    () => requestsData?.results || requestsData || [],
    [requestsData]
  );
  const hasMore = useMemo(() => {
    if (typeof requestsData?.total === "number") {
      return currentPage * pageSize < requestsData.total;
    }
    return (requestsData?.results || requestsData || []).length === pageSize;
  }, [requestsData, currentPage, pageSize]);
  const totalCount = useMemo(() => {
    return (
      requestsData?.total ??
      (requestsData?.results
        ? requestsData.results.length
        : requestsData?.length || 0)
    );
  }, [requestsData]);

  // Combined loading and error states
  const loading = summaryLoading || requestsLoading;
  const error = summaryError || requestsError;

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter, propertyFilter]);

  // Clear selection when requests change (e.g., after filter changes or deletion)
  useEffect(() => {
    const requestArray = requests as MaintenanceRequest[];
    const currentRequestIds = new Set(
      requestArray.map((r: MaintenanceRequest) => r.id)
    );
    setSelectedRequests((prev) => {
      const filtered = Array.from(prev).filter((id) =>
        currentRequestIds.has(id)
      );
      return filtered.length !== prev.size ? new Set(filtered) : prev;
    });
  }, [requests]);

  const handleModalSubmit = async (formData: any) => {
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
          requestData: payload,
        });
        toast.success("Maintenance request updated successfully!");
      } else {
        await createRequestMutation.mutateAsync(payload);
        toast.success("Maintenance request created successfully!");
      }
      closeModal();
      setCurrentPage(1); // Reset to first page after creating/editing
    } catch (error: any) {
      console.error("Failed to save request:", error);
      toast.error(error?.message || "Failed to save maintenance request");
      throw error; // Let the modal handle the error
    }
  };

  const handleEdit = (request: MaintenanceRequest) => {
    setEditingRequest(request);
    setViewingRequest(null);
    setIsModalOpen(true);
  };

  const handleView = (request: MaintenanceRequest) => {
    setViewingRequest(request);
    setEditingRequest(null);
    setIsModalOpen(true);
  };

  const handleDelete = async (requestId: number) => {
    if (window.confirm("Are you sure you want to delete this request?")) {
      try {
        await deleteRequestMutation.mutateAsync(requestId);
        toast.success("Maintenance request deleted successfully!");
      } catch (error: any) {
        console.error("Failed to delete request:", error);
        toast.error(error?.message || "Failed to delete maintenance request");
      }
    }
  };

  const handleBulkDelete = async () => {
    if (selectedRequests.size === 0) return;

    const requestIdsArray = Array.from(selectedRequests);

    if (
      window.confirm(
        `Are you sure you want to delete ${
          requestIdsArray.length
        } selected request${requestIdsArray.length !== 1 ? "s" : ""}?`
      )
    ) {
      await Sentry.startSpan(
        {
          op: "ui.click",
          name: "Bulk Delete Maintenance Requests",
        },
        async (span) => {
          span.setAttribute("requestCount", requestIdsArray.length);
          span.setAttribute("requestIds", requestIdsArray.join(","));

          try {
            Sentry.logger.info(
              "Bulk deleting maintenance requests after confirmation",
              {
                requestCount: requestIdsArray.length,
                requestIds: requestIdsArray,
              }
            );

            await bulkDeleteRequestMutation.mutateAsync(requestIdsArray);

            toast.success(
              `${requestIdsArray.length} maintenance request${
                requestIdsArray.length !== 1 ? "s" : ""
              } deleted successfully!`
            );

            Sentry.logger.info(
              "Maintenance requests bulk deleted successfully",
              {
                requestCount: requestIdsArray.length,
              }
            );

            setSelectedRequests(new Set());
          } catch (error: any) {
            const errorMessage =
              error?.response?.data?.detail ||
              error?.message ||
              "Failed to delete selected requests";

            toast.error(errorMessage);

            Sentry.captureException(error, {
              tags: {
                component: "Maintenance",
                action: "bulk_delete_maintenance_requests",
                feature: "maintenance",
                operation: "bulk_delete",
              },
              contexts: {
                bulkDelete: {
                  requestCount: requestIdsArray.length,
                  requestIds: requestIdsArray,
                },
              },
            });

            throw error;
          }
        }
      );
    }
  };

  const handleStatusFilterChange = (newStatus: string) => {
    setStatusFilter(newStatus);
    setCurrentPage(1); // Reset to first page when changing filters
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
  };

  const handleLoadMore = () => {
    setCurrentPage((prev) => prev + 1);
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

  if (loading && !summary) return <MaintenanceSkeleton />;
  if (error && !summary)
    return (
      <div className="p-6 text-center text-red-500">
        Error: {error instanceof Error ? error.message : String(error)}
      </div>
    );

  return (
    <div className="p-6 min-h-screen dark-bg transition-colors duration-300">
      {error && (
        <div className="p-4 mb-4 text-center bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-700 transition-colors duration-300">
          {error instanceof Error ? error.message : String(error)}
        </div>
      )}

      {/* Status Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatusCard
          title="Total Requests"
          count={summary?.total_requests ?? (loading ? "..." : 0)}
          icon="fa-tools"
          color="gray"
          onClick={() => {
            setStatusFilter("All Requests");
            setPropertyFilter(null);
            setCurrentPage(1);
          }}
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

      {/* Property Filter Section */}
      <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg shadow dark-divider border transition-colors duration-300">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            <i className="fas fa-filter mr-2"></i>
            Filter by Property:
          </span>
          {propertiesError ? (
            <span className="text-sm text-red-600 dark:text-red-400">
              <i className="fas fa-exclamation-triangle mr-2"></i>
              Failed to load properties
            </span>
          ) : propertiesLoading ? (
            <PropertyFilterSkeleton />
          ) : (
            <PropertyFilterDropdown
              selectedProperty={propertyFilter}
              onPropertyChange={setPropertyFilter}
              properties={properties}
            />
          )}
        </div>

        {/* Clear Filters Button */}
        {hasActiveFilters && (
          <button
            type="button"
            onClick={clearAllFilters}
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 border border-red-300 dark:border-red-600 rounded-lg transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            <i className="fas fa-times-circle mr-2"></i>
            Clear All Filters
          </button>
        )}
      </div>

      <div className="dark-panel dark-shadow rounded-lg overflow-hidden dark-divider border transition-colors duration-300">
        <div className="flex justify-between items-center px-6 py-4 dark-divider border-b dark-input transition-colors duration-300">
          <div className="flex items-center">
            {TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => handleStatusFilterChange(tab)}
                className={`px-4 py-2 mr-1 rounded-md text-sm font-medium transition-colors duration-150 ${
                  statusFilter === tab
                    ? "bg-blue-600 dark:bg-blue-500 text-white shadow-sm"
                    : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600"
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
            {selectedRequests.size > 0 && (
              <button
                type="button"
                onClick={handleBulkDelete}
                disabled={selectedRequests.size === 0}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors duration-150 mr-4"
              >
                Delete Selected ({selectedRequests.size})
              </button>
            )}
            <button
              type="button"
              onClick={openModalForNew}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-150"
            >
              <svg
                className="h-4 w-4 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
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
              requests={requests as MaintenanceRequest[]}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onView={handleView}
              currentPage={currentPage}
              pageSize={pageSize}
              selectedRequests={Array.from(selectedRequests)}
              onSelectedRequestsChange={(ids) =>
                setSelectedRequests(new Set(ids))
              }
            />

            {/* Pagination Controls */}
            <div className="px-6 py-4 flex items-center justify-between dark-divider border-t dark-input transition-colors duration-300">
              <div className="text-sm text-gray-700 dark:text-gray-300">
                Showing page {currentPage} ({requests.length} items)
                {typeof totalCount === "number" && totalCount > 0 && (
                  <span className="ml-2">of {totalCount} total</span>
                )}
                {hasActiveFilters && (
                  <span className="ml-2 text-blue-600 dark:text-blue-400">
                    {statusFilter !== "All Requests" && (
                      <>Filtered by: {statusFilter}</>
                    )}
                    {propertyFilter &&
                      statusFilter !== "All Requests" && <> • </>}
                    {propertyFilter && (
                      <>
                        Property:{" "}
                        {
                          properties.find(
                            (p) => p.id === propertyFilter
                          )?.name
                        }
                      </>
                    )}
                  </span>
                )}
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage <= 1}
                  className="px-3 py-2 text-sm font-medium text-gray-500 dark:text-gray-400 dark-panel dark-divider border rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-300"
                >
                  Previous
                </button>
                <span className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 dark-panel dark-divider border rounded-md transition-colors duration-300">
                  Page {currentPage}
                </span>
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={!hasMore || loading}
                  className="px-3 py-2 text-sm font-medium text-gray-500 dark:text-gray-400 dark-panel dark-divider border rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-300"
                >
                  Next
                </button>
                {hasMore && (
                  <button
                    onClick={handleLoadMore}
                    disabled={loading}
                    className="ml-4 px-3 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-300 dark:border-blue-600 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-300"
                  >
                    {loading ? "Loading..." : "Load More"}
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Create Modal */}
      {isModalOpen && !editingRequest && !viewingRequest && (
        <CreateMaintenanceModal
          isOpen={isModalOpen}
          onClose={closeModal}
          onSubmit={handleModalSubmit}
          isSubmitting={createRequestMutation.isPending}
        />
      )}

      {/* Edit/View Modal */}
      {isModalOpen && (editingRequest || viewingRequest) && (
        <EditMaintenanceModal
          isOpen={isModalOpen}
          onClose={closeModal}
          onSubmit={handleModalSubmit}
          request={editingRequest || viewingRequest!}
          isViewing={!!viewingRequest}
          isSubmitting={updateRequestMutation.isPending}
        />
      )}
    </div>
  );
};

export default Maintenance;
