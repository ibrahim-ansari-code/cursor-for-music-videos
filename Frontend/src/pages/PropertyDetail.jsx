import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchPropertyById, createUnit, updateUnit, deleteUnit } from '../utils/api';
import StatCard from '../components/StatCard'; // Import StatCard
import UnitTable from '../components/UnitTable'; // Import UnitTable
import NewUnitModal from '../components/NewUnitModal'; // Import NewUnitModal
import AssignTenantModal from '../components/AssignTenantModal'; // Import AssignTenantModal

// Icons for StatCards
const UnitIcon = () => <i className="fas fa-door-closed text-blue-600"></i>;
const VacantIcon = () => <i className="fas fa-door-open text-yellow-600"></i>;
const RevenueIcon = () => <i className="fas fa-dollar-sign text-green-600"></i>;

const PropertyDetail = () => {
  const { id } = useParams();
  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Unit modal states
  const [isUnitModalOpen, setIsUnitModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState(null);
  
  // Assign tenant modal states
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [currentUnit, setCurrentUnit] = useState(null);
  
  // Edit unit states
  const [unitModalMode, setUnitModalMode] = useState('create');
  const [unitInitialData, setUnitInitialData] = useState(null);

  const [stats, setStats] = useState({
    totalUnits: 0,
    vacantUnits: 0,
    monthlyRevenue: 0,
  });

  useEffect(() => {
    loadProperty();
  }, [id]);

  const loadProperty = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log(`Fetching property details for ID: ${id}`);
      const data = await fetchPropertyById(id);
      console.log('Property data received:', data);
      setProperty(data);

      // Calculate stats based on the fetched units
      if (data && data.units) {
        const totalUnits = data.units.length;
        const vacantUnits = data.units.filter(unit => !unit.is_rented).length;
        const monthlyRevenue = data.units
          .filter(unit => unit.is_rented && unit.monthly_rent)
          .reduce((sum, unit) => sum + unit.monthly_rent, 0);
        
        setStats({ totalUnits, vacantUnits, monthlyRevenue });
      }

    } catch (err) {
      console.error('Error fetching property details:', err);
      setError(err.message || 'Failed to load property details.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount || 0);
  };

  // Function to handle unit editing
  const handleEditUnit = (unitId) => {
    if (!property || !property.units) return;
    
    // Find the unit in the property data
    const unitToEdit = property.units.find(unit => unit.id === unitId);
    if (!unitToEdit) {
      console.error(`Unit with ID ${unitId} not found`);
      return;
    }
    
    // Set up the edit mode
    setUnitModalMode('edit');
    setUnitInitialData({
      name: unitToEdit.name,
      floor: unitToEdit.floor,
      monthly_rent: unitToEdit.monthly_rent || '',
      is_rented: unitToEdit.is_rented
    });
    setCurrentUnit(unitToEdit);
    setIsUnitModalOpen(true);
  };

  // Function to handle unit deletion
  const handleDeleteUnit = async (unitId) => {
    if (!window.confirm('Are you sure you want to delete this unit? This action cannot be undone.')) {
      return;
    }
    
    try {
      setIsSubmitting(true);
      console.log(`Deleting unit with ID: ${unitId}`);
      
      // Call API to delete the unit
      await deleteUnit(unitId);
      
      // Show success notification
      setNotification({
        type: 'success',
        message: 'Unit deleted successfully'
      });
      
      // Refresh property data
      await loadProperty();
      
      // Clear notification after 3 seconds
      setTimeout(() => {
        setNotification(null);
      }, 3000);
    } catch (error) {
      console.error('Error deleting unit:', error);
      setNotification({
        type: 'error',
        message: error.message || 'Failed to delete unit'
      });
      
      // Clear notification after 3 seconds
      setTimeout(() => {
        setNotification(null);
      }, 3000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddNewUnit = () => {
    // Reset to create mode
    setUnitModalMode('create');
    setUnitInitialData(null);
    setCurrentUnit(null);
    setIsUnitModalOpen(true);
  };

  // Function to handle unit creation or update
  const handleUnitSubmit = async (propertyId, unitData) => {
    try {
      setIsSubmitting(true);
      let result;
      
      // If we're in edit mode and have a current unit
      if (unitModalMode === 'edit' && currentUnit) {
        console.log(`Updating unit ${currentUnit.id} with data:`, unitData);
        
        // Call API to update the unit
        result = await updateUnit(currentUnit.id, unitData);
        
        // Show success notification
        setNotification({
          type: 'success',
          message: 'Unit updated successfully'
        });
      } else {
        // We're in create mode
        console.log('Creating new unit with data:', unitData);
        
        // Call API to create the unit
        result = await createUnit(propertyId, unitData);
        
        // Show success notification
        setNotification({
          type: 'success',
          message: 'Unit created successfully'
        });
      }
      
      // Reset modal state
      setUnitModalMode('create');
      setUnitInitialData(null);
      setCurrentUnit(null);
      setIsUnitModalOpen(false);
      
      // Refresh property data to include the new/updated unit
      await loadProperty();
      
      // Clear notification after 3 seconds
      setTimeout(() => {
        setNotification(null);
      }, 3000);
      
      return result;
    } catch (error) {
      console.error('Error saving unit:', error);
      
      // Display a more user-friendly error
      const errorMessage = error.message || 'Failed to save unit';
      setNotification({
        type: 'error',
        message: errorMessage
      });
      
      // Clear notification after 3 seconds
      setTimeout(() => {
        setNotification(null);
      }, 3000);
      
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

  // Function to refresh data after tenant assignment
  const handleTenantAssigned = async () => {
    // Show success notification
    setNotification({
      type: 'success',
      message: 'Tenant assigned successfully'
    });
    
    // Refresh property data
    await loadProperty();
    
    // Clear notification after 3 seconds
    setTimeout(() => {
      setNotification(null);
    }, 3000);
  };

  // Close the assign tenant modal
  const handleCloseAssignModal = () => {
    setIsAssignModalOpen(false);
    setCurrentUnit(null);
  };

  // Close the unit modal
  const handleCloseUnitModal = () => {
    setIsUnitModalOpen(false);
    setCurrentUnit(null);
    setUnitInitialData(null);
  };

  if (loading) return (
    <div className="p-6 text-center">
      <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
      <p className="text-gray-600">Loading property details...</p>
    </div>
  );
  
  if (error) return (
    <div className="p-6 text-center">
      <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4 max-w-md mx-auto">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
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
  
  if (!property) return <div className="p-6 text-center">Property not found.</div>;

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
              <Link to="/properties" className="text-gray-500 hover:text-gray-700">Properties</Link>
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
      {notification && (
        <div className={`mb-6 p-4 rounded-lg ${notification.type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'}`}>
          <div className="flex items-center">
            <div className="flex-shrink-0">
              {notification.type === 'success' ? (
                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium">{notification.message}</p>
            </div>
          </div>
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard 
          title="Total units" 
          value={stats.totalUnits} 
          icon={<UnitIcon />} 
          bgColor="bg-blue-50"
          textColor="text-blue-600"
        />
        <StatCard 
          title="Vacant units" 
          value={stats.vacantUnits} 
          icon={<VacantIcon />} 
          bgColor="bg-yellow-50"
          textColor="text-yellow-600"
        />
        <StatCard 
          title="Monthly Revenue" 
          value={formatCurrency(stats.monthlyRevenue)} 
          icon={<RevenueIcon />} 
          bgColor="bg-green-50"
          textColor="text-green-600"
        />
      </div>

      {/* Units Section */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
          <div className="w-1/3">
            {/* Left spacer */}
          </div>
          <h2 className="text-lg font-medium text-center text-gray-800 w-1/3">Units</h2>
          <div className="w-1/3 flex justify-end">
            <button
              onClick={handleAddNewUnit}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
            >
              <i className="fas fa-plus text-xs"></i>
              Add a new unit
            </button>
          </div>
        </div>

        {/* Unit Table */}
        <UnitTable 
          units={property.units || []} 
          loading={false} // We're already handling main page loading state
          error={null}
          onEdit={handleEditUnit} 
          onDelete={handleDeleteUnit}
          onAssign={handleAssignTenant} 
        />
      </div>

      {/* Unit Modal - Used for both creating and editing */}
      <NewUnitModal
        isOpen={isUnitModalOpen}
        onClose={handleCloseUnitModal}
        onSubmit={handleUnitSubmit}
        propertyId={id}
        isLoading={isSubmitting}
        initialData={unitInitialData}
        mode={unitModalMode}
      />

      {/* Assign Tenant Modal */}
      {currentUnit && (
        <AssignTenantModal
          isOpen={isAssignModalOpen}
          onClose={handleCloseAssignModal}
          onSubmit={handleTenantAssigned}
          propertyId={id}
          unitId={currentUnit.id}
          unitName={currentUnit.name}
          isLoading={isSubmitting}
        />
      )}
    </div>
  );
};

export default PropertyDetail; 