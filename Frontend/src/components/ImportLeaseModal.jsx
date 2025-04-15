import React, { useState, useEffect } from 'react';
import { fetchProperties, parseLease, fetchTenantsByProperty, getCurrentUser } from '../utils/api';
import TenantModal from './TenantModal';
import ConfirmLeaseModal from './ConfirmLeaseModal';
import { getInputClassName } from '../utils/formUtils';

const ImportLeaseModal = ({ isOpen, onClose, onImport }) => {
  const [properties, setProperties] = useState([]);
  const [selectedProperty, setSelectedProperty] = useState('');
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [file, setFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [leaseData, setLeaseData] = useState({
    monthly_rent: '',
    start_date: '',
    end_date: '',
    security_deposit: '',
    tenant_name: '',
    unit: ''
  });
  const [isCreatingNewTenant, setIsCreatingNewTenant] = useState(false);
  const [isLoadingTenants, setIsLoadingTenants] = useState(false);
  const [tenantLoadError, setTenantLoadError] = useState(null);
  const [showTenantModal, setShowTenantModal] = useState(false);
  const [showConfirmLeaseModal, setShowConfirmLeaseModal] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [propertySearchTerm, setPropertySearchTerm] = useState('');
  const [tenantData, setTenantData] = useState({});
  const [createdTenant, setCreatedTenant] = useState(null);
  
  // Load properties on component mount
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

  // Load tenants when property is selected
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
        } finally {
          setIsLoadingTenants(false);
        }
      } else {
        setTenants([]);
        setSelectedTenant(null);
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
        special_terms: null,
        unit: response.unit || ''
      };
      console.log('Storing lease data:', extractedLeaseData);
      setLeaseData(extractedLeaseData);

      // Set tenant data
      const tenantData = {
        full_name: response.tenant_name,
        first_name: '',
        last_name: '',
        phone: '',
        email: '',
        current_property_id: parseInt(selectedProperty),
        unit: response.unit || '',
        lease_start: response.start_date,
        lease_end: response.end_date,
        monthly_rent: response.monthly_rent?.toString() || '0',
        status: 'Active'
      };

      // Split the full name into first and last name
      if (response.tenant_name) {
        const nameParts = response.tenant_name.split(' ');
        tenantData.first_name = nameParts[0] || '';
        tenantData.last_name = nameParts.slice(1).join(' ') || '';
      }

      console.log('Setting tenant data:', tenantData);
      setTenantData(tenantData);
      
      // If creating a new tenant, show the tenant modal first
      if (isCreatingNewTenant) {
        setShowTenantModal(true);
      } else if (selectedTenant) {
        // If an existing tenant is selected, show the confirm lease modal
        setCreatedTenant(selectedTenant);
        setShowConfirmLeaseModal(true);
      }
    } catch (error) {
      console.error('Error analyzing lease:', error);
      setError(error.message || 'Failed to analyze lease. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTenantSave = (tenant) => {
    console.log('Received created tenant from TenantModal:', tenant);
    setError(null);
    setCreatedTenant(tenant);
    setShowTenantModal(false);
    
    // Show the confirm lease modal after tenant is created
    setShowConfirmLeaseModal(true);
  };

  const handleLeaseSubmit = (lease) => {
    console.log('Lease created successfully:', lease);
    onImport();
    onClose();
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
    setSelectedTenant(null);
    setCreatedTenant(null);
    setShowTenantModal(false);
    setShowConfirmLeaseModal(false);
    
    // Call the parent's onClose
    onClose();
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
                              setSelectedTenant(tenant);
                              setSearchTerm(tenant.name || tenant.full_name);
                              setIsCreatingNewTenant(false);
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
                          setSelectedTenant(null);
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

          {/* Error Display */}
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

        {/* Tenant Modal for creating a new tenant */}
        {showTenantModal && (
          <TenantModal
            isOpen={showTenantModal}
            onClose={() => setShowTenantModal(false)}
            tenant={tenantData}
            onSave={handleTenantSave}
            source="importLeaseModal"
          />
        )}

        {/* Confirm Lease Modal */}
        {showConfirmLeaseModal && (
          <ConfirmLeaseModal
            isOpen={showConfirmLeaseModal}
            onClose={() => setShowConfirmLeaseModal(false)}
            leaseData={leaseData}
            tenant={createdTenant}
            onSubmit={handleLeaseSubmit}
          />
        )}

        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
              <p className="mt-3 text-gray-600">
                Processing lease...
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ImportLeaseModal; 