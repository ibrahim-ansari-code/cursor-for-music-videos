import React, { useState, useEffect, useRef, useMemo, MouseEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchPropertyById } from '../utils/api';
import NewPropertyModal from '../components/properties/NewPropertyModal';
import { PropertiesTableSkeleton } from '../components/ui/skeletons';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import useProperties from '../hooks/useProperties';
import { useDeleteProperty } from '../hooks/usePropertiesMutations';
import { preloadGoogleMaps } from '../utils/googleMapsLoader';
import { Property, PropertyStatus } from '../types/property';

// Utility functions
const capitalize = (str: string): string => {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
};

// Component Props Types
interface StatusCardProps {
  title: string;
  count: number;
  bgColor?: string;
  textColor?: string;
  onClick: () => void;
  icon: React.ReactNode;
  isLoading?: boolean;
}

interface StatusBadgeProps {
  status: string;
}

interface PropertyTableProps {
  properties: Property[];
  loading: boolean;
  error: string | null;
  onDelete: (propertyId: number) => void;
  onEdit: (propertyId: number) => void;
}

interface FilterOptions {
  propertyType: string | null;
  status: string | null;
  dateAdded: string | null;
}

interface StatusCounts {
  ACTIVE: number;
  MAINTENANCE: number;
  VACANT: number;
  total: number;
  [key: string]: number; // Index signature for dynamic access
}

// Status Card Component
const StatusCard: React.FC<StatusCardProps> = ({
  title,
  count,
  bgColor = 'bg-white',
  textColor = 'text-gray-900',
  onClick,
  icon,
  isLoading = false,
}) => (
  <div
    className="bg-white overflow-hidden shadow rounded-lg cursor-pointer hover:shadow-md transition-shadow"
    onClick={onClick}
  >
    <div className="px-4 py-5 sm:p-6">
      <div className="flex items-center">
        <div className={`flex-shrink-0 ${bgColor} rounded-md p-3`}>{icon}</div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">
              {title}
            </dt>
            <dd>
              {isLoading ? (
                <div className="animate-pulse h-6 w-8 bg-gray-200 rounded"></div>
              ) : (
                <div className={`text-lg font-medium ${textColor}`}>{count}</div>
              )}
            </dd>
          </dl>
        </div>
      </div>
    </div>
  </div>
);

// Status Badge Component
const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    ACTIVE: 'bg-green-50 text-green-700',
    MAINTENANCE: 'bg-orange-50 text-orange-700',
    VACANT: 'bg-yellow-50 text-yellow-700',
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

// Property Table Component
const PropertyTable: React.FC<PropertyTableProps> = ({ 
  properties, 
  loading, 
  error, 
  onDelete, 
  onEdit 
}) => {
  const navigate = useNavigate();

  if (loading) return <PropertiesTableSkeleton rowCount={8} />;

  if (error)
    return (
      <div className="p-8 text-center">
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

  if (!properties || properties.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        No properties found. Create your first property!
      </div>
    );
  }

  // Generate image placeholder based on property name
  const getImageInitial = (name: string): string => {
    if (!name) return '';
    return name.charAt(0).toUpperCase();
  };

  const handleDelete = (e: MouseEvent<HTMLButtonElement>, propertyId: number) => {
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
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Property
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Type
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Address
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Status
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Added
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
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
                <div className="flex items-center justify-start">
                  <div className="flex-shrink-0 h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 font-bold text-left">
                    {getImageInitial(property.name)}
                  </div>
                  <div className="ml-4">
                    <div className="text-sm font-medium text-gray-900 text-left">
                      {property.name}
                    </div>
                  </div>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                {property.property_type}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                <div
                  className="max-w-xs truncate mx-auto"
                  title={`${property.address}, ${property.city}, ${property.province}`}
                >
                  {property.address}, {property.city}, {property.province}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center">
                <div className="flex justify-center">
                  <StatusBadge status={property.status || PropertyStatus.ACTIVE} />
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                {property.created_at && new Date(property.created_at).toLocaleDateString()}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                <div className="flex justify-center space-x-3">
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
                      property.id && onEdit(property.id);
                    }}
                    className="text-blue-600 hover:text-blue-900"
                  >
                    Edit
                  </button>
                  <button
                    onClick={(e) => property.id && handleDelete(e, property.id)}
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

// Main Properties Component
const Properties: React.FC = () => {
  
  // Use standardized useProperties hook
  const { properties, loading, error } = useProperties();
  
  // Mutation hooks
  const deletePropertyMutation = useDeleteProperty();
  
  // Local UI state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentProperty, setCurrentProperty] = useState<Property | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [sortOption, setSortOption] = useState<string | null>(null);
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    propertyType: null,
    status: null,
    dateAdded: null,
  });

  // Memoized filtered and sorted properties
  const filteredProperties = useMemo(() => {
    if (!properties.length) return [];

    let result = [...properties];

    // Apply status filter from cards or dropdown
    if (statusFilter) {
      result = result.filter(
        (p) =>
          (p.status || PropertyStatus.ACTIVE).toUpperCase() === statusFilter.toUpperCase()
      );
    }

    // Apply search term filter
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(term) ||
          p.address.toLowerCase().includes(term) ||
          p.city.toLowerCase().includes(term) ||
          p.property_type.toLowerCase().includes(term)
      );
    }

    // Apply property type filter
    if (filterOptions.propertyType) {
      result = result.filter(
        (p) => p.property_type === filterOptions.propertyType
      );
    }

    // Apply status filter from dropdown (overrides card selection)
    if (filterOptions.status) {
      result = result.filter(
        (p) =>
          (p.status || PropertyStatus.ACTIVE).toUpperCase() ===
          filterOptions.status?.toUpperCase()
      );
    }

    // Apply date filter
    if (filterOptions.dateAdded) {
      const now = new Date();
      const cutoffDate = new Date();

      switch (filterOptions.dateAdded) {
        case 'last-week':
          cutoffDate.setDate(now.getDate() - 7);
          break;
        case 'last-month':
          cutoffDate.setMonth(now.getMonth() - 1);
          break;
        case 'last-year':
          cutoffDate.setFullYear(now.getFullYear() - 1);
          break;
        default:
          break;
      }

      result = result.filter((p) => 
        p.created_at && new Date(p.created_at) >= cutoffDate
      );
    }

    // Apply sorting
    if (sortOption) {
      result.sort((a, b) => {
        switch (sortOption) {
          case 'name-asc':
            return a.name.localeCompare(b.name);
          case 'name-desc':
            return b.name.localeCompare(a.name);
          case 'type-asc':
            return a.property_type.localeCompare(b.property_type);
          case 'type-desc':
            return b.property_type.localeCompare(a.property_type);
          case 'status-asc':
            return (a.status || PropertyStatus.ACTIVE)
              .toUpperCase()
              .localeCompare((b.status || PropertyStatus.ACTIVE).toUpperCase());
          case 'status-desc':
            return (b.status || PropertyStatus.ACTIVE)
              .toUpperCase()
              .localeCompare((a.status || PropertyStatus.ACTIVE).toUpperCase());
          case 'date-asc':
            return (a.created_at ? new Date(a.created_at).getTime() : 0) - 
                   (b.created_at ? new Date(b.created_at).getTime() : 0);
          case 'date-desc':
            return (b.created_at ? new Date(b.created_at).getTime() : 0) - 
                   (a.created_at ? new Date(a.created_at).getTime() : 0);
          default:
            return 0;
        }
      });
    }

    return result;
  }, [properties, statusFilter, searchTerm, filterOptions, sortOption]);

  // Memoized status counts
  const statusCounts = useMemo(() => {
    return filteredProperties.reduce<StatusCounts>(
      (acc, property) => {
        acc.total++;
        const status = (property.status || PropertyStatus.ACTIVE).toUpperCase();
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      },
      {
        ACTIVE: 0,
        MAINTENANCE: 0,
        VACANT: 0,
        total: 0,
      }
    );
  }, [filteredProperties]);

  // Refs for clicking outside filter/sort menus
  const filterMenuRef = useRef<HTMLDivElement>(null);
  const sortMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Close menus when clicking outside
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node;
      if (
        filterMenuRef.current &&
        !filterMenuRef.current.contains(target)
      ) {
        setShowFilterMenu(false);
      }
      if (sortMenuRef.current && !sortMenuRef.current.contains(target)) {
        setShowSortMenu(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside as any);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside as any);
    };
  }, []);


  const handleEditProperty = async (propertyId: number) => {
    try {
      const property = await fetchPropertyById(propertyId);
      setCurrentProperty(property);
      setIsEditing(true);
      setIsModalOpen(true);
    } catch (error) {
      console.error('Error fetching property details:', error);
      toast.error('Failed to load property details');
    }
  };

  const handleStatusCardClick = (status: string) => {
    setStatusFilter(
      status.toUpperCase() === statusFilter ? null : status.toUpperCase()
    );
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const clearFilters = () => {
    setFilterOptions({
      propertyType: null,
      status: null,
      dateAdded: null,
    });
    setStatusFilter(null);
    setSearchTerm('');
    setSortOption(null);
  };

  const handleDeleteProperty = async (propertyId: number) => {
    try {
      console.log(`[handleDeleteProperty] Deleting property ID: ${propertyId}`);
      await deletePropertyMutation.mutateAsync(propertyId);
      toast.success('Property was successfully deleted');
    } catch (error: any) {
      console.error('Error deleting property:', error);
      toast.error(error.message || 'Failed to delete property. Please try again.');
    }
  };

  const handleFilterToggle = () => {
    setShowFilterMenu(!showFilterMenu);
    setShowSortMenu(false);
  };

  const handleSortToggle = () => {
    setShowSortMenu(!showSortMenu);
    setShowFilterMenu(false);
  };

  const handleFilterSelect = (type: keyof FilterOptions, value: string) => {
    setFilterOptions((prev) => ({
      ...prev,
      [type]: value === prev[type] ? null : value,
    }));
  };

  const handleSortSelect = (option: string) => {
    setSortOption(option === sortOption ? null : option);
    setShowSortMenu(false);
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatusCard
          title="Active"
          count={statusCounts.ACTIVE}
          bgColor={statusFilter === 'ACTIVE' ? 'bg-green-100' : 'bg-green-50'}
          textColor="text-green-600"
          onClick={() => handleStatusCardClick('ACTIVE')}
          isLoading={loading && properties.length === 0}
          icon={
            <svg
              className="h-6 w-6 text-green-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
        <StatusCard
          title="In-maintenance"
          count={statusCounts.MAINTENANCE}
          bgColor={
            statusFilter === 'MAINTENANCE' ? 'bg-orange-100' : 'bg-orange-50'
          }
          textColor="text-orange-600"
          onClick={() => handleStatusCardClick('MAINTENANCE')}
          isLoading={loading && properties.length === 0}
          icon={
            <svg
              className="h-6 w-6 text-orange-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
        <StatusCard
          title="Vacant"
          count={statusCounts.VACANT}
          bgColor={statusFilter === 'VACANT' ? 'bg-yellow-100' : 'bg-yellow-50'}
          textColor="text-yellow-600"
          onClick={() => handleStatusCardClick('VACANT')}
          isLoading={loading && properties.length === 0}
          icon={
            <svg
              className="h-6 w-6 text-yellow-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
        <StatusCard
          title="Total"
          count={statusCounts.total}
          onClick={clearFilters}
          isLoading={loading && properties.length === 0}
          icon={
            <svg
              className="h-6 w-6 text-indigo-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
          }
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
              {(statusFilter ||
                Object.values(filterOptions).some((val) => val !== null)) && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">Filtered by:</span>
                  {statusFilter && <StatusBadge status={statusFilter} />}
                  {filterOptions.propertyType && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                      Type: {filterOptions.propertyType}
                    </span>
                  )}
                  {filterOptions.status && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                      Status: {capitalize(filterOptions.status.toLowerCase())}
                    </span>
                  )}
                  {filterOptions.dateAdded && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                      Date:{' '}
                      {filterOptions.dateAdded === 'last-week'
                        ? 'Last week'
                        : filterOptions.dateAdded === 'last-month'
                        ? 'Last month'
                        : 'Last year'}
                    </span>
                  )}
                  <button
                    onClick={clearFilters}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    <i className="fas fa-times-circle"></i>
                  </button>
                </div>
              )}

              <button
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
                onClick={() => setIsModalOpen(true)}
                onMouseEnter={() => preloadGoogleMaps()}
                onFocus={() => preloadGoogleMaps()}
              >
                <i className="fas fa-plus"></i>
                Add new property
              </button>

              {/* Filter Dropdown */}
              <div className="relative" ref={filterMenuRef}>
                <button
                  onClick={handleFilterToggle}
                  className={`inline-flex items-center px-4 py-2 border rounded-lg shadow-sm text-sm font-medium ${
                    Object.values(filterOptions).some((val) => val !== null)
                      ? 'bg-blue-50 text-blue-700 border-blue-300'
                      : 'text-gray-700 bg-white border-gray-300'
                  } hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
                >
                  <i className="fas fa-filter mr-2"></i>
                  Filter
                </button>

                {showFilterMenu && (
                  <div className="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 divide-y divide-gray-100 focus:outline-none z-10">
                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Property Type
                      </h3>
                      <div className="space-y-1">
                        {[
                          'Residential',
                          'Commercial',
                          'Industrial',
                          'Mixed-Use',
                          'Apartment Complex',
                          'Land',
                          'Special Purpose',
                          'Other',
                        ].map((type) => (
                          <button
                            key={type}
                            onClick={() =>
                              handleFilterSelect('propertyType', type)
                            }
                            className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                              filterOptions.propertyType === type
                                ? 'bg-blue-100 text-blue-800'
                                : 'text-gray-700 hover:bg-gray-100'
                            }`}
                          >
                            {filterOptions.propertyType === type && (
                              <svg
                                className="mr-2 h-4 w-4 text-blue-500"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            )}
                            {type}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Status
                      </h3>
                      <div className="space-y-1">
                        {['ACTIVE', 'MAINTENANCE', 'VACANT'].map((status) => (
                          <button
                            key={status}
                            onClick={() => handleFilterSelect('status', status)}
                            className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                              filterOptions.status === status
                                ? 'bg-blue-100 text-blue-800'
                                : 'text-gray-700 hover:bg-gray-100'
                            }`}
                          >
                            {filterOptions.status === status && (
                              <svg
                                className="mr-2 h-4 w-4 text-blue-500"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            )}
                            {capitalize(status.toLowerCase())}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Date Added
                      </h3>
                      <div className="space-y-1">
                        {[
                          { id: 'last-week', label: 'Last Week' },
                          { id: 'last-month', label: 'Last Month' },
                          { id: 'last-year', label: 'Last Year' },
                        ].map((option) => (
                          <button
                            key={option.id}
                            onClick={() =>
                              handleFilterSelect('dateAdded', option.id)
                            }
                            className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                              filterOptions.dateAdded === option.id
                                ? 'bg-blue-100 text-blue-800'
                                : 'text-gray-700 hover:bg-gray-100'
                            }`}
                          >
                            {filterOptions.dateAdded === option.id && (
                              <svg
                                className="mr-2 h-4 w-4 text-blue-500"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            )}
                            {option.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="p-2">
                      <button
                        onClick={clearFilters}
                        className="w-full flex justify-center items-center px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md"
                      >
                        <i className="fas fa-times-circle mr-2"></i>
                        Clear All Filters
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Sort Dropdown */}
              <div className="relative" ref={sortMenuRef}>
                <button
                  onClick={handleSortToggle}
                  className={`inline-flex items-center px-4 py-2 border rounded-lg shadow-sm text-sm font-medium ${
                    sortOption
                      ? 'bg-blue-50 text-blue-700 border-blue-300'
                      : 'text-gray-700 bg-white border-gray-300'
                  } hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
                >
                  <i className="fas fa-sort mr-2"></i>
                  Sort
                </button>

                {showSortMenu && (
                  <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 divide-y divide-gray-100 focus:outline-none z-10">
                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Name
                      </h3>
                      <div className="space-y-1">
                        <button
                          onClick={() => handleSortSelect('name-asc')}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === 'name-asc'
                              ? 'bg-blue-100 text-blue-800'
                              : 'text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          <i className="fas fa-sort-alpha-down mr-2"></i>A to Z
                        </button>
                        <button
                          onClick={() => handleSortSelect('name-desc')}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === 'name-desc'
                              ? 'bg-blue-100 text-blue-800'
                              : 'text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          <i className="fas fa-sort-alpha-down-alt mr-2"></i>Z
                          to A
                        </button>
                      </div>
                    </div>

                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Type
                      </h3>
                      <div className="space-y-1">
                        <button
                          onClick={() => handleSortSelect('type-asc')}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === 'type-asc'
                              ? 'bg-blue-100 text-blue-800'
                              : 'text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          <i className="fas fa-sort-alpha-down mr-2"></i>A to Z
                        </button>
                        <button
                          onClick={() => handleSortSelect('type-desc')}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === 'type-desc'
                              ? 'bg-blue-100 text-blue-800'
                              : 'text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          <i className="fas fa-sort-alpha-down-alt mr-2"></i>Z
                          to A
                        </button>
                      </div>
                    </div>

                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Date Added
                      </h3>
                      <div className="space-y-1">
                        <button
                          onClick={() => handleSortSelect('date-desc')}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === 'date-desc'
                              ? 'bg-blue-100 text-blue-800'
                              : 'text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          <i className="fas fa-sort-numeric-down-alt mr-2"></i>
                          Newest First
                        </button>
                        <button
                          onClick={() => handleSortSelect('date-asc')}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === 'date-asc'
                              ? 'bg-blue-100 text-blue-800'
                              : 'text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          <i className="fas fa-sort-numeric-down mr-2"></i>
                          Oldest First
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        <PropertyTable
          properties={filteredProperties}
          loading={loading || deletePropertyMutation.isPending}
          error={error}
          onDelete={handleDeleteProperty}
          onEdit={handleEditProperty}
        />
      </div>

      {/* New/Edit Property Modal */}
      <NewPropertyModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setCurrentProperty(null);
          setIsEditing(false);
        }}
        propertyData={currentProperty as Record<string, unknown> | null}
        isEditing={isEditing}
      />

      {/* Toast Notifications */}
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
        theme="light"
      />
    </div>
  );
};

export default Properties;