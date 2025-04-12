import React, { useState, useEffect } from 'react';
import { fetchProperties, createTenant, updateTenant, fetchPropertyUnits } from '../utils/api';

const TenantModal = ({ isOpen, onClose, tenant = null, onSave }) => {
  const [properties, setProperties] = useState([]);
  const [propertyUnits, setPropertyUnits] = useState([]);
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
    status: 'Active',
    leasing_agent: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [isLLMFlow, setIsLLMFlow] = useState(false);

  // Load properties on component mount
  useEffect(() => {
    loadProperties();
  }, []);

  // Sync tenant prop to formData state - this is the source of truth for LLM flow
  useEffect(() => {
    console.log('TenantModal - tenant prop received:', tenant);
    
    if (tenant) {
      setIsLLMFlow(true); // Mark this as an LLM-driven flow
      
      const updatedFormData = {
        full_name: tenant.full_name || '',
        phone: tenant.phone || '',
        email: tenant.email || '',
        current_property_id: tenant.current_property_id || '',
        unit_id: tenant.unit_id || '',
        unit: tenant.unit || '',
        lease_start: tenant.lease_start || '',
        lease_end: tenant.lease_end || '',
        monthly_rent: typeof tenant.monthly_rent !== 'undefined' ? tenant.monthly_rent.toString() : '',
        status: tenant.status || 'Active',
        leasing_agent: tenant.leasing_agent || ''
      };

      console.log('TenantModal - updating formData with LLM data:', updatedFormData);
      setFormData(updatedFormData);
      
      // Clear any previous errors
      setFieldErrors({});
      setError(null);
    } else {
      setIsLLMFlow(false); // Reset for manual entry flow
    }
  }, [tenant, isOpen]);

  // Load property units ONLY for manual entry flow
  useEffect(() => {
    const loadUnits = async () => {
      // Skip if this is LLM flow or no property selected
      if (isLLMFlow || !formData.current_property_id) {
        return;
      }

      try {
        console.log('Loading units for property:', formData.current_property_id);
        const units = await fetchPropertyUnits(formData.current_property_id);
        setPropertyUnits(units);
      } catch (error) {
        console.error('Failed to fetch property units:', error);
        setError('Failed to load property units. Please try again.');
      }
    };

    loadUnits();
  }, [formData.current_property_id, isLLMFlow]);

  const loadProperties = async () => {
    try {
      const data = await fetchProperties();
      setProperties(data);
    } catch (error) {
      console.error('Failed to fetch properties:', error);
      setError('Failed to load properties. Please try again.');
    }
  };

  // Handle form field changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    
// Prevent property changes in LLM flow, but allow manual unit entry
if (isLLMFlow && name === 'current_property_id') {
  console.log('Preventing property change in LLM flow');
  return;
}

    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear field-specific error when user changes the field
    if (fieldErrors[name]) {
      setFieldErrors(prev => {
        const updated = {...prev};
        delete updated[name];
        return updated;
      });
    }
  };

  const validateForm = () => {
    const errors = {};
    // Required fields
    if (!formData.full_name.trim()) errors.full_name = 'Full Name is required';
    if (!formData.phone.trim()) errors.phone = 'Phone Number is required';
    if (!formData.email.trim()) errors.email = 'Email is required';
    if (!formData.current_property_id) errors.current_property_id = 'Property is required';
    
    // Require either unit_id or unit field to be filled
    if (!formData.unit_id && !formData.unit.trim()) {
      errors.unit_id = 'Unit selection is required';
      errors.unit = 'Unit information is required';
    }
    
    if (!formData.lease_start) errors.lease_start = 'Lease Start Date is required';
    if (!formData.lease_end) errors.lease_end = 'Lease End Date is required';
    if (!formData.monthly_rent) errors.monthly_rent = 'Monthly Rent is required';
    if (!formData.status) errors.status = 'Status is required';

    // Email validation
    if (formData.email.trim() && !/\S+@\S+\.\S+/.test(formData.email)) {
      errors.email = 'Email is invalid';
    }

    // Dates validation
    if (formData.lease_start && formData.lease_end) {
      const start = new Date(formData.lease_start);
      const end = new Date(formData.lease_end);
      if (start > end) {
        errors.lease_end = 'End date must be after start date';
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
      const tenantData = {
        ...formData,
        monthly_rent: formData.monthly_rent ? parseFloat(formData.monthly_rent) : null,
        current_property_id: formData.current_property_id ? parseInt(formData.current_property_id) : null,
        unit_id: formData.unit_id ? parseInt(formData.unit_id) : null
      };

      let response;
      // Check if we have a valid tenant ID (not undefined or null)
      if (tenant && tenant.id) {
        // Update existing tenant
        response = await updateTenant(tenant.id, tenantData);
      } else {
        // Create new tenant
        response = await createTenant(tenantData);
      }

      console.log('Tenant created/updated successfully:', response);

      if (onSave) {
        // Ensure all necessary fields are properly formatted
        const formattedResponse = {
          id: parseInt(response.id), // Ensure ID is an integer
          full_name: response.full_name,
          email: response.email,
          phone: response.phone,
          current_property_id: response.current_property_id ? parseInt(response.current_property_id) : null,
          unit_id: response.unit_id ? parseInt(response.unit_id) : null,
          unit: response.unit,
          lease_start: response.lease_start,
          lease_end: response.lease_end,
          monthly_rent: response.monthly_rent ? parseFloat(response.monthly_rent) : null,
          status: response.status
        };

        console.log('Passing formatted tenant data to parent:', formattedResponse);
        onSave(formattedResponse);
      }
      onClose();
    } catch (err) {
      console.error('Failed to save tenant:', err);
      
      // Handle validation errors (422 status)
      if (err.status === 422 && err.data?.detail) {
        // Handle field validation errors
        if (Array.isArray(err.data.detail)) {
          const validationErrors = {};
          const generalErrors = [];
          
          err.data.detail.forEach(error => {
            if (error.loc && error.loc.length > 1) {
              // This is a field-specific error
              const fieldName = error.loc[1];
              validationErrors[fieldName] = error.msg;
            } else {
              // This is a general error
              generalErrors.push(error.msg);
            }
          });
          
          setFieldErrors(validationErrors);
          
          if (generalErrors.length > 0) {
            setError(`Please correct the following: ${generalErrors.join(', ')}`);
          } else {
            setError('Please correct the validation errors below.');
          }
        } else if (typeof err.data.detail === 'string') {
          setError(err.data.detail);
        }
      } else {
        // Handle generic errors
        setError(err.message || 'Failed to save tenant. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Helper function to get input class based on error state
  const getInputClassName = (fieldName) => {
    const baseClass = "mt-1 block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm";
    return (fieldErrors[fieldName] || (formSubmitted && !formData[fieldName]))
      ? `${baseClass} border-red-300 text-red-900 placeholder-red-300 focus:outline-none focus:ring-red-500 focus:border-red-500`
      : baseClass;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
      <div className="relative p-5 border w-full max-w-2xl shadow-lg rounded-lg bg-white">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-800">
            {tenant ? 'Edit Tenant' : 'Add Tenant'}
          </h2>
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
            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-gray-700">
                Full Name <span className="text-red-600">*</span>
              </label>
              <input
                type="text"
                id="full_name"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                required
                className={getInputClassName('full_name')}
              />
              {fieldErrors.full_name && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.full_name}</p>
              )}
            </div>

            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700">
                Phone Number <span className="text-red-600">*</span>
              </label>
              <input
                type="tel"
                id="phone"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                required
                className={getInputClassName('phone')}
              />
              {fieldErrors.phone && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.phone}</p>
              )}
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email <span className="text-red-600">*</span>
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                className={getInputClassName('email')}
              />
              {fieldErrors.email && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.email}</p>
              )}
            </div>

            <div>
              <label htmlFor="current_property_id" className="block text-sm font-medium text-gray-700">
                Property <span className="text-red-600">*</span>
              </label>
              <select
                id="current_property_id"
                name="current_property_id"
                value={formData.current_property_id}
                onChange={handleChange}
                required
                className={getInputClassName('current_property_id')}
              >
                <option value="">Select a property</option>
                {properties.map((property) => (
                  <option key={property.id} value={property.id}>
                    {property.name}
                  </option>
                ))}
              </select>
              {fieldErrors.current_property_id && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.current_property_id}</p>
              )}
            </div>

            {formData.current_property_id && (
              <div>
                <label htmlFor="unit_id" className="block text-sm font-medium text-gray-700">
                  Unit {propertyUnits.length === 0 ? '' : <span className="text-red-600">*</span>}
                </label>
                {propertyUnits.length > 0 ? (
                  <>
                    <select
                      id="unit_id"
                      name="unit_id"
                      value={formData.unit_id}
                      onChange={handleChange}
                      className={getInputClassName('unit_id')}
                      disabled={!formData.current_property_id || propertyUnits.length === 0}
                    >
                      <option value="">Select a unit</option>
                      {propertyUnits.map((unit) => (
                        <option key={unit.id} value={unit.id}>
                          {unit.unit_number}
                        </option>
                      ))}
                    </select>
                    {fieldErrors.unit_id && !fieldErrors.unit && (
                      <p className="mt-1 text-sm text-red-600">{fieldErrors.unit_id}</p>
                    )}
                  </>
                ) : (
                  <p className="mt-1 text-sm text-amber-600">
                    No units available for this property.
                  </p>
                )}
              </div>
            )}

            <div>
              <label htmlFor="unit" className="block text-sm font-medium text-gray-700">
                Unit Number (Manual) {(!formData.unit_id || propertyUnits.length === 0) && <span className="text-red-600">*</span>}
              </label>
              <input
                type="text"
                id="unit"
                name="unit"
                value={formData.unit}
                onChange={handleChange}
                className={getInputClassName('unit')}
                placeholder="For properties without unit records"
              />
              {fieldErrors.unit && !fieldErrors.unit_id && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.unit}</p>
              )}
              {propertyUnits.length === 0 && formData.current_property_id ? (
                <p className="mt-1 text-xs text-gray-500">Please enter unit information manually</p>
              ) : (
                <p className="mt-1 text-xs text-gray-500">Required if no unit is selected above</p>
              )}
            </div>

            <div>
              <label htmlFor="lease_start" className="block text-sm font-medium text-gray-700">
                Lease Start Date <span className="text-red-600">*</span>
              </label>
              <input
                type="date"
                id="lease_start"
                name="lease_start"
                value={formData.lease_start}
                onChange={handleChange}
                required
                className={getInputClassName('lease_start')}
              />
              {fieldErrors.lease_start && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.lease_start}</p>
              )}
            </div>

            <div>
              <label htmlFor="lease_end" className="block text-sm font-medium text-gray-700">
                Lease End Date <span className="text-red-600">*</span>
              </label>
              <input
                type="date"
                id="lease_end"
                name="lease_end"
                value={formData.lease_end}
                onChange={handleChange}
                required
                className={getInputClassName('lease_end')}
              />
              {fieldErrors.lease_end && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.lease_end}</p>
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
                  required
                  className={`${getInputClassName('monthly_rent')} pl-7`}
                />
              </div>
              {fieldErrors.monthly_rent && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.monthly_rent}</p>
              )}
            </div>

            <div>
              <label htmlFor="status" className="block text-sm font-medium text-gray-700">
                Status <span className="text-red-600">*</span>
              </label>
              <select
                id="status"
                name="status"
                value={formData.status}
                onChange={handleChange}
                required
                className={getInputClassName('status')}
              >
                <option value="">Select a status</option>
                <option value="Active">Active</option>
                <option value="Inactive">Inactive</option>
                <option value="Pending">Pending</option>
                <option value="Evicted">Evicted</option>
                <option value="Moved Out">Moved Out</option>
              </select>
              {fieldErrors.status && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.status}</p>
              )}
            </div>

            <div>
              <label htmlFor="leasing_agent" className="block text-sm font-medium text-gray-700">
                Leasing Agent
              </label>
              <input
                type="text"
                id="leasing_agent"
                name="leasing_agent"
                value={formData.leasing_agent}
                onChange={handleChange}
                className={getInputClassName('leasing_agent')}
              />
              {fieldErrors.leasing_agent && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.leasing_agent}</p>
              )}
            </div>
          </div>

          <div className="mt-2 text-sm text-gray-700">
            <span className="text-red-600">*</span> Required fields
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
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Saving...
                </>
              ) : (
                'Save'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TenantModal; 