import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchProperties, createProperty, deleteProperty } from '../utils/api';
import NewPropertyModal from '../components/NewPropertyModal';

const StatusCard = ({ title, count, bgColor = 'bg-white', textColor = 'text-gray-900', onClick }) => (
  <div 
    className={`${bgColor} rounded-lg p-6 shadow-sm cursor-pointer hover:shadow-md transition-shadow`}
    onClick={onClick}
  >
    <h3 className="text-sm font-medium text-gray-500">{title}</h3>
    <p className={`mt-2 text-3xl font-semibold ${textColor}`}>{count}</p>
  </div>
);

const StatusBadge = ({ status }) => {
  const statusStyles = {
    active: 'bg-green-50 text-green-700',
    maintenance: 'bg-orange-50 text-orange-700',
    vacant: 'bg-yellow-50 text-yellow-700',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyles[status.toLowerCase()] || 'bg-gray-100 text-gray-800'}`}>
      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current"></span>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

const PropertyTable = ({ properties, loading, error, onDelete }) => {
  const navigate = useNavigate();
  
  if (loading) return (
    <div className="p-8 text-center">
      <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
      <p className="text-gray-600">Loading properties...</p>
    </div>
  );
  
  if (error) return (
    <div className="p-8 text-center">
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
  
  if (!properties || properties.length === 0) {
    return <div className="p-4 text-center text-gray-500">No properties found. Create your first property!</div>;
  }

  // Capitalize first letter of string
  const capitalize = (str) => {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  };

  // Generate image placeholder based on property name
  const getImageInitial = (name) => {
    if (!name) return '';
    return name.charAt(0).toUpperCase();
  };

  const handleDelete = (e, propertyId) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this property?')) {
      onDelete(propertyId);
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Property
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Address
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Added
            </th>
            <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {properties.map((property) => (
            <tr 
              key={property.id}
              className="hover:bg-gray-50 cursor-pointer transition-colors"
              onClick={() => navigate(`/properties/${property.id}`)}
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  <div className="flex-shrink-0 h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 font-bold">
                    {getImageInitial(property.name)}
                  </div>
                  <div className="ml-4">
                    <div className="text-sm font-medium text-gray-900">{property.name}</div>
                  </div>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {capitalize(property.property_type)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {property.address}, {property.city}, {property.state}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <StatusBadge status={property.status || 'active'} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {new Date(property.created_at).toLocaleDateString()}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/properties/${property.id}`);
                    }}
                    className="text-indigo-600 hover:text-indigo-900"
                  >
                    View
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      // Edit functionality will be added later
                    }}
                    className="text-blue-600 hover:text-blue-900"
                  >
                    Edit
                  </button>
                  <button
                    onClick={(e) => handleDelete(e, property.id)}
                    className="text-red-600 hover:text-red-900"
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const Properties = () => {
  const navigate = useNavigate();
  const [properties, setProperties] = useState([]);
  const [filteredProperties, setFilteredProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusFilter, setStatusFilter] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusCounts, setStatusCounts] = useState({
    active: 0,
    maintenance: 0,
    vacant: 0,
    total: 0
  });
  const [isDeleting, setIsDeleting] = useState(false);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    fetchPropertiesData();
  }, []);

  useEffect(() => {
    // Filter properties based on search term and status filter
    if (!properties.length) return;

    let result = [...properties];

    if (statusFilter) {
      result = result.filter(p => p.status === statusFilter);
    }

    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      result = result.filter(p => 
        p.name.toLowerCase().includes(term) || 
        p.address.toLowerCase().includes(term) || 
        p.city.toLowerCase().includes(term) ||
        p.property_type.toLowerCase().includes(term)
      );
    }

    setFilteredProperties(result);
  }, [properties, statusFilter, searchTerm]);

  const fetchPropertiesData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Fetching properties...');
      const response = await fetchProperties();
      console.log('Properties response:', response);
      
      setProperties(response);
      setFilteredProperties(response);
      
      // Calculate status counts
      const counts = response.reduce((acc, property) => {
        acc.total++;
        const status = property.status || 'active';
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      }, {
        active: 0,
        maintenance: 0,
        vacant: 0,
        total: 0
      });
      
      setStatusCounts(counts);
    } catch (err) {
      console.error('Error fetching properties:', err);
      setError(err.message || 'Failed to load properties. Please try again.');
      // If fetch fails, set empty arrays to avoid undefined errors
      setProperties([]);
      setFilteredProperties([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProperty = async (propertyData) => {
    setIsSubmitting(true);
    try {
      const newProperty = await createProperty(propertyData);
      
      // Update properties and counts
      setProperties(prev => [newProperty, ...prev]);
      setStatusCounts(prev => ({
        ...prev,
        total: prev.total + 1,
        [newProperty.status]: (prev[newProperty.status] || 0) + 1
      }));
      
      setIsModalOpen(false);
    } catch (error) {
      console.error('Error creating property:', error);
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStatusCardClick = (status) => {
    setStatusFilter(status === statusFilter ? null : status);
  };

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
  };

  const clearFilters = () => {
    setStatusFilter(null);
    setSearchTerm('');
  };

  const handleDeleteProperty = async (propertyId) => {
    setIsDeleting(true);
    try {
      // The delete endpoint returns 204 No Content which doesn't have a JSON body
      // so we need to handle it differently
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/properties/${propertyId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok && response.status !== 204) {
        throw new Error(`Failed to delete property: ${response.status}`);
      }
      
      // Update properties list after successful deletion
      setProperties(prev => prev.filter(p => p.id !== propertyId));
      
      // Update status counts
      const deletedProperty = properties.find(p => p.id === propertyId);
      if (deletedProperty) {
        setStatusCounts(prev => ({
          ...prev,
          total: prev.total - 1,
          [deletedProperty.status]: prev[deletedProperty.status] - 1
        }));
      }

      // Show success notification
      setNotification({
        type: 'success',
        message: 'Property was successfully deleted'
      });

      // Clear notification after 3 seconds
      setTimeout(() => {
        setNotification(null);
      }, 3000);
    } catch (error) {
      console.error('Error deleting property:', error);
      
      // Show error notification
      setNotification({
        type: 'error',
        message: 'Failed to delete property. Please try again.'
      });

      // Clear notification after 3 seconds
      setTimeout(() => {
        setNotification(null);
      }, 3000);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Properties</h1>
        <button
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          onClick={() => setIsModalOpen(true)}
        >
          <i className="fas fa-plus"></i>
          Add new property
        </button>
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

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatusCard 
          title="Active" 
          count={statusCounts.active} 
          bgColor={statusFilter === 'active' ? 'bg-green-100' : 'bg-green-50'} 
          textColor="text-green-600"
          onClick={() => handleStatusCardClick('active')}
        />
        <StatusCard 
          title="In-maintenance" 
          count={statusCounts.maintenance} 
          bgColor={statusFilter === 'maintenance' ? 'bg-orange-100' : 'bg-orange-50'} 
          textColor="text-orange-600"
          onClick={() => handleStatusCardClick('maintenance')}
        />
        <StatusCard 
          title="Vacant" 
          count={statusCounts.vacant} 
          bgColor={statusFilter === 'vacant' ? 'bg-yellow-100' : 'bg-yellow-50'} 
          textColor="text-yellow-600"
          onClick={() => handleStatusCardClick('vacant')}
        />
        <StatusCard 
          title="Total" 
          count={statusCounts.total}
          onClick={clearFilters}
        />
      </div>

      {/* Properties Table */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <i className="fas fa-search text-gray-400"></i>
              </div>
              <input
                type="text"
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-600 focus:border-blue-600 sm:text-sm"
                placeholder="Search properties..."
                value={searchTerm}
                onChange={handleSearch}
              />
            </div>
            <div className="flex items-center gap-4">
              {statusFilter && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">Filtered by:</span>
                  <StatusBadge status={statusFilter} />
                  <button 
                    onClick={clearFilters}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    <i className="fas fa-times-circle"></i>
                  </button>
                </div>
              )}
              <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                <i className="fas fa-filter mr-2"></i>
                Filter
              </button>
              <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                <i className="fas fa-sort mr-2"></i>
                Sort
              </button>
            </div>
          </div>
        </div>
        <PropertyTable 
          properties={filteredProperties} 
          loading={loading || isDeleting} 
          error={error}
          onDelete={handleDeleteProperty} 
        />
      </div>

      {/* New Property Modal */}
      <NewPropertyModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateProperty}
        isLoading={isSubmitting}
      />
    </div>
  );
};

export default Properties; 