import React, { useState, useEffect } from 'react';
import { submitLease, fetchProperties } from '../utils/api';
import { getInputClassName } from '../utils/formUtils';

const ConfirmLeaseModal = ({ isOpen, onClose, leaseData, tenant, onSubmit }) => {
  const [formData, setFormData] = useState({
    property_id: '',
    unit_id: '',
    unit: '',
    start_date: '',
    end_date: '',
    monthly_rent: '',
    security_deposit: '',
    tenant_id: '',
    is_renewable: true,
    auto_renew: false,
    rent_due_day: 1,
    late_fee_amount: null,
    late_fee_after_days: null,
    special_terms: null
  });
  const [properties, setProperties] = useState([]);
  const [fieldErrors, setFieldErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingProperties, setIsLoadingProperties] = useState(false);
  const [error, setError] = useState(null);
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [selectedProperty, setSelectedProperty] = useState(null);

  // Load properties on component mount
  useEffect(() => {
    const loadProperties = async () => {
      setIsLoadingProperties(true);
      try {
        const data = await fetchProperties();
        setProperties(data);
        
        // If leaseData already has a property_id, find the property object
        if (leaseData?.property_id) {
          const property = data.find(p => p.id === parseInt(leaseData.property_id));
          if (property) {
            setSelectedProperty(property);
          }
        }
      } catch (error) {
        console.error('Failed to fetch properties:', error);
        setError('Failed to load properties. Please try again.');
      } finally {
        setIsLoadingProperties(false);
      }
    };

    if (isOpen) {
      loadProperties();
    }
  }, [isOpen, leaseData?.property_id]);

  // Populate form data when leaseData or tenant changes
  useEffect(() => {
    if (leaseData && tenant) {
      // Merge data from leaseData and tenant
      const updatedFormData = {
        tenant_id: tenant.id,
        property_id: leaseData.property_id || tenant.current_property_id || '',
        unit_id: tenant.unit_id || '',
        unit: leaseData.unit || tenant.unit || '',
        start_date: leaseData.start_date || tenant.lease_start || '',
        end_date: leaseData.end_date || tenant.lease_end || '',
        monthly_rent: leaseData.monthly_rent || tenant.monthly_rent || '',
        security_deposit: leaseData.security_deposit || '0',
        is_renewable: leaseData.is_renewable !== undefined ? leaseData.is_renewable : true,
        auto_renew: leaseData.auto_renew || false,
        rent_due_day: leaseData.rent_due_day || 1,
        late_fee_amount: leaseData.late_fee_amount || null,
        late_fee_after_days: leaseData.late_fee_after_days || null,
        special_terms: leaseData.special_terms || null
      };
      setFormData(updatedFormData);
      console.log('ConfirmLeaseModal - Form data initialized:', updatedFormData);
    }
  }, [leaseData, tenant]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    // Handle checkboxes
    if (type === 'checkbox') {
      setFormData(prev => ({
        ...prev,
        [name]: checked
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
    
    // Clear field-specific error when user changes the field
    if (fieldErrors[name]) {
      setFieldErrors(prev => {
        const updated = {...prev};
        delete updated[name];
        return updated;
      });
    }
  };

  const handlePropertyChange = (e) => {
    const propertyId = e.target.value;
    setFormData(prev => ({
      ...prev,
      property_id: propertyId
    }));
    
    if (fieldErrors.property_id) {
      setFieldErrors(prev => {
        const updated = {...prev};
        delete updated.property_id;
        return updated;
      });
    }
    
    const property = properties.find(p => p.id === parseInt(propertyId));
    setSelectedProperty(property);
  };

  const validateForm = () => {
    const errors = {};
    
    // Required fields
    if (!formData.property_id) errors.property_id = 'Property is required';
    if (!formData.start_date) errors.start_date = 'Lease Start Date is required';
    if (!formData.end_date) errors.end_date = 'Lease End Date is required';
    if (!formData.monthly_rent) errors.monthly_rent = 'Monthly Rent is required';
    if (formData.security_deposit === undefined || formData.security_deposit === '') {
      errors.security_deposit = 'Security Deposit is required';
    }
    if (!formData.tenant_id) errors.tenant_id = 'Tenant is required';
    
    // Require either unit_id or unit field to be filled
    if (!formData.unit_id && !formData.unit) {
      errors.unit = 'Unit information is required';
    }
    
    // Dates validation
    if (formData.start_date && formData.end_date) {
      const start = new Date(formData.start_date);
      const end = new Date(formData.end_date);
      if (start > end) {
        errors.end_date = 'End date must be after start date';
      }
    }
    
    return errors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormSubmitted(true);
    
    // Validate form
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      setError('Please correct the validation errors below.');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    setFieldErrors({});
    
    try {
      // Format data for API
      const leaseSubmitData = {
        ...formData,
        monthly_rent: parseFloat(formData.monthly_rent),
        security_deposit: parseFloat(formData.security_deposit),
        property_id: parseInt(formData.property_id),
        tenant_id: parseInt(formData.tenant_id),
        unit_id: formData.unit_id ? parseInt(formData.unit_id) : null,
        rent_due_day: parseInt(formData.rent_due_day || 1)
      };
      
      console.log('Submitting lease data:', leaseSubmitData);
      
      // Submit to backend
      const response = await submitLease(leaseSubmitData);
      console.log('Lease created successfully:', response);
      
      if (onSubmit) {
        onSubmit(response);
      }
      
      onClose();
    } catch (err) {
      console.error('Failed to create lease:', err);
      setError(err.message || 'Failed to create lease. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Safely get input class name
  const safeGetInputClassName = (field) => {
    try {
      if (formSubmitted || fieldErrors[field]) {
        return getInputClassName(field, fieldErrors, formSubmitted, formData);
      }
      return 'border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm'; // Default class
    } catch (error) {
      console.error(`Error getting input class name for ${field}:`, error);
      return 'border-gray-300 rounded-md shadow-sm'; // Fallback class
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-lg bg-white">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-800">Confirm Lease Details</h2>
          <button
            onClick={onClose}
            className="text-gray-600 hover:text-gray-800"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Tenant Information (Read-only) */}
            <div className="col-span-2 bg-gray-50 p-3 rounded-md">
              <h3 className="text-md font-medium text-gray-700 mb-2">Tenant Information</h3>
              <p className="text-sm text-gray-600">{tenant?.full_name}</p>
              <p className="text-sm text-gray-600">{tenant?.email}</p>
              <p className="text-sm text-gray-600">{tenant?.phone}</p>
            </div>

            {/* Property Information */}
            <div>
              <label htmlFor="property_id" className="block text-sm font-medium text-gray-700">
                Property <span className="text-red-600">*</span>
              </label>
              <select
                id="property_id"
                name="property_id"
                value={formData.property_id}
                onChange={handlePropertyChange}
                className={`mt-1 block w-full ${safeGetInputClassName('property_id')}`}
              >
                <option value="">Select a property</option>
                {properties.map(property => (
                  <option key={property.id} value={property.id}>
                    {property.name}
                  </option>
                ))}
              </select>
              {fieldErrors.property_id && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.property_id}</p>
              )}
            </div>

            <div>
              <label htmlFor="unit" className="block text-sm font-medium text-gray-700">
                Unit <span className="text-red-600">*</span>
              </label>
              <input
                type="text"
                id="unit"
                name="unit"
                value={formData.unit}
                onChange={handleChange}
                className={`mt-1 block w-full ${safeGetInputClassName('unit')}`}
              />
              {fieldErrors.unit && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.unit}</p>
              )}
            </div>

            {/* Lease Information */}
            <div>
              <label htmlFor="start_date" className="block text-sm font-medium text-gray-700">
                Lease Start Date <span className="text-red-600">*</span>
              </label>
              <input
                type="date"
                id="start_date"
                name="start_date"
                value={formData.start_date}
                onChange={handleChange}
                className={`mt-1 block w-full ${safeGetInputClassName('start_date')}`}
              />
              {fieldErrors.start_date && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.start_date}</p>
              )}
            </div>

            <div>
              <label htmlFor="end_date" className="block text-sm font-medium text-gray-700">
                Lease End Date <span className="text-red-600">*</span>
              </label>
              <input
                type="date"
                id="end_date"
                name="end_date"
                value={formData.end_date}
                onChange={handleChange}
                className={`mt-1 block w-full ${safeGetInputClassName('end_date')}`}
              />
              {fieldErrors.end_date && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.end_date}</p>
              )}
            </div>

            <div>
              <label htmlFor="monthly_rent" className="block text-sm font-medium text-gray-700">
                Monthly Rent <span className="text-red-600">*</span>
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">$</span>
                </div>
                <input
                  type="number"
                  id="monthly_rent"
                  name="monthly_rent"
                  value={formData.monthly_rent}
                  onChange={handleChange}
                  step="0.01"
                  min="0"
                  className={`mt-1 block w-full pl-7 ${safeGetInputClassName('monthly_rent')}`}
                />
              </div>
              {fieldErrors.monthly_rent && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.monthly_rent}</p>
              )}
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
                  value={formData.security_deposit}
                  onChange={handleChange}
                  step="0.01"
                  min="0"
                  className={`mt-1 block w-full pl-7 ${safeGetInputClassName('security_deposit')}`}
                />
              </div>
              {fieldErrors.security_deposit && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.security_deposit}</p>
              )}
            </div>

            <div>
              <label htmlFor="rent_due_day" className="block text-sm font-medium text-gray-700">
                Rent Due Day
              </label>
              <input
                type="number"
                id="rent_due_day"
                name="rent_due_day"
                value={formData.rent_due_day}
                onChange={handleChange}
                min="1"
                max="31"
                className={`mt-1 block w-full ${safeGetInputClassName('rent_due_day')}`}
              />
              {fieldErrors.rent_due_day && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.rent_due_day}</p>
              )}
            </div>

            <div>
              <div className="flex items-center space-x-2 mt-7">
                <input
                  type="checkbox"
                  id="is_renewable"
                  name="is_renewable"
                  checked={formData.is_renewable}
                  onChange={handleChange}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label htmlFor="is_renewable" className="text-sm font-medium text-gray-700">
                  Lease is renewable
                </label>
              </div>
            </div>

            <div>
              <div className="flex items-center space-x-2 mt-7">
                <input
                  type="checkbox"
                  id="auto_renew"
                  name="auto_renew"
                  checked={formData.auto_renew}
                  onChange={handleChange}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label htmlFor="auto_renew" className="text-sm font-medium text-gray-700">
                  Auto renew
                </label>
              </div>
            </div>
          </div>

          <div className="flex justify-end space-x-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating...
                </>
              ) : (
                'Create Lease'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ConfirmLeaseModal;
