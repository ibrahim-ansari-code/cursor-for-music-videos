import React, { useState, useEffect, useCallback } from "react";
import {
  getMaintenanceSummary,
  fetchMaintenanceRequests,
  createMaintenanceRequest,
  updateMaintenanceRequest,
  deleteMaintenanceRequest,
} from "../utils/api";
import MaintenanceTable from "../components/maintenance/MaintenanceTable";
import MaintenanceRequestModal from "../components/maintenance/MaintenanceRequestModal";
import StatusCard from "../components/maintenance/StatusCard";
import LoadingSpinner from "../components/LoadingSpinner";

const Maintenance = () => {
  const [summary, setSummary] = useState(null);
  const [requests, setRequests] = useState([]);
  const [filteredRequests, setFilteredRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState("All Requests");

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRequest, setEditingRequest] = useState(null);
  const [viewingRequest, setViewingRequest] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [summaryData, requestsData] = await Promise.all([
        getMaintenanceSummary(),
        fetchMaintenanceRequests(),
      ]);
      setSummary(summaryData);
      setRequests(requestsData);
    } catch (err) {
      setError(err.message || "Failed to fetch maintenance data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    let result = [...requests];
    if (statusFilter !== "All Requests") {
      result = requests.filter((req) => req.status === statusFilter);
    }
    setFilteredRequests(result);
  }, [statusFilter, requests]);

  const handleModalSubmit = async (formData) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const payload = {
        ...formData,
        property_id: formData.property_id
          ? Number(formData.property_id)
          : undefined,
        unit_id: Number.parseInt(formData.unit_id, 10),
        tenant_id: formData.tenant_id
          ? Number.parseInt(formData.tenant_id, 10)
          : null,
        estimated_cost: formData.estimated_cost
          ? Number.parseFloat(formData.estimated_cost)
          : null,
      };

      if (editingRequest) {
        await updateMaintenanceRequest(editingRequest.id, payload);
      } else {
        await createMaintenanceRequest(payload);
      }
      closeModal();
      await fetchData();
    } catch (error) {
      console.error("Failed to save request:", error);
      setError(error.message || "Failed to save the request.");
    } finally {
      setIsSubmitting(false);
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
      setError(null);
      try {
        await deleteMaintenanceRequest(requestId);
        setRequests((prev) => prev.filter((req) => req.id !== requestId));
        fetchData();
      } catch (error) {
        console.error("Failed to delete request:", error);
        setError(error.message || "Failed to delete request.");
      }
    }
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
    return <LoadingSpinner message="Loading maintenance dashboard..." />;
  if (error && !summary)
    return <div className="p-6 text-center text-red-500">Error: {error}</div>;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Maintenance</h1>
          <p className="text-gray-500">Maintenance requests and tracking</p>
        </div>
        <button
          type="button"
          onClick={openModalForNew}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <i className="fas fa-plus mr-2" />
          New Maintenance Request
        </button>
      </div>

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
          onClick={() => setStatusFilter("All Requests")}
          active={statusFilter === "All Requests"}
        />
        <StatusCard
          title="Pending"
          count={summary?.pending ?? (loading ? "..." : 0)}
          icon="fa-hourglass-start"
          color="yellow"
          onClick={() => setStatusFilter("Pending")}
          active={statusFilter === "Pending"}
        />
        <StatusCard
          title="In Progress"
          count={summary?.in_progress ?? (loading ? "..." : 0)}
          icon="fa-tasks"
          color="blue"
          onClick={() => setStatusFilter("In Progress")}
          active={statusFilter === "In Progress"}
        />
        <StatusCard
          title="Completed"
          count={summary?.completed ?? (loading ? "..." : 0)}
          icon="fa-check-circle"
          color="green"
          onClick={() => setStatusFilter("Completed")}
          active={statusFilter === "Completed"}
        />
      </div>

      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex border-b mb-4">
          {TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setStatusFilter(tab)}
              className={`px-4 py-2 ${
                statusFilter === tab
                  ? "border-b-2 border-blue-600 text-blue-600"
                  : "text-gray-500"
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
        {loading ? (
          <LoadingSpinner message="Loading requests..." />
        ) : (
          <MaintenanceTable
            requests={filteredRequests}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onView={handleView}
          />
        )}
      </div>

      {isModalOpen && (
        <MaintenanceRequestModal
          isOpen={isModalOpen}
          onClose={closeModal}
          onSubmit={handleModalSubmit}
          request={editingRequest || viewingRequest}
          isViewing={!!viewingRequest}
          isSubmitting={isSubmitting}
        />
      )}
    </div>
  );
};

export default Maintenance;
