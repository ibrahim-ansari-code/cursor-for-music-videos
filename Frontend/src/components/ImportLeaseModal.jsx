import React, { useState, useEffect } from 'react';
import { fetchProperties, parseLease, submitLease, fetchTenantsByProperty, getCurrentUser, createTenant as createTenantAPI, createLease as createLeaseAPI } from '../utils/api';
import TenantModal from './TenantModal';
import { getInputClassName } from '../utils/formUtils';

const ImportLeaseModal = ({ isOpen, onClose, onImport }) => {
  const [properties, setProperties] = useState([]);
  const [selectedProperty, setSelectedProperty] = useState('');
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [file, setFile] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isTenantCreating, setIsTenantCreating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [leaseData, setLeaseData] = useState({
    monthly_rent: '',
    start_date: '',
    end_date: '',
    security_deposit: '',
    tenant_name: '',
    unit: ''
  });
  const [isCreatingNewTenant, setIsCreatingNewTenant] = useState(false);
  const [additionalFields, setAdditionalFields] = useState({});
  const [isLoadingTenants, setIsLoadingTenants] = useState(false);
  const [tenantLoadError, setTenantLoadError] = useState(null);
  const [showTenantModal, setShowTenantModal] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [propertySearchTerm, setPropertySearchTerm] = useState('');
  const [tenantData, setTenantData] = useState({});
  const [isLeaseCreating, setIsLeaseCreating] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({
    security_deposit: '',
    monthly_rent: '',
    start_date: '',
    end_date: '',
    tenant_name: '',
    unit: ''
  });
  const [formData, setFormData] = useState({
    full_name: '',
    phone: '',
    email: '',
    current_property_id: '',
    unit_id: '',
    unit: '',
    lease_start: '',
    lease_end: '',
    monthly_rent: '',
    security_deposit: '',
    status: 'Active',
    leasing_agent: ''
  });
  const [formSubmitted, setFormSubmitted] = useState(false);

  useEffect(() => {
    const loadProperties = async () => {
      try {
        const data = await fetchProperties();
        setProperties(data);
      } catch (error) {
        console.error('Failed to fetch properties:', error);
        setError('Failed to load properties. Please try again.');
      }
    };

    const validateUserPermissions = async () => {
      try {
        // Check current user permissions from server
        const userInfo = await getCurrentUser();
        
        // Get and log the user type we got from the server
        const userType = userInfo.user_type?.toUpperCase();
        console.log('Current user type from server:', userType);
        
        // Also check what we have in localStorage
        const localUserType = localStorage.getItem('user_type');
        const localUser = JSON.parse(localStorage.getItem('user') || '{}');
        console.log('User type from localStorage:', localUserType);
        console.log('User object from localStorage:', localUser);
        
        // Validate against uppercase values to match the enum
        if (userType !== 'LANDLORD' && userType !== 'ADMIN') {
          setError('Your account doesn\'t have permission to create leases. Please contact an administrator.');
        } else {
          // Ensure we have the correct uppercase value in localStorage
          localStorage.setItem('user_type', userType);
          
          // Update the user object too if it exists
          if (localUser && localUser.id) {
            localUser.user_type = userType;
            localStorage.setItem('user', JSON.stringify(localUser));
          }
        }
      } catch (error) {
        console.error('Failed to validate user permissions:', error);
        setError('Unable to verify your permissions. Please refresh the page and try again.');
      }
    };

    loadProperties();
    validateUserPermissions();
  }, []);

  useEffect(() => {
    const loadTenants = async () => {
      if (selectedProperty) {
        setIsLoadingTenants(true);
        setTenantLoadError(null);
        try {
          const data = await fetchTenantsByProperty(selectedProperty);
          setTenants(data);
          setError(null); // Clear any previous errors
        } catch (error) {
          console.error('Failed to fetch tenants:', error);
          setTenantLoadError('Failed to load tenants for this property. Please try again.');
          // Don't reset tenants array to avoid UI flickering
        } finally {
          setIsLoadingTenants(false);
        }
      } else {
        setTenants([]);
        setSelectedTenant('');
        setTenantLoadError(null);
      }
    };

    loadTenants();
  }, [selectedProperty]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownOpen && !event.target.closest('.tenant-dropdown')) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [dropdownOpen]);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError(null);
    } else {
      alert('Please select a PDF file');
      setFile(null);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    const selectedFile = e.dataTransfer.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError(null);
    } else {
      alert('Please drop a PDF file');
      setFile(null);
    }
  };

  const handleImportClick = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Analyze the lease to get LLM data
      const formData = new FormData();
      formData.append('file', file);
      formData.append('property_id', selectedProperty);

      console.log('Calling parseLease API endpoint...');
      const response = await parseLease(formData);
      console.log('Lease parse successful:', response);

      // Store the complete lease data needed for creation
      const extractedLeaseData = {
        monthly_rent: parseFloat(response.monthly_rent || 0),
        security_deposit: parseFloat(response.security_deposit || 0),
        start_date: response.start_date,
        end_date: response.end_date,
        property_id: parseInt(selectedProperty),
        is_renewable: true,
        auto_renew: false,
        rent_due_day: 1,
        late_fee_amount: null,
        late_fee_after_days: null,
        special_terms: null
      };
      console.log('Storing lease data:', extractedLeaseData);
      setLeaseData(extractedLeaseData);

      // Set tenant data
      const tenantData = {
        full_name: response.tenant_name,
        current_property_id: parseInt(selectedProperty),
        unit: response.unit || '',
        lease_start: response.start_date,
        lease_end: response.end_date,
        monthly_rent: response.monthly_rent?.toString() || '0'
      };

      console.log('Setting tenant data:', tenantData);
      setTenantData(tenantData);

      // Open TenantModal after LLM data is set
      setShowTenantModal(true);
    } catch (error) {
      console.error('Error analyzing lease:', error);
      setError(error.message || 'Failed to analyze lease. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTenantSave = async (tenant) => {
    try {
      console.log('Received created tenant from TenantModal:', tenant);
      setError(null);

      // Merge LLM-extracted lease fields into leaseData
      const updatedLeaseData = {
        ...leaseData,
        tenant_id: tenant.id,
        start_date: leaseData.start_date || tenant.lease_start,
        end_date: leaseData.end_date || tenant.lease_end,
        monthly_rent: leaseData.monthly_rent || tenant.monthly_rent
      };
      setLeaseData(updatedLeaseData);

      // Call handleSubmit after leaseData is fully populated
      handleSubmit();
    } catch (error) {
      console.error('Error in lease creation flow:', error);
      setError(error.message || 'Failed to create lease. Please try again.');
      throw error;
    }
  };

  const safeToISOString = (date) => {
    if (date instanceof Date && !isNaN(date)) {
      return date.toISOString().split('T')[0];
    }
    return '';
  };

  const handleSubmit = async () => {
    // Validate dates
    if (!leaseData.start_date || !leaseData.end_date) {
      setError('Start date and end date are required.');
      return;
    }
    if (new Date(leaseData.start_date) > new Date(leaseData.end_date)) {
      setError('End date must be after start date');
      return;
    }

    try {
      const formattedLeaseData = {
        ...leaseData,
        start_date: safeToISOString(new Date(leaseData.start_date)),
        end_date: safeToISOString(new Date(leaseData.end_date))
      };

      // Validate required fields
      const requiredFields = ['monthly_rent', 'start_date', 'end_date', 'security_deposit'];
      const missingFields = requiredFields.filter(field => !formattedLeaseData[field]);
      if (missingFields.length > 0) {
        setError(`Missing required fields: ${missingFields.join(', ')}`);
        return;
      }

      // Submit to backend
      await submitLease(formattedLeaseData);
      onImport();
    } catch (error) {
      console.error('Error submitting lease:', error);
      setError('Failed to submit lease. Please try again.');
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setLeaseData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const filteredTenants = tenants.filter(tenant => {
    const tenantName = tenant.name || tenant.full_name || '';
    const tenantEmail = tenant.email || '';
    
    return tenantName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tenantEmail.toLowerCase().includes(searchTerm.toLowerCase());
  });

  // Handle closing the modal with cleanup
  const handleClose = () => {
    // Reset states when closing
    setError(null);
    setTenantLoadError(null);
    setSuccess(false);
    
    // Call the parent's onClose
    onClose();
  };

  // Function to safely format dates
  const formatDate = (dateValue) => {
    if (!dateValue) return '';
    
    // If it's already in YYYY-MM-DD format, return it as is
    if (typeof dateValue === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(dateValue)) {
      return dateValue;
    }
    
    // For dates already in Date object format
    if (dateValue instanceof Date) {
      const year = dateValue.getFullYear();
      const month = String(dateValue.getMonth() + 1).padStart(2, '0');
      const day = String(dateValue.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    }
    
    // Handle other string formats - explicitly parse components
    if (typeof dateValue === 'string') {
      // Try standard date parsing first
      try {
        const tempDate = new Date(dateValue);
        if (!isNaN(tempDate.getTime())) {
          const year = tempDate.getFullYear();
          const month = String(tempDate.getMonth() + 1).padStart(2, '0');
          const day = String(tempDate.getDate()).padStart(2, '0');
          return `${year}-${month}-${day}`;
        }
      } catch (e) {
        console.error('Error parsing date string:', e);
      }
      
      // If standard parsing fails, try manual parsing for common formats
      // MM/DD/YYYY or MM-DD-YYYY
      const dateRegex = /^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/;
      const match = dateValue.match(dateRegex);
      if (match) {
        const month = String(parseInt(match[1])).padStart(2, '0');
        const day = String(parseInt(match[2])).padStart(2, '0');
        const year = match[3];
        return `${year}-${month}-${day}`;
      }
    }
    
    console.error('Could not parse date:', dateValue);
    return '';
  };

  // Debugging: Log formData and fieldErrors
  useEffect(() => {
    console.log('formData:', formData);
    console.log('fieldErrors:', fieldErrors);
  }, [formData, fieldErrors]);

  // Wrap getInputClassName in a try-catch block
  const safeGetInputClassName = (field) => {
    try {
      if (formSubmitted || fieldErrors[field]) {
        return getInputClassName(field, fieldErrors, formData);
      }
      return ''; // Return default class if no validation is needed
    } catch (error) {
      console.error(`Error getting input class name for ${field}:`, error);
      return '';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-lg bg-white">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-800">Import Lease</h2>
          <button
            onClick={handleClose}
            className="text-gray-600 hover:text-gray-800"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select Property
            </label>
            <div className="relative tenant-dropdown">
              <input
                type="text"
                placeholder="Search or select property..."
                value={propertySearchTerm}
                onChange={(e) => {
                  setPropertySearchTerm(e.target.value);
                  setDropdownOpen('property');
                }}
                className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              />
              {dropdownOpen === 'property' && (
                <div className="absolute z-10 mt-1 w-full bg-white shadow-lg rounded-md">
                  <ul className="max-h-60 overflow-auto rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                    {properties.filter(property => property.name.toLowerCase().includes(propertySearchTerm.toLowerCase())).map((property) => (
                      <li
                        key={property.id}
                        className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-blue-100"
                        onClick={() => {
                          setSelectedProperty(property.id);
                          setPropertySearchTerm(property.name);
                          setDropdownOpen(false);
                        }}
                      >
                        <span className="font-normal block truncate">
                          {property.name}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {selectedProperty && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select or Create Tenant
              </label>
              <div className="relative tenant-dropdown">
                <input
                  type="text"
                  placeholder="Search or create tenant..."
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setDropdownOpen('tenant');
                  }}
                  className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                />
                {dropdownOpen === 'tenant' && (
                  <div className="absolute z-10 mt-1 w-full bg-white shadow-lg rounded-md">
                    <ul className="max-h-60 overflow-auto rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                      {filteredTenants.length > 0 ? (
                        filteredTenants.map((tenant) => (
                          <li
                            key={tenant.id}
                            className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-blue-100"
                            onClick={() => {
                              setSelectedTenant(tenant.id);
                              setSearchTerm(tenant.name || tenant.full_name);
                              setDropdownOpen(false);
                            }}
                          >
                            <span className="font-normal block truncate">
                              {tenant.name || tenant.full_name} {tenant.email ? `(${tenant.email})` : ''}
                            </span>
                          </li>
                        ))
                      ) : (
                        <li className="text-gray-500 py-2 px-3">No tenants found</li>
                      )}
                      <li
                        className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-blue-100"
                        onClick={() => {
                          setIsCreatingNewTenant(true);
                          setSearchTerm('Create New Tenant');
                          setDropdownOpen(false);
                        }}
                      >
                        <span className="font-normal block truncate text-blue-600">
                          + Create New Tenant
                        </span>
                      </li>
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          <div
            onDrop={handleFileDrop}
            onDragOver={(e) => e.preventDefault()}
            className="border-2 border-dashed border-gray-300 rounded-md p-4 text-center cursor-pointer"
            onClick={() => document.getElementById('fileInput').click()}
          >
            {file ? file.name : 'Click to select or drop lease PDF here'}
            <input
              type="file"
              id="fileInput"
              accept=".pdf"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
          </div>

          <div>
            <label htmlFor="security_deposit" className="block text-sm font-medium text-gray-700">
              Security Deposit <span className="text-red-600">*</span>
            </label>
            <div className="mt-1 relative rounded-md shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="text-gray-500 sm:text-sm">$</span>
              </div>
              <input
                type="number"
                id="security_deposit"
                name="security_deposit"
                value={leaseData.security_deposit}
                onChange={handleInputChange}
                step="0.01"
                min="0"
                required
                className={`${safeGetInputClassName('security_deposit')} pl-7`}
              />
            </div>
            {fieldErrors.security_deposit && (
              <p className="mt-1 text-sm text-red-600">{fieldErrors.security_deposit}</p>
            )}
          </div>

          {/* Error Display - Show any errors in a consistent way */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
              <span className="block sm:inline">{error}</span>
              <button
                onClick={() => setError(null)}
                className="absolute top-0 right-0 px-4 py-3"
              >
                <span className="sr-only">Dismiss</span>
                <svg
                  className="h-6 w-6 text-red-500"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          )}

          <button
            onClick={handleImportClick}
            disabled={!file || !selectedProperty || (!selectedTenant && !isCreatingNewTenant) || isLoading}
            className="w-full inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Importing...
              </>
            ) : (
              'Import'
            )}
          </button>
        </div>

        {showTenantModal && (
          <TenantModal
            isOpen={showTenantModal}
            onClose={() => setShowTenantModal(false)}
            tenant={selectedTenant}
            onSave={handleTenantSave}
            source="importLeaseModal"
          />
        )}

        {/* Show loading state when creating tenant or lease */}
        {(isLoading || isLeaseCreating) && (
          <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
              <p className="mt-3 text-gray-600">
                {isLeaseCreating ? 'Creating lease...' : 'Processing lease...'}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ImportLeaseModal; 