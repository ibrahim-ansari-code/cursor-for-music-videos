import React, { useState, useEffect } from 'react';
import { fetchProperties, analyzeLease, submitLease, fetchTenantsByProperty } from '../utils/api';

const ImportLeaseModal = ({ isOpen, onClose, onImport }) => {
  const [properties, setProperties] = useState([]);
  const [selectedProperty, setSelectedProperty] = useState('');
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [file, setFile] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [leaseData, setLeaseData] = useState({
    monthlyRent: '',
    startDate: '',
    endDate: '',
    securityDeposit: '',
    tenantName: '',
    unit: ''
  });

  useEffect(() => {
    const loadProperties = async () => {
      try {
        const data = await fetchProperties();
        setProperties(data);
      } catch (error) {
        console.error('Failed to fetch properties:', error);
      }
    };

    loadProperties();
  }, []);

  useEffect(() => {
    const loadTenants = async () => {
      if (selectedProperty) {
        try {
          const data = await fetchTenantsByProperty(selectedProperty);
          setTenants(data);
        } catch (error) {
          console.error('Failed to fetch tenants:', error);
          setError('Failed to load tenants for this property');
        }
      } else {
        setTenants([]);
        setSelectedTenant('');
      }
    };

    loadTenants();
  }, [selectedProperty]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError(null);
    } else {
      alert('Please select a PDF file');
      e.target.value = null;
      setFile(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file || !selectedProperty || !selectedTenant) return;

    setIsLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('property_id', selectedProperty);

      const response = await analyzeLease(formData);
      
      // Convert the API response to match our form state
      setLeaseData({
        monthlyRent: response.monthly_rent.toString(),
        startDate: response.start_date,
        endDate: response.end_date,
        securityDeposit: response.security_deposit.toString(),
        tenantName: response.tenant_name,
        unit: response.unit || ''
      });
      
      setShowPreview(true);
    } catch (err) {
      console.error('Failed to analyze lease:', err);
      setError(err.message || 'Failed to analyze lease. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setLeaseData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleImport = async () => {
    if (!showPreview) return;

    setIsLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await submitLease({
        ...leaseData,
        propertyId: selectedProperty,
        tenantId: selectedTenant
      });

      setSuccess(true);
      // Close modal after 1.5 seconds
      setTimeout(() => {
        onClose();
        // Refresh the lease list if onImport callback is provided
        if (onImport) {
          onImport();
        }
      }, 1500);
    } catch (err) {
      console.error('Failed to import lease:', err);
      setError(err.message || 'Failed to import lease. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const filteredTenants = tenants.filter(tenant => 
    tenant.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tenant.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-lg bg-white">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-800">Import Lease</h2>
          <button
            onClick={onClose}
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
            <select
              className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              value={selectedProperty}
              onChange={(e) => setSelectedProperty(e.target.value)}
            >
              <option value="">Choose a property</option>
              {properties.map((property) => (
                <option key={property.id} value={property.id}>{property.name}</option>
              ))}
            </select>
          </div>

          {selectedProperty && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Tenant
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search tenants..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                />
                <select
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={selectedTenant}
                  onChange={(e) => setSelectedTenant(e.target.value)}
                >
                  <option value="">Choose a tenant</option>
                  {filteredTenants.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>
                      {tenant.name} ({tenant.email})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Upload Lease PDF
            </label>
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <button
            onClick={handleAnalyze}
            disabled={!file || !selectedProperty || !selectedTenant || isLoading}
            className="w-full inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Analyzing...
              </>
            ) : (
              'Analyze Lease'
            )}
          </button>

          {showPreview && (
            <div className="mt-6 space-y-4">
              <h3 className="text-lg font-medium text-gray-900">Lease Details</h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Monthly Rent</label>
                  <input
                    type="text"
                    name="monthlyRent"
                    value={leaseData.monthlyRent}
                    onChange={handleInputChange}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Security Deposit</label>
                  <input
                    type="text"
                    name="securityDeposit"
                    value={leaseData.securityDeposit}
                    onChange={handleInputChange}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Start Date</label>
                  <input
                    type="date"
                    name="startDate"
                    value={leaseData.startDate}
                    onChange={handleInputChange}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">End Date</label>
                  <input
                    type="date"
                    name="endDate"
                    value={leaseData.endDate}
                    onChange={handleInputChange}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Tenant Name</label>
                  <input
                    type="text"
                    name="tenantName"
                    value={leaseData.tenantName}
                    onChange={handleInputChange}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Unit (Optional)</label>
                  <input
                    type="text"
                    name="unit"
                    value={leaseData.unit}
                    onChange={handleInputChange}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>
              </div>
            </div>
          )}

          <div className="mt-6 flex justify-end space-x-3">
            <button
              onClick={onClose}
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              onClick={handleImport}
              disabled={!showPreview || isLoading}
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Importing...
                </>
              ) : success ? (
                'Success!'
              ) : (
                'Import Lease'
              )}
            </button>
          </div>

          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {success && (
            <div className="mt-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
              Lease imported successfully!
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ImportLeaseModal; 