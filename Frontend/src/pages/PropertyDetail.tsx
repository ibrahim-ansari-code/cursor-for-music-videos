import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import * as Sentry from '@sentry/react';
import {
  fetchPropertyById,
  createUnit,
  updateUnit,
  deleteUnit,
  fetchUnitLease,
} from '../utils/api';
import StatCard from '../components/StatCard';
import UnitTable from '../components/units/UnitTable';
import NewUnitModal from '../components/units/NewUnitModal';
import EditUnitModal from '../components/units/EditUnitModal';
import PropertyDetailSkeleton from '../components/ui/skeletons/PropertyDetailSkeleton';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import AssignTenantModal from '../components/units/AssignTenantModal';
import BulkAssignTenantModal from '../components/units/BulkAssignTenantModal';
import CSVUploadModal from '../components/units/CSVUploadModal';
import type { PropertyWithUnits, UnitWithLease, PropertyStats, Unit } from '../types/unit';
import type { Lease } from '../types/lease';

/**
 * Raw unit data from API before lease enrichment
 */
interface RawUnit extends Unit {
  tenant?: {
    first_name?: string;
    last_name?: string;
    tenant_type?: string;
    company_name?: string;
  } | null;
}

/**
 * Raw property data from API before processing
 */
interface RawPropertyResponse {
  id: number;
  name: string;
  address?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  property_type?: string;
  year_built?: number;
  description?: string;
  status?: string;
  user_id?: string;
  created_at?: string;
  updated_at?: string;
  units?: RawUnit[];
  stats?: PropertyStats | null;
}

// Icons for StatCards
const UnitIcon: React.FC = () => <i className="fas fa-door-closed text-blue-600"></i>;
const VacantIcon: React.FC = () => <i className="fas fa-door-open text-yellow-600"></i>;
const RevenueIcon: React.FC = () => <i className="fas fa-dollar-sign text-green-600"></i>;

/**
 * Unit data structure for edit modal compatibility
 */
interface EditableUnit {
  id: string;
  name: string;
  floor?: number;
  description?: string;
  size?: number;
  monthly_rent?: number;
  is_rented?: boolean;
  bedrooms?: number;
  bathrooms?: number;
  unit_type_details?: Record<string, unknown>;
  tenant?: {
    first_name: string;
    last_name: string;
  };
}

/**
 * PropertyDetail Page Component
 * Displays detailed information about a property including units, stats, and management actions
 */
const PropertyDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [property, setProperty] = useState<PropertyWithUnits | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Create unit modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Edit unit modal states
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [unitToEdit, setUnitToEdit] = useState<EditableUnit | null>(null);

  // Assign tenant modal states
  const [isAssignModalOpen, setIsAssignModalOpen] = useState<boolean>(false);
  const [currentUnit, setCurrentUnit] = useState<UnitWithLease | null>(null);

  // Bulk operations state
  const [bulkMode, setBulkMode] = useState<boolean>(false);
  const [selectedUnits, setSelectedUnits] = useState<number[]>([]);
  const [showBulkAssignModal, setShowBulkAssignModal] = useState<boolean>(false);
  const [showCSVUploadModal, setShowCSVUploadModal] = useState<boolean>(false);

  const loadProperty = useCallback(async () => {
    if (!id) return;

    try {
      setLoading(true);
      setError(null);
      console.log(`Fetching property details for ID: ${id}`);
      const data = (await fetchPropertyById(id)) as RawPropertyResponse;
      console.log('Property data received:', data);

      // Fetch lease data for rented units
      let processedUnits: UnitWithLease[] | undefined;
      if (data.units && data.units.length > 0) {
        processedUnits = await Promise.all(
          data.units.map(async (unit: RawUnit): Promise<UnitWithLease> => {
            if (unit.is_rented) {
              try {
                const lease = await fetchUnitLease(unit.id);
                return { ...unit, lease } as UnitWithLease;
              } catch (leaseError) {
                // Log to Sentry for monitoring - this shouldn't happen in normal operation
                Sentry.captureException(leaseError, {
                  tags: {
                    component: 'PropertyDetail',
                    action: 'fetch_unit_lease',
                    unitId: String(unit.id),
                  },
                  contexts: {
                    business: {
                      feature: 'property_management',
                      operation: 'lease_enrichment',
                    },
                  },
                });
                // Set lease to null to indicate fetch completed but no lease found
                // This prevents the UI from showing "Loading..." indefinitely
                return { ...unit, lease: null } as UnitWithLease;
              }
            }
            return { ...unit, lease: null } as UnitWithLease;
          })
        );
      }

      const propertyWithUnits: PropertyWithUnits = {
        ...data,
        units: processedUnits,
      };

      setProperty(propertyWithUnits);
    } catch (err) {
      console.error('Error fetching property details:', err);
      setError(err instanceof Error ? err.message : 'Failed to load property details.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadProperty();
  }, [id, loadProperty]);

  const formatCurrency = (amount: number | string | null | undefined): string => {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: 'CAD',
    }).format(Number(amount) || 0);
  };

  // Function to handle unit editing
  const handleEditUnit = (unitId: number): void => {
    if (!property || !property.units) return;

    // Find the unit in the property data
    const unit = property.units.find((u) => u.id === unitId);
    if (!unit) {
      console.error(`Unit with ID ${unitId} not found`);
      return;
    }

    // Convert to EditableUnit format for the modal
    const editableUnit: EditableUnit = {
      id: String(unit.id),
      name: unit.name,
      floor: unit.floor ?? undefined,
      description: unit.description ?? undefined,
      size: unit.size ?? undefined,
      monthly_rent: unit.monthly_rent ?? undefined,
      is_rented: unit.is_rented,
      bedrooms: unit.bedrooms ?? undefined,
      bathrooms: unit.bathrooms ?? undefined,
      unit_type_details: unit.unit_type_details,
      tenant: unit.tenant
        ? {
            first_name: unit.tenant.first_name || '',
            last_name: unit.tenant.last_name || '',
          }
        : undefined,
    };

    // Set up the edit modal
    setUnitToEdit(editableUnit);
    setIsEditModalOpen(true);
  };

  // Function to handle unit deletion with optimistic updates
  const handleDeleteUnit = async (unitId: number): Promise<void> => {
    if (
      !window.confirm(
        'Are you sure you want to delete this unit? This action cannot be undone.'
      )
    ) {
      return;
    }

    // Store original property state for rollback
    const originalProperty = property;
    const unitToDelete = property?.units?.find((u) => u.id === unitId);

    try {
      setIsSubmitting(true);
      console.log(`Deleting unit with ID: ${unitId}`);

      // Optimistically remove the unit from local state
      setProperty((prev) => {
        if (!prev) return prev;
        const newStats: PropertyStats | null =
          prev.stats && unitToDelete
            ? {
                ...prev.stats,
                total_units: prev.stats.total_units - 1,
                vacant_units: unitToDelete.is_rented
                  ? prev.stats.vacant_units
                  : prev.stats.vacant_units - 1,
                occupied_units: unitToDelete.is_rented
                  ? prev.stats.occupied_units - 1
                  : prev.stats.occupied_units,
                monthly_revenue:
                  unitToDelete.is_rented && unitToDelete.monthly_rent
                    ? (
                        parseFloat(String(prev.stats.monthly_revenue)) -
                        parseFloat(String(unitToDelete.monthly_rent))
                      ).toFixed(2)
                    : prev.stats.monthly_revenue,
              }
            : null;

        return {
          ...prev,
          units: prev.units?.filter((unit) => unit.id !== unitId),
          stats: newStats,
        };
      });

      // Call API to delete the unit
      await deleteUnit(unitId);

      // Show success notification
      toast.success('Unit deleted successfully');

      // Refresh property data in the background for consistency
      loadProperty();
    } catch (err) {
      console.error('Error deleting unit:', err);

      // Rollback to original state on error
      setProperty(originalProperty);

      toast.error(err instanceof Error ? err.message : 'Failed to delete unit');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddNewUnit = (): void => {
    // Open create modal
    setIsCreateModalOpen(true);
  };

  // Function to handle unit creation with optimistic updates
  const handleCreateUnit = async (
    propertyId: string,
    unitData: unknown
  ): Promise<unknown> => {
    try {
      setIsSubmitting(true);
      console.log('Creating new unit with data:', unitData);

      // Call API to create the unit
      const result = await createUnit(Number(propertyId), unitData as object);

      // Optimistically add the new unit to the property
      setProperty((prev) => {
        if (!prev) return prev;
        const newStats: PropertyStats | null = prev.stats
          ? {
              ...prev.stats,
              total_units: prev.stats.total_units + 1,
              vacant_units: prev.stats.vacant_units + 1, // New units are always vacant
            }
          : null;

        return {
          ...prev,
          units: [...(prev.units || []), result as UnitWithLease],
          stats: newStats,
        };
      });

      // Show success notification
      toast.success('Unit created successfully');

      // Close modal
      setIsCreateModalOpen(false);

      // Refresh property data in the background for consistency
      loadProperty();

      return result;
    } catch (err) {
      console.error('Error creating unit:', err);

      // Display a more user-friendly error
      const errorMessage = err instanceof Error ? err.message : 'Failed to create unit';
      toast.error(errorMessage);

      // Re-throw so the modal can handle display of the error
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  // Function to handle unit update with optimistic updates
  const handleUpdateUnit = async (unitId: string, unitData: unknown): Promise<unknown> => {
    // Store original property state for rollback
    const originalProperty = property;
    const numericUnitId = parseInt(unitId, 10);
    const originalUnit = property?.units?.find((u) => u.id === numericUnitId);

    try {
      setIsSubmitting(true);
      console.log(`Updating unit ${unitId} with data:`, unitData);

      const typedUnitData = unitData as Record<string, unknown>;

      // Optimistically update the unit in local state and recalculate stats
      setProperty((prev) => {
        if (!prev) return prev;

        const updatedUnits = prev.units?.map((unit) =>
          unit.id === numericUnitId
            ? ({ ...unit, ...typedUnitData, lease: unit.lease } as UnitWithLease)
            : unit
        );

        // Recalculate monthly revenue if rent changed for rented units
        let newStats = prev.stats;
        if (
          prev.stats &&
          originalUnit &&
          'monthly_rent' in typedUnitData &&
          originalUnit.is_rented
        ) {
          const oldRent = parseFloat(String(originalUnit.monthly_rent || 0));
          const newRent = parseFloat(String(typedUnitData.monthly_rent || 0));
          const rentDifference = newRent - oldRent;

          newStats = {
            ...prev.stats,
            monthly_revenue: (
              parseFloat(String(prev.stats.monthly_revenue)) + rentDifference
            ).toFixed(2),
          };
        }

        return {
          ...prev,
          units: updatedUnits,
          stats: newStats,
        };
      });

      // Close modal immediately for better UX
      setIsEditModalOpen(false);
      setUnitToEdit(null);

      // Call API to update the unit
      const result = await updateUnit(numericUnitId, unitData as object);

      // Show success notification
      toast.success('Unit updated successfully');

      // Refresh property data in the background for consistency
      loadProperty();

      return result;
    } catch (err) {
      console.error('Error updating unit:', err);

      // Rollback to original state on error
      setProperty(originalProperty);

      // Display a more user-friendly error
      const errorMessage = err instanceof Error ? err.message : 'Failed to update unit';
      toast.error(errorMessage);

      // Re-throw so the modal can handle display of the error
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  // Function to handle assign tenant action
  const handleAssignTenant = (unit: UnitWithLease): void => {
    setCurrentUnit(unit);
    setIsAssignModalOpen(true);
  };

  // Function to handle view lease action
  const handleViewLease = (unitId: number): void => {
    // Navigate to the leases page with the unit filter
    navigate(`/leases?unit=${unitId}`);
  };

  // Function to refresh data after tenant assignment
  const handleTenantAssigned = async (createdLease: Lease): Promise<void> => {
    console.log('[PropertyDetail] handleTenantAssigned called with lease:', createdLease);

    // Show success notification immediately
    toast.success('Lease created and tenant assigned successfully');

    // Refresh property data from server to ensure consistency
    await loadProperty();
  };

  // Close the assign tenant modal
  const handleCloseAssignModal = (): void => {
    setIsAssignModalOpen(false);
    setCurrentUnit(null);
  };

  // Close the create modal
  const handleCloseCreateModal = (): void => {
    setIsCreateModalOpen(false);
  };

  // Close the edit modal
  const handleCloseEditModal = (): void => {
    setIsEditModalOpen(false);
    setUnitToEdit(null);
  };

  const handleToggleBulkMode = (): void => {
    setBulkMode(!bulkMode);
    setSelectedUnits([]);
  };

  const handleUnitSelect = (unitId: number): void => {
    // Find the unit to check if it's occupied
    const unit = property?.units?.find((u) => u.id === unitId);

    // Prevent selection of occupied units
    if (unit?.is_rented) {
      toast.warning('Cannot select occupied units for bulk assignment');
      return;
    }

    setSelectedUnits((prev) => {
      if (prev.includes(unitId)) {
        return prev.filter((id) => id !== unitId);
      } else {
        return [...prev, unitId];
      }
    });
  };

  const handleSelectAll = (): void => {
    if (!property?.units) return;

    // Only select vacant units for bulk assignment
    const vacantUnitIds = property.units.filter((unit) => !unit.is_rented).map((unit) => unit.id);

    const allVacantSelected = vacantUnitIds.every((id) => selectedUnits.includes(id));

    if (allVacantSelected) {
      setSelectedUnits([]); // Deselect all
    } else {
      setSelectedUnits(vacantUnitIds); // Select all vacant units only
    }
  };

  const handleBulkAssign = (): void => {
    if (selectedUnits.length === 0) {
      toast.warning('Please select units to assign tenants to');
      return;
    }
    setShowBulkAssignModal(true);
  };

  const handleCSVUpload = (): void => {
    setShowCSVUploadModal(true);
  };

  const handleCSVUploadSuccess = (): void => {
    // Refresh property data to reflect new assignments
    loadProperty();
    setSelectedUnits([]);
  };

  const handleBulkAssignSuccess = (): void => {
    // Refresh property data to reflect new assignments
    loadProperty();
    setSelectedUnits([]);
    setShowBulkAssignModal(false);
  };

  const handleClearSelection = (): void => {
    setSelectedUnits([]);
  };

  const getSelectedUnitsCount = (): number => selectedUnits.length;

  const getVacantSelectedUnits = (): UnitWithLease[] => {
    if (!property?.units) return [] as UnitWithLease[];
    return property.units.filter((unit) => selectedUnits.includes(unit.id) && !unit.is_rented);
  };

  const getSelectedUnitObjects = (): UnitWithLease[] => {
    if (!property?.units) return [] as UnitWithLease[];
    return property.units.filter((unit) => selectedUnits.includes(unit.id));
  };

  if (loading) return <PropertyDetailSkeleton />;

  if (error)
    return (
      <div className="p-6 text-center bg-white dark:bg-gray-800 min-h-screen transition-colors duration-300">
        <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 dark:border-red-400 p-4 mb-4 max-w-md mx-auto transition-colors duration-300">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400 dark:text-red-500"
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
              <p className="text-sm leading-5 text-red-700 dark:text-red-300 transition-colors duration-300">
                {error}
              </p>
            </div>
          </div>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 px-4 py-2 border border-transparent text-sm leading-5 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-500 dark:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:border-blue-700 focus:shadow-outline-blue active:bg-blue-700 transition ease-in-out duration-150"
        >
          Try Again
        </button>
      </div>
    );

  if (!property)
    return (
      <div className="p-6 text-center dark:text-gray-100">Property not found.</div>
    );

  return (
    <div className="p-6 max-w-[1600px] mx-auto bg-white dark:bg-gray-900 min-h-screen transition-colors duration-300">
      {/* Breadcrumbs */}
      <div className="mb-6">
        <nav className="text-sm" aria-label="Breadcrumb">
          <ol className="list-none p-0 inline-flex space-x-2">
            <li className="flex items-center">
              <Link
                to="/"
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 transition-colors duration-300"
              >
                <i className="fas fa-home"></i>
              </Link>
            </li>
            <li>
              <span className="text-gray-400 dark:text-gray-500">/</span>
            </li>
            <li className="flex items-center">
              <Link
                to="/properties"
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 transition-colors duration-300"
              >
                Properties
              </Link>
            </li>
            <li>
              <span className="text-gray-400 dark:text-gray-500">/</span>
            </li>
            <li
              className="text-gray-700 dark:text-gray-200 font-medium transition-colors duration-300"
              aria-current="page"
            >
              {property.name}
            </li>
          </ol>
        </nav>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard
          title="Total units"
          value={property.stats?.total_units || 0}
          icon={<UnitIcon />}
          bgColor="bg-blue-50 dark:bg-blue-900/20"
          textColor="text-blue-600 dark:text-blue-400"
          onClick={undefined}
        />
        <StatCard
          title="Vacant units"
          value={property.stats?.vacant_units || 0}
          icon={<VacantIcon />}
          bgColor="bg-yellow-50 dark:bg-yellow-900/20"
          textColor="text-yellow-600 dark:text-yellow-400"
          onClick={undefined}
        />
        <StatCard
          title="Monthly Revenue"
          value={formatCurrency(property.stats?.monthly_revenue || 0)}
          icon={<RevenueIcon />}
          bgColor="bg-green-50 dark:bg-green-900/20"
          textColor="text-green-600 dark:text-green-400"
          onClick={undefined}
        />
      </div>

      {/* Units Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex justify-between items-center mb-4">
            <div className="w-1/3"></div>
            <h2 className="text-lg font-medium text-center text-gray-800 dark:text-gray-200 w-1/3">
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
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  bulkMode
                    ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <i
                  className={`fas ${bulkMode ? 'fa-times' : 'fa-check-square'} text-xs mr-2`}
                ></i>
                {bulkMode ? 'Exit Bulk' : 'Bulk Select'}
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
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 transition-colors duration-300">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium text-blue-900 dark:text-blue-100 transition-colors duration-300">
                    {getSelectedUnitsCount()} unit{getSelectedUnitsCount() !== 1 ? 's' : ''}{' '}
                    selected
                  </span>
                  {getSelectedUnitsCount() > 0 && (
                    <span className="text-sm text-blue-700 dark:text-blue-300 transition-colors duration-300">
                      ({getVacantSelectedUnits().length} vacant)
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  {getSelectedUnitsCount() > 0 && (
                    <>
                      <button
                        onClick={handleClearSelection}
                        className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline transition-colors duration-300"
                      >
                        Clear Selection
                      </button>
                      <button
                        onClick={handleBulkAssign}
                        disabled={getVacantSelectedUnits().length === 0}
                        className="bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors duration-300"
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
          loading={false}
          error={null}
          onEdit={handleEditUnit}
          onDelete={handleDeleteUnit}
          onAssign={handleAssignTenant}
          onViewLease={handleViewLease}
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
        propertyId={id || ''}
        propertyType={property?.property_type}
        isLoading={isSubmitting}
      />

      {/* Edit Unit Modal */}
      <EditUnitModal
        isOpen={isEditModalOpen}
        onClose={handleCloseEditModal}
        onSubmit={handleUpdateUnit}
        unit={unitToEdit}
        propertyType={property?.property_type}
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
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore - BulkAssignTenantModal is JSX without type definitions
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
