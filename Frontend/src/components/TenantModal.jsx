import React, { useState, useEffect } from 'react';
import { createTenant, updateTenant } from '../utils/api';
import { getInputClassName } from '../utils/formUtils';

const TenantModal = ({ isOpen, onClose, tenant = null, onSave, source }) => {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    status: 'active',
    current_property_id: null,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: ''
  });
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [touched, setTouched] = useState({
    first_name: false,
    last_name: false,
    phone: false,
    email: false,
  });
  const [submitAttempted, setSubmitAttempted] = useState(false);

  // Sync tenant prop to formData state
  useEffect(() => {
    if (tenant) {
      console.log('TenantModal - tenant prop received:', tenant);
      
      // Handle both the old format (full_name) and new format (first_name, last_name)
      let first = '';
      let last = '';
      
      if (tenant.first_name && tenant.last_name) {
        // New format
        first = tenant.first_name;
        last = tenant.last_name;
      } else if (tenant.full_name) {
        // Old format - split full_name into first_name and last_name
        const nameParts = tenant.full_name.split(' ');
        first = nameParts[0] || '';
        last = nameParts.slice(1).join(' ') || '';
      }
      
      const updatedFormData = {
        first_name: first,
        last_name: last,
        phone: tenant.phone || '',
        email: tenant.email || '',
        status: tenant.status || 'active',
        current_property_id: tenant.current_property_id || null,
      };

      console.log('TenantModal - updating formData:', updatedFormData);
      setFormData(updatedFormData);
      
      // Clear any previous errors
      setFieldErrors({});
      setError(null);
    } else {
      // New tenant flow
      setFormData({
        first_name: '',
        last_name: '',
        phone: '',
        email: '',
        status: 'active',
        current_property_id: null,
      });
    }
  }, [tenant, isOpen]);

  // Handle form field changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Mark field as touched
    setTouched(prev => ({
      ...prev,
      [name]: true
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
    const newErrors = {};
    let isValid = true;

    if (!formData.first_name || formData.first_name.trim() === "") {
      newErrors.first_name = "First name is required";
      isValid = false;
    }

    if (!formData.last_name || formData.last_name.trim() === "") {
      newErrors.last_name = "Last name is required";
      isValid = false;
    }

    if (!formData.email || formData.email.trim() === "") {
      newErrors.email = "Email is required";
      isValid = false;
    } else {
      // More robust email validation
      const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      if (!emailRegex.test(formData.email.trim())) {
        newErrors.email = "Please enter a valid email address";
        isValid = false;
      }
    }

    if (!formData.phone || formData.phone.trim() === "") {
      newErrors.phone = "Phone number is required";
      isValid = false;
    } else if (!/^[0-9]{10,15}$/.test(formData.phone.replace(/[^0-9]/g, ''))) {
      newErrors.phone = "Invalid phone number format (must contain 10-15 digits)";
      isValid = false;
    }

    setFieldErrors(newErrors);
    setTouched({
      first_name: true,
      last_name: true,
      email: true,
      phone: true,
    });
    setSubmitAttempted(true);
    
    return isValid;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormSubmitted(true);
    
    // Clear all previous errors
    setError(null);
    setFieldErrors({});
    setApiError(null);
    
    // Get the current values directly from the form elements to ensure we have the latest
    const formElements = e.target.elements;
    const currentFormData = {
      first_name: formElements.first_name.value.trim(),
      last_name: formElements.last_name.value.trim(),
      phone: formElements.phone.value.trim(),
      email: formElements.email.value.trim(),
      status: formData.status,
      current_property_id: formData.current_property_id,
      user_id: null // Explicitly set user_id to null for new tenants
    };
    
    // Update the form data state with the latest values
    setFormData(currentFormData);
    
    if (!validateForm()) {
      return;
    }
    
    setIsLoading(true);

    try {
      // Extract only the fields that belong to the Tenant model
      const tenantPayload = {
        first_name: currentFormData.first_name,
        last_name: currentFormData.last_name,
        phone: currentFormData.phone,
        email: currentFormData.email,
        // Convert status to title case (first letter uppercase, rest lowercase)
        status: (currentFormData.status || 'active').charAt(0).toUpperCase() + (currentFormData.status || 'active').slice(1).toLowerCase(),
        current_property_id: currentFormData.current_property_id,
        user_id: null // Explicitly set user_id to null for new tenants
      };
      
      // Log the payload for debugging
      console.log('Sending tenant payload to server:', tenantPayload);
      
      // Remove undefined fields to avoid validation errors
      Object.keys(tenantPayload).forEach(key => 
        tenantPayload[key] === undefined && delete tenantPayload[key]
      );
      
      let response;
      // Only update if tenant exists and has an ID
      if (tenant && tenant.id) {
        console.log(`Updating existing tenant with ID: ${tenant.id}`, tenantPayload);
        // For updates, don't change the user_id to avoid unique constraint issues
        if (tenant.user_id) {
          tenantPayload.user_id = tenant.user_id;
        }
        // Update existing tenant
        response = await updateTenant(tenant.id, tenantPayload);
      } else {
        console.log('Creating new tenant:', tenantPayload);
        // Create new tenant
        response = await createTenant(tenantPayload);
      }

      console.log('Tenant created/updated successfully:', response);

      if (onSave) {
        onSave(response);
      }
      
      if (!source || source !== "importLeaseModal") {
        onClose();
      }
    } catch (err) {
      console.error('Failed to save tenant:', err);
      
      // Enhanced error debugging
      console.error('Error status:', err.status);
      console.error('Error name:', err.name);
      console.error('Error message:', err.message);
      
      // Log more details about the error for debugging
      if (err.data) {
        console.error('Error data:', err.data);
      }
      if (err.rawResponse) {
        console.error('Raw error response:', err.rawResponse);
        try {
          const rawError = JSON.parse(err.rawResponse);
          console.error('Parsed raw error:', rawError);
        } catch (e) {
          console.error('Could not parse raw error response');
        }
      }
      
      // Handle different error scenarios
      if (err.status === 422) {
        // Validation error from backend
        handleValidationError(err);
        
        // Check specifically for email issues
        if (err.data?.detail && Array.isArray(err.data.detail)) {
          const emailErrors = err.data.detail.filter(e => 
            e.loc && e.loc.length > 1 && e.loc[1] === 'email'
          );
          
          const userIdErrors = err.data.detail.filter(e => 
            e.loc && e.loc.length > 1 && e.loc[1] === 'user_id'
          );
          
          if (userIdErrors.length > 0) {
            setFieldErrors(prev => ({
              ...prev,
              user_id: "There's a constraint error with the user_id. Try a different tenant."
            }));
            setError("There's a database constraint issue. Please try with different information.");
          } else if (emailErrors.length > 0) {
            // We have specific email-related errors
            setFieldErrors(prev => ({
              ...prev,
              email: emailErrors[0].msg || "Invalid email format or email already in use"
            }));
            setError("There seems to be an issue with the email address. It may be invalid or already in use.");
          } else {
            setError("Please correct the validation errors below.");
          }
        } else {
          // Generic validation error
          setError("Failed to validate tenant information. Please check your input and try again.");
        }
      } else if (err.status === 401 || err.status === 403) {
        // Authentication/authorization error
        setError('You are not authorized to perform this action. Please check your permissions.');
      } else if (err.status === 404) {
        // Not found error
        setError('The requested resource was not found. Please refresh and try again.');
      } else if (err.status === 500) {
        // Server error
        setError('An unexpected server error occurred. Please try again later.');
      } else {
        // Generic error handling
        setError('Failed to save tenant. Please check your connection and try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Helper function to handle validation errors from the backend
  const handleValidationError = (err) => {
    console.log('Handling validation error:', err);
    
    if (err.data?.detail) {
      // Handle field validation errors
      if (Array.isArray(err.data.detail)) {
        const validationErrors = {};
        const generalErrors = [];
        
        err.data.detail.forEach(error => {
          console.log('Validation error detail:', error);
          if (error.loc && error.loc.length > 1) {
            // This is a field-specific error
            const fieldName = error.loc[1];
            validationErrors[fieldName] = error.msg;
            
            // Log which field has the error for debugging
            console.log(`Field ${fieldName} has error: ${error.msg}`);
          } else {
            // This is a general error
            generalErrors.push(error.msg);
          }
        });
        
        // Check specifically for email-related errors in the response
        const emailErrors = err.data.detail.filter(error => 
          error.loc && error.loc.length > 1 && error.loc[1] === 'email'
        );
        
        if (emailErrors.length > 0) {
          console.log('Email validation errors found:', emailErrors);
        }
        
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
      // If we got a raw error message without structure, use it directly
      const errorMessage = err.message || 'Validation failed. Please check your input and try again.';
      setError(errorMessage);
      console.error('Raw error response:', err);
    }
  };

  // Wrap getInputClassName in a try-catch block
  const safeGetInputClassName = (field) => {
    try {
      const errors = fieldErrors || {};
      const data = formData || {};
      return getInputClassName(field, errors, formSubmitted, data);
    } catch (error) {
      console.error(`Error getting input class name for ${field}:`, error);
      return 'border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm'; // Fallback class
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-75 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
      <div className="relative p-6 border w-full max-w-md shadow-lg rounded-lg bg-white">
        <div className="flex justify-between items-center mb-5">
          <h2 className="text-xl font-bold text-gray-800">
            {tenant && tenant.id ? 'Edit Tenant' : 'Add Tenant'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors duration-150"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"></path>
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        {apiError && (
          <div className="alert alert-danger mb-3" role="alert">
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-4">
            <div className="mb-3">
              <label htmlFor="first_name" className="form-label">
                First Name<span className="text-red-600 font-bold text-lg">*</span>
              </label>
              <input
                type="text"
                className={safeGetInputClassName("first_name")}
                id="first_name"
                name="first_name"
                placeholder="Enter first name"
                value={formData.first_name || ""}
                onChange={handleChange}
              />
              {fieldErrors.first_name && (touched.first_name || submitAttempted) && (
                <div className="mt-1 text-sm text-red-600">{fieldErrors.first_name}</div>
              )}
            </div>

            <div className="mb-3">
              <label htmlFor="last_name" className="form-label">
                Last Name<span className="text-red-600 font-bold text-lg">*</span>
              </label>
              <input
                type="text"
                className={safeGetInputClassName("last_name")}
                id="last_name"
                name="last_name"
                placeholder="Enter last name"
                value={formData.last_name || ""}
                onChange={handleChange}
              />
              {fieldErrors.last_name && (touched.last_name || submitAttempted) && (
                <div className="mt-1 text-sm text-red-600">{fieldErrors.last_name}</div>
              )}
            </div>

            <div className="mb-3">
              <label htmlFor="phone" className="form-label">
                Phone Number<span className="text-red-600 font-bold text-lg">*</span>
              </label>
              <input
                type="tel"
                className={safeGetInputClassName("phone")}
                id="phone"
                name="phone"
                placeholder="Enter phone number"
                value={formData.phone || ""}
                onChange={handleChange}
              />
              {fieldErrors.phone && (touched.phone || submitAttempted) && (
                <div className="mt-1 text-sm text-red-600">{fieldErrors.phone}</div>
              )}
            </div>

            <div className="mb-3">
              <label htmlFor="email" className="form-label">
                Email<span className="text-red-600 font-bold text-lg">*</span>
              </label>
              <input
                type="email"
                className={safeGetInputClassName("email")}
                id="email"
                name="email"
                placeholder="Enter email"
                value={formData.email || ""}
                onChange={handleChange}
              />
              {fieldErrors.email && (touched.email || submitAttempted) && (
                <div className="mt-1 text-sm text-red-600">{fieldErrors.email}</div>
              )}
            </div>
          </div>

          <div className="mt-2 mb-4 text-sm text-gray-500">
            <span className="text-red-600 font-bold">*</span> Required fields
          </div>

          <div className="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-100">
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
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
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