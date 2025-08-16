import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  fetchPropertyById,
  createUnit,
  updateUnit,
  deleteUnit,
  fetchUnitLease,
} from "../utils/api";
import StatCard from "../components/StatCard"; // Import StatCard
import UnitTable from "../components/units/UnitTable"; // Import UnitTable
import NewUnitModal from "../components/units/NewUnitModal"; // Import NewUnitModal
import EditUnitModal from "../components/units/EditUnitModal"; // Import EditUnitModal
import LoadingSpinner from "../components/LoadingSpinner"; // Import LoadingSpinner
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import AssignTenantModal from "../components/units/AssignTenantModal"; // Import AssignTenantModal
import BulkAssignTenantModal from "../components/units/BulkAssignTenantModal";
import CSVUploadModal from "../components/units/CSVUploadModal";

// Icons for StatCards
const UnitIcon = () => <i className="fas fa-door-closed text-blue-600"></i>;
const VacantIcon = () => <i className="fas fa-door-open text-yellow-600"></i>;
const RevenueIcon = () => <i className="fas fa-dollar-sign text-green-600"></i>;

const PropertyDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Create unit modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Edit unit modal states
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [unitToEdit, setUnitToEdit] = useState(null);

  // Assign tenant modal states
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [currentUnit, setCurrentUnit] = useState(null);

  // Bulk operations state
  const [bulkMode, setBulkMode] = useState(false);
  const [selectedUnits, setSelectedUnits] = useState([]);
  const [showBulkAssignModal, setShowBulkAssignModal] = useState(false);
  const [showCSVUploadModal, setShowCSVUploadModal] = useState(false);

  useEffect(() => {
    loadProperty();
  }, [id]);

  const loadProperty = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log(`Fetching property details for ID: ${id}`);
      const data = await fetchPropertyById(id);
      console.log("Property data received:", data);

      // Fetch lease data for rented units
      if (data.units && data.units.length > 0) {
        const unitsWithLeases = await Promise.all(
          data.units.map(async (unit) => {
            if (unit.is_rented) {
              try {
                const lease = await fetchUnitLease(unit.id);
                return { ...unit, lease };
              } catch (leaseError) {
                console.error(`Error fetching lease for unit ${unit.id}:`, leaseError);
                return unit; // Return unit without lease data if fetch fails
              }
            }
            return unit;
          })
        );
        data.units = unitsWithLeases;
      }

      setProperty(data);
    } catch (err) {
      console.error("Error fetching property details:", err);
      setError(err.message || "Failed to load property details.");
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount || 0);
  };

  // Function to handle unit editing
  const handleEditUnit = (unitId) => {
    if (!property || !property.units) return;

    // Find the unit in the property data
    const unit = property.units.find((unit) => unit.id === unitId);
    if (!unit) {
      console.error(`Unit with ID ${unitId} not found`);
      return;
    }

    // Set up the edit modal
    setUnitToEdit(unit);
    setIsEditModalOpen(true);
  };

  // Function to handle unit deletion with optimistic updates
  const handleDeleteUnit = async (unitId) => {
    if (
      !window.confirm(
        "Are you sure you want to delete this unit? This action cannot be undone."
      )
    ) {
      return;
    }

    // Store original property state for rollback
    const originalProperty = property;
    const unitToDelete = property.units.find(u => u.id === unitId);

    try {
      setIsSubmitting(true);
      console.log(`Deleting unit with ID: ${unitId}`);

      // Optimistically remove the unit from local state
      setProperty(prev => ({
        ...prev,
        units: prev.units.filter(unit => unit.id !== unitId),
        stats: prev.stats && unitToDelete ? {
          ...prev.stats,
          total_units: prev.stats.total_units - 1,
          vacant_units: unitToDelete.is_rented
            ? prev.stats.vacant_units
            : prev.stats.vacant_units - 1,
          occupied_units: unitToDelete.is_rented
            ? prev.stats.occupied_units - 1
            : prev.stats.occupied_units,
          monthly_revenue: unitToDelete.is_rented && unitToDelete.monthly_rent
            ? (parseFloat(prev.stats.monthly_revenue) - parseFloat(unitToDelete.monthly_rent)).toFixed(2)
            : prev.stats.monthly_revenue
        } : null
      }));

      // Call API to delete the unit
      await deleteUnit(unitId);

      // Show success notification
      toast.success("Unit deleted successfully");

      // Refresh property data in the background for consistency
      loadProperty();
    } catch (error) {
      console.error("Error deleting unit:", error);

      // Rollback to original state on error
      setProperty(originalProperty);

      toast.error(error.message || "Failed to delete unit");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddNewUnit = () => {
    // Open create modal
    setIsCreateModalOpen(true);
  };

  // Function to handle unit creation with optimistic updates
  const handleCreateUnit = async (propertyId, unitData) => {
    try {
      setIsSubmitting(true);
      console.log("Creating new unit with data:", unitData);

      // Call API to create the unit
      const result = await createUnit(propertyId, unitData);

      // Optimistically add the new unit to the property
      setProperty(prev => ({
        ...prev,
        units: [...(prev.units || []), result],
        stats: prev.stats ? {
          ...prev.stats,
          total_units: prev.stats.total_units + 1,
          vacant_units: prev.stats.vacant_units + 1 // New units are always vacant
        } : null
      }));

      // Show success notification
      toast.success("Unit created successfully");

      // Close modal
      setIsCreateModalOpen(false);

      // Refresh property data in the background for consistency
      loadProperty();

      return result;
    } catch (error) {
      console.error("Error creating unit:", error);

      // Display a more user-friendly error
      const errorMessage = error.message || "Failed to create unit";
      toast.error(errorMessage);

      // Re-throw so the modal can handle display of the error
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  // Function to handle unit update with optimistic updates
  const handleUpdateUnit = async (unitId, unitData) => {
    // Store original property state for rollback
    const originalProperty = property;
    const originalUnit = property.units.find(u => u.id === unitId);

    try {
      setIsSubmitting(true);
      console.log(`Updating unit ${unitId} with data:`, unitData);

      // Optimistically update the unit in local state and recalculate stats
      setProperty(prev => {
        const updatedUnits = prev.units.map(unit =>
          unit.id === unitId
            ? { ...unit, ...unitData, lease: unit.lease } // Preserve lease data
            : unit
        );

        // Recalculate monthly revenue if rent changed for rented units
        let newStats = prev.stats;
        if (prev.stats && originalUnit && 'monthly_rent' in unitData && originalUnit.is_rented) {
          const oldRent = parseFloat(originalUnit.monthly_rent || 0);
          const newRent = parseFloat(unitData.monthly_rent || 0);
          const rentDifference = newRent - oldRent;

          newStats = {
            ...prev.stats,
            monthly_revenue: (parseFloat(prev.stats.monthly_revenue) + rentDifference).toFixed(2)
          };
        }

        return {
          ...prev,
          units: updatedUnits,
          stats: newStats
        };
      });

      // Close modal immediately for better UX
      setIsEditModalOpen(false);
      setUnitToEdit(null);

      // Call API to update the unit
      const result = await updateUnit(unitId, unitData);

      // Show success notification
      toast.success("Unit updated successfully");

      // Refresh property data in the background for consistency
      loadProperty();

      return result;
    } catch (error) {
      console.error("Error updating unit:", error);

      // Rollback to original state on error
      setProperty(originalProperty);

      // Display a more user-friendly error
      const errorMessage = error.message || "Failed to update unit";
      toast.error(errorMessage);

      // Re-throw so the modal can handle display of the error
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  // Function to handle assign tenant action
  const handleAssignTenant = (unit) => {
    setCurrentUnit(unit);
    setIsAssignModalOpen(true);
  };

  // Function to handle view lease action
  const handleViewLease = (unitId) => {
    // Navigate to the leases page with the unit filter
    navigate(`/leases?unit=${unitId}`);
  };

  // Function to refresh data after tenant assignment
  const handleTenantAssigned = async (createdLease) => {
    console.log(
      "[PropertyDetail] handleTenantAssigned called with lease:",
      createdLease
    );

    // Show success notification immediately
    toast.success("Lease created and tenant assigned successfully");

    // Refresh property data from server to ensure consistency
    await loadProperty();
  };

  // Close the assign tenant modal
  const handleCloseAssignModal = () => {
    setIsAssignModalOpen(false);
    setCurrentUnit(null);
  };

  // Close the create modal
  const handleCloseCreateModal = () => {
    setIsCreateModalOpen(false);
  };

  // Close the edit modal
  const handleCloseEditModal = () => {
    setIsEditModalOpen(false);
    setUnitToEdit(null);
  };

  const handleToggleBulkMode = () => {
    setBulkMode(!bulkMode);
    setSelectedUnits([]);
  };

  const handleUnitSelect = (unitId) => {
    // Find the unit to check if it's occupied
    const unit = property?.units?.find(u => u.id === unitId);
    
    // Prevent selection of occupied units
    if (unit?.is_rented) {
      toast.warning("Cannot select occupied units for bulk assignment");
      return;
    }

    setSelectedUnits(prev => {
      if (prev.includes(unitId)) {
        return prev.filter(id => id !== unitId);
      } else {
        return [...prev, unitId];
      }
    });
  };

  const handleSelectAll = () => {
    if (!property?.units) return;

    // Only select vacant units for bulk assignment
    const vacantUnitIds = property.units
      .filter(unit => !unit.is_rented)
      .map(unit => unit.id);
    
    const allVacantSelected = vacantUnitIds.every(id => selectedUnits.includes(id));

    if (allVacantSelected) {
      setSelectedUnits([]); // Deselect all
    } else {
      setSelectedUnits(vacantUnitIds); // Select all vacant units only
    }
  };

  const handleBulkAssign = () => {
    if (selectedUnits.length === 0) {
      toast.warning("Please select units to assign tenants to");
      return;
    }
    setShowBulkAssignModal(true);
  };

  const handleCSVUpload = () => {
    setShowCSVUploadModal(true);
  };

  const handleCSVUploadSuccess = (response) => {
    // Refresh property data to reflect new assignments
    loadProperty();
    setSelectedUnits([]);
  };

  const handleBulkAssignSuccess = (response) => {
    // Refresh property data to reflect new assignments
    loadProperty();
    setSelectedUnits([]);
    setShowBulkAssignModal(false);
  };

  const handleClearSelection = () => {
    setSelectedUnits([]);
  };

  const getSelectedUnitsCount = () => selectedUnits.length;
  const getVacantSelectedUnits = () => {
    if (!property?.units) return [];
    return property.units.filter(unit =>
      selectedUnits.includes(unit.id) && !unit.is_rented
    );
  };

  const getSelectedUnitObjects = () => {
    if (!property?.units) return [];
    return property.units.filter(unit => selectedUnits.includes(unit.id));
  };

  if (loading) return <LoadingSpinner message="Loading property details..." />;

  if (error)
    return (
      <div className="p-6 text-center">
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4 max-w-md mx-auto">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm leading-5 text-red-700">{error}</p>
            </div>
          </div>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 px-4 py-2 border border-transparent text-sm leading-5 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-500 focus:outline-none focus:border-blue-700 focus:shadow-outline-blue active:bg-blue-700 transition ease-in-out duration-150"
        >
          Try Again
        </button>
      </div>
    );

  if (!property)
    return <div className="p-6 text-center">Property not found.</div>;

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      {/* Breadcrumbs */}
      <div className="mb-6">
        <nav className="text-sm" aria-label="Breadcrumb">
          <ol className="list-none p-0 inline-flex space-x-2">
            <li className="flex items-center">
              <Link to="/" className="text-gray-500 hover:text-gray-700">
                <i className="fas fa-home"></i>
              </Link>
            </li>
            <li>
              <span className="text-gray-400">/</span>
            </li>
            <li className="flex items-center">
              <Link
                to="/properties"
                className="text-gray-500 hover:text-gray-700"
              >
                Properties
              </Link>
            </li>
            <li>
              <span className="text-gray-400">/</span>
            </li>
            <li className="text-gray-700 font-medium" aria-current="page">
              {property.name}
            </li>
          </ol>
        </nav>
      </div>

      {/* Notification */}
      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
      />

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard
          title="Total units"
          value={property.stats?.total_units || 0}
          icon={<UnitIcon />}
          bgColor="bg-blue-50"
          textColor="text-blue-600"
        />
        <StatCard
          title="Vacant units"
          value={property.stats?.vacant_units || 0}
          icon={<VacantIcon />}
          bgColor="bg-yellow-50"
          textColor="text-yellow-600"
        />
        <StatCard
          title="Monthly Revenue"
          value={formatCurrency(property.stats?.monthly_revenue || 0)}
          icon={<RevenueIcon />}
          bgColor="bg-green-50"
          textColor="text-green-600"
        />
      </div>

      {/* Units Section */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200">
          <div className="flex justify-between items-center mb-4">
            <div className="w-1/3"></div>
            <h2 className="text-lg font-medium text-center text-gray-800 w-1/3">
              Units
            </h2>
            <div className="w-1/3 flex justify-end items-center gap-3">
              {!bulkMode && (
                <button
                  onClick={handleCSVUpload}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
                >
                  <i className="fas fa-table text-xs"></i>
                  CSV Upload
                </button>
              )}
              <button
                onClick={handleToggleBulkMode}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${bulkMode
                  ? "bg-orange-100 text-orange-700 hover:bg-orange-200"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
              >
                <i className={`fas ${bulkMode ? "fa-times" : "fa-check-square"} text-xs mr-2`}></i>
                {bulkMode ? "Exit Bulk" : "Bulk Select"}
              </button>
              {!bulkMode && (
                <button
                  onClick={handleAddNewUnit}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
                >
                  <i className="fas fa-plus text-xs"></i>
                  Add a new unit
                </button>
              )}
            </div>
          </div>

          {bulkMode && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium text-blue-900">
                    {getSelectedUnitsCount()} unit{getSelectedUnitsCount() !== 1 ? 's' : ''} selected
                  </span>
                  {getSelectedUnitsCount() > 0 && (
                    <span className="text-sm text-blue-700">
                      ({getVacantSelectedUnits().length} vacant)
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  {getSelectedUnitsCount() > 0 && (
                    <>
                      <button
                        onClick={handleClearSelection}
                        className="text-sm text-blue-600 hover:text-blue-800 underline"
                      >
                        Clear Selection
                      </button>
                      <button
                        onClick={handleBulkAssign}
                        disabled={getVacantSelectedUnits().length === 0}
                        className="bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
                      >
                        <i className="fas fa-user-plus text-xs"></i>
                        Assign Tenants ({getVacantSelectedUnits().length})
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Unit Table */}
        <UnitTable
          units={property.units || []}
          loading={false} // We're already handling main page loading state
          error={null}
          onEdit={handleEditUnit}
          onDelete={handleDeleteUnit}
          onAssign={handleAssignTenant}
          onViewLease={handleViewLease}
          // Bulk selection props
          selectedUnits={selectedUnits}
          onUnitSelect={handleUnitSelect}
          onSelectAll={handleSelectAll}
          showSelection={bulkMode}
          bulkMode={bulkMode}
        />
      </div>

      {/* Create Unit Modal */}
      <NewUnitModal
        isOpen={isCreateModalOpen}
        onClose={handleCloseCreateModal}
        onSubmit={handleCreateUnit}
        propertyId={id}
        isLoading={isSubmitting}
      />

      {/* Edit Unit Modal */}
      <EditUnitModal
        isOpen={isEditModalOpen}
        onClose={handleCloseEditModal}
        onSubmit={handleUpdateUnit}
        unit={unitToEdit}
        isLoading={isSubmitting}
      />

      {/* Assign Tenant Modal */}
      {currentUnit && (
        <AssignTenantModal
          isOpen={isAssignModalOpen}
          onClose={handleCloseAssignModal}
          unit={currentUnit}
          propertyId={id}
          onSuccess={handleTenantAssigned}
        />
      )}

      {/* Bulk Assign Tenant Modal */}
      <BulkAssignTenantModal
        isOpen={showBulkAssignModal}
        onClose={() => setShowBulkAssignModal(false)}
        selectedUnits={getSelectedUnitObjects()}
        propertyId={id}
        onSuccess={handleBulkAssignSuccess}
      />

      {/* CSV Upload Modal */}
      <CSVUploadModal
        isOpen={showCSVUploadModal}
        onClose={() => setShowCSVUploadModal(false)}
        propertyId={id}
        onSuccess={handleCSVUploadSuccess}
      />
    </div>
  );
};

export default PropertyDetail;
