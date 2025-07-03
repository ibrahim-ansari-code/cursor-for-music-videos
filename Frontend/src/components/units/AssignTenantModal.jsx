import { AnimatePresence, motion } from "framer-motion";
import React, { useState, useEffect, useRef } from "react";
import {
  fetchTenants,
  createLease,
} from "../../utils/api";
import TenantModal from "../tenants/TenantModal";

const AssignTenantModal = ({ isOpen, onClose, unit, propertyId, onSuccess }) => {
  // State Management
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isLoadingTenants, setIsLoadingTenants] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  
  // Tenant Selection State
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [tenantSearchTerm, setTenantSearchTerm] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  
  // Lease Form Data
  const [leaseData, setLeaseData] = useState({
    start_date: new Date().toISOString().split('T')[0],
    end_date: "",
    monthly_rent: unit?.monthly_rent || "",
    security_deposit: "",
    rent_due_day: 1,
    late_fee_amount: "",
    late_fee_after_days: "",
    special_terms: "",
  });
  
  // Child Modal State
  const [showTenantModal, setShowTenantModal] = useState(false);
  
  // Add state for custom rent due day
  const [rentDueOption, setRentDueOption] = useState('1'); // '1', '15', 'last', or 'custom'
  const [customRentDueDay, setCustomRentDueDay] = useState('');

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      loadTenants();
      // Reset form when opening
      setSelectedTenant(null);
      setTenantSearchTerm("");
      setLeaseData({
        start_date: new Date().toISOString().split('T')[0],
        end_date: "",
        monthly_rent: unit?.monthly_rent || "",
        security_deposit: "",
        rent_due_day: 1,
        late_fee_amount: "",
        late_fee_after_days: "",
        special_terms: "",
      });
      setError(null);
      setFieldErrors({});
      setRentDueOption('1');
      setCustomRentDueDay('');
    }
  }, [isOpen, unit]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadTenants = async () => {
    setIsLoadingTenants(true);
    try {
      const data = await fetchTenants({ unassigned_only: true });
      setTenants(data || []);
    } catch (err) {
      console.error("Error loading tenants:", err);
      setError("Failed to load tenants");
    } finally {
      setIsLoadingTenants(false);
    }
  };

  const handleSelectTenant = (tenant) => {
    setSelectedTenant(tenant);
    setTenantSearchTerm(`${tenant.first_name} ${tenant.last_name}`);
    setIsDropdownOpen(false);
  };

  const handleCreateNewTenant = () => {
    setIsDropdownOpen(false);
    setShowTenantModal(true);
  };

  const handleTenantSaved = (newTenant) => {
    setShowTenantModal(false);
    setTenants(prev => [newTenant, ...prev]);
    handleSelectTenant(newTenant);
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    
    // Clear field error when user starts typing
    if (fieldErrors[name]) {
      setFieldErrors(prev => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }

    setLeaseData(prev => ({ ...prev, [name]: value }));
  };
  
  const handleRentDueOptionChange = (option) => {
    setRentDueOption(option);
    
    // Update the actual rent_due_day value based on selection
    if (option === '1') {
      setLeaseData(prev => ({ ...prev, rent_due_day: 1 }));
    } else if (option === '15') {
      setLeaseData(prev => ({ ...prev, rent_due_day: 15 }));
    } else if (option === 'last') {
      setLeaseData(prev => ({ ...prev, rent_due_day: -1 })); // -1 indicates last day of month
    }
    // For custom, we'll update when they enter a value
  };
  
  const handleCustomRentDueChange = (value) => {
    setCustomRentDueDay(value);
    const day = parseInt(value);
    if (!isNaN(day) && day >= 1 && day <= 31) {
      setLeaseData(prev => ({ ...prev, rent_due_day: day }));
    }
  };

  const validateForm = () => {
    const errors = {};

    if (!selectedTenant) errors.tenant = "Please select a tenant";
    if (!leaseData.start_date) errors.start_date = "Start date is required";
    if (!leaseData.end_date) errors.end_date = "End date is required";
    if (!leaseData.monthly_rent) errors.monthly_rent = "Monthly rent is required";
    if (!leaseData.security_deposit) errors.security_deposit = "Security deposit is required";

    // Date validation using UTC to avoid timezone issues
    if (leaseData.start_date && leaseData.end_date) {
      // Create UTC dates for comparison to avoid timezone issues
      const startUTC = new Date(leaseData.start_date + 'T00:00:00.000Z');
      const endUTC = new Date(leaseData.end_date + 'T00:00:00.000Z');
      if (startUTC >= endUTC) {
        errors.end_date = "End date must be after start date";
      }
    }

    return errors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate form
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setError("Please correct the validation errors below.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Create the lease
      const leasePayload = {
        property_id: parseInt(propertyId),
        unit_id: unit.id,
        tenant_id: selectedTenant.id,
        status: "ACTIVE",
        ...leaseData,
        monthly_rent: parseFloat(leaseData.monthly_rent),
        security_deposit: parseFloat(leaseData.security_deposit),
        rent_due_day: parseInt(leaseData.rent_due_day),
        late_fee_amount: leaseData.late_fee_amount ? parseFloat(leaseData.late_fee_amount) : null,
        late_fee_after_days: leaseData.late_fee_after_days ? parseInt(leaseData.late_fee_after_days) : null,
        special_terms: leaseData.special_terms || null,
      };

      const createdLease = await createLease(leasePayload);
      
      // Call success callback
      if (onSuccess) {
        onSuccess(createdLease);
      }
      
      onClose();
    } catch (err) {
      console.error("Error creating lease:", err);
      setError(err.message || "Failed to create lease");
    } finally {
      setLoading(false);
    }
  };

  const filteredTenants = tenants.filter(
    (t) =>
      `${t.first_name} ${t.last_name}`.toLowerCase().includes(tenantSearchTerm.toLowerCase()) ||
      (t.email && t.email.toLowerCase().includes(tenantSearchTerm.toLowerCase()))
  );

  return (
    <>
      <AnimatePresence>
        {isOpen && !showTenantModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
            onClick={onClose}
          >
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 400 }}
              className="relative w-full max-w-2xl bg-white rounded-xl shadow-xl max-h-[85vh] overflow-hidden flex flex-col z-[10000]"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="relative px-6 py-4 bg-gradient-to-br from-brand-green to-brand-teal text-white">
                <div className="flex justify-between items-center">
                  <div>
                    <h2 className="text-xl font-semibold text-white">Create Lease Agreement</h2>
                    <p className="text-white/80 mt-0.5 text-sm">Assign {selectedTenant ? `${selectedTenant.first_name} ${selectedTenant.last_name}` : 'a tenant'} to {unit?.name || 'Unit'}</p>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-white/70 hover:text-white hover:bg-white/10 p-1.5 rounded-lg transition-all"
                  >
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Content */}
              <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto bg-gray-50">
                {error && (
                  <motion.div 
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mx-6 mt-4 p-3 bg-red-50 border border-red-100 text-red-700 rounded-lg"
                  >
                    <div className="flex">
                      <svg className="h-5 w-5 text-red-400 mr-2 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                      <span className="text-sm">{error}</span>
                    </div>
                  </motion.div>
                )}

                <div className="p-6 space-y-4">
                  {/* Tenant Section */}
                  <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                    <div className="flex items-center mb-3">
                      <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center mr-3">
                        <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                      <h3 className="text-base font-medium text-gray-900">Tenant Information</h3>
                    </div>
                    
                    <div ref={dropdownRef}>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Select Tenant <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <input 
                          type="text" 
                          placeholder="Search for existing tenant or create new" 
                          value={tenantSearchTerm} 
                          onChange={(e) => {
                            setTenantSearchTerm(e.target.value);
                            setIsDropdownOpen(true);
                          }} 
                          onFocus={() => setIsDropdownOpen(true)}
                          className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${
                            fieldErrors.tenant ? 'border-red-300' : 'border-gray-200'
                          }`}
                        />
                        <AnimatePresence>
                          {isDropdownOpen && (
                            <motion.div 
                              initial={{ opacity: 0, y: -10 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -10 }}
                              className="absolute z-10 mt-2 w-full bg-white shadow-lg rounded-lg border border-gray-100 max-h-48 overflow-y-auto"
                            >
                              {isLoadingTenants ? (
                                <div className="p-3 text-sm text-gray-500">Loading...</div>
                              ) : (
                                <ul>
                                  {filteredTenants.map(t => (
                                    <li 
                                      key={t.id} 
                                      onClick={() => handleSelectTenant(t)} 
                                      className="p-3 hover:bg-gray-50 cursor-pointer text-sm border-b border-gray-100 last:border-b-0 transition-colors"
                                    >
                                      <div className="font-medium text-gray-900">{t.first_name} {t.last_name}</div>
                                      {t.email && <div className="text-gray-500 text-xs mt-0.5">{t.email}</div>}
                                    </li>
                                  ))}
                                  <li 
                                    onClick={handleCreateNewTenant} 
                                    className="p-3 hover:bg-blue-50 cursor-pointer text-sm font-medium text-blue-600 bg-gray-50"
                                  >
                                    <div className="flex items-center">
                                      <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                                      </svg>
                                      Create New Tenant
                                    </div>
                                  </li>
                                </ul>
                              )}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                      {fieldErrors.tenant && (
                        <p className="mt-2 text-sm text-red-600">{fieldErrors.tenant}</p>
                      )}
                    </div>
                  </div>

                  {/* Lease Terms Section */}
                  <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                    <div className="flex items-center mb-3">
                      <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center mr-3">
                        <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </div>
                      <h3 className="text-base font-medium text-gray-900">Lease Duration</h3>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Start Date <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="date"
                          name="start_date"
                          value={leaseData.start_date}
                          onChange={handleFormChange}
                          className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${
                            fieldErrors.start_date ? 'border-red-300' : 'border-gray-200'
                          }`}
                          required
                        />
                        {fieldErrors.start_date && (
                          <p className="mt-2 text-sm text-red-600">{fieldErrors.start_date}</p>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          End Date <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="date"
                          name="end_date"
                          value={leaseData.end_date}
                          onChange={handleFormChange}
                          min={leaseData.start_date}
                          className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${
                            fieldErrors.end_date ? 'border-red-300' : 'border-gray-200'
                          }`}
                          required
                        />
                        {fieldErrors.end_date && (
                          <p className="mt-2 text-sm text-red-600">{fieldErrors.end_date}</p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Financial Terms Section */}
                  <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                    <div className="flex items-center mb-3">
                      <div className="w-9 h-9 bg-yellow-50 rounded-lg flex items-center justify-center mr-3">
                        <svg className="w-4 h-4 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <h3 className="text-base font-medium text-gray-900">Financial Terms</h3>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Monthly Rent <span className="text-red-500">*</span>
                        </label>
                        <div className="relative">
                          <span className="absolute left-4 top-2.5 text-gray-500 font-medium">$</span>
                          <input
                            type="number"
                            name="monthly_rent"
                            value={leaseData.monthly_rent}
                            onChange={handleFormChange}
                            className={`w-full pl-10 pr-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${
                              fieldErrors.monthly_rent ? 'border-red-300' : 'border-gray-200'
                            } [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none`}
                            placeholder="0.00"
                            step="0.01"
                            min="0"
                            required
                          />
                        </div>
                        {fieldErrors.monthly_rent && (
                          <p className="mt-2 text-sm text-red-600">{fieldErrors.monthly_rent}</p>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Security Deposit <span className="text-red-500">*</span>
                        </label>
                        <div className="relative">
                          <span className="absolute left-4 top-2.5 text-gray-500 font-medium">$</span>
                          <input
                            type="number"
                            name="security_deposit"
                            value={leaseData.security_deposit}
                            onChange={handleFormChange}
                            className={`w-full pl-10 pr-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${
                              fieldErrors.security_deposit ? 'border-red-300' : 'border-gray-200'
                            } [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none`}
                            placeholder="0.00"
                            step="0.01"
                            min="0"
                            required
                          />
                        </div>
                        {fieldErrors.security_deposit && (
                          <p className="mt-2 text-sm text-red-600">{fieldErrors.security_deposit}</p>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          When is Rent Due?
                        </label>
                        <div className="space-y-1.5 bg-gray-50 p-3 rounded-lg">
                          <label className="flex items-center cursor-pointer hover:text-blue-600 transition-colors py-1">
                            <input
                              type="radio"
                              name="rent_due_option"
                              value="1"
                              checked={rentDueOption === '1'}
                              onChange={(e) => handleRentDueOptionChange(e.target.value)}
                              className="mr-2.5 text-blue-600 focus:ring-blue-500"
                            />
                            <span className="text-sm">1st of every month</span>
                          </label>
                          <label className="flex items-center cursor-pointer hover:text-blue-600 transition-colors py-1">
                            <input
                              type="radio"
                              name="rent_due_option"
                              value="15"
                              checked={rentDueOption === '15'}
                              onChange={(e) => handleRentDueOptionChange(e.target.value)}
                              className="mr-2.5 text-blue-600 focus:ring-blue-500"
                            />
                            <span className="text-sm">15th of every month</span>
                          </label>
                          <label className="flex items-center cursor-pointer hover:text-blue-600 transition-colors py-1">
                            <input
                              type="radio"
                              name="rent_due_option"
                              value="last"
                              checked={rentDueOption === 'last'}
                              onChange={(e) => handleRentDueOptionChange(e.target.value)}
                              className="mr-2.5 text-blue-600 focus:ring-blue-500"
                            />
                            <span className="text-sm">Last day of every month</span>
                          </label>
                          <div className="flex items-center py-1">
                            <label className="flex items-center cursor-pointer hover:text-blue-600 transition-colors">
                              <input
                                type="radio"
                                name="rent_due_option"
                                value="custom"
                                checked={rentDueOption === 'custom'}
                                onChange={(e) => handleRentDueOptionChange(e.target.value)}
                                className="mr-2.5 text-blue-600 focus:ring-blue-500"
                              />
                              <span className="text-sm">Other day:</span>
                            </label>
                            {rentDueOption === 'custom' && (
                              <input
                                type="number"
                                value={customRentDueDay}
                                onChange={(e) => handleCustomRentDueChange(e.target.value)}
                                className="ml-2 w-16 px-2 py-1 border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                                placeholder="e.g. 5"
                                min="1"
                                max="31"
                              />
                            )}
                          </div>
                        </div>
                        <p className="mt-1.5 text-xs text-gray-500">
                          For months with fewer days, the last valid day will be used
                        </p>
                      </div>
                      
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Late Fee Amount
                          </label>
                          <div className="relative">
                            <span className="absolute left-4 top-2.5 text-gray-500 font-medium">$</span>
                            <input
                              type="number"
                              name="late_fee_amount"
                              value={leaseData.late_fee_amount}
                              onChange={handleFormChange}
                              className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                              placeholder="50.00"
                              step="0.01"
                              min="0"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Grace Period Before Late Fee
                          </label>
                          <div className="relative">
                            <input
                              type="number"
                              name="late_fee_after_days"
                              value={leaseData.late_fee_after_days}
                              onChange={handleFormChange}
                              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                              placeholder="5"
                              min="0"
                            />
                            <span className="absolute right-4 top-2.5 text-gray-500 text-sm">days</span>
                          </div>
                          <p className="mt-1 text-xs text-gray-500">
                            Number of days after due date before late fee applies
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Special Terms Section */}
                  <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                    <div className="flex items-center mb-3">
                      <div className="w-9 h-9 bg-purple-50 rounded-lg flex items-center justify-center mr-3">
                        <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <h3 className="text-base font-medium text-gray-900">Additional Terms</h3>
                    </div>
                    
                    <textarea
                      name="special_terms"
                      rows="4"
                      value={leaseData.special_terms}
                      onChange={handleFormChange}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none bg-white"
                      placeholder="Enter any special conditions, pet policies, utilities arrangements, or other lease terms..."
                    />
                  </div>
                </div>
              </form>

              {/* Footer */}
              <div className="px-6 py-5 bg-gray-50 border-t border-gray-200">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div className="text-sm text-gray-500 flex items-start flex-1 sm:max-w-md">
                    <svg className="w-4 h-4 mr-2 text-gray-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>This will create an active lease in your system. You can upload documents and set other lease details on the Leases page.</span>
                  </div>
                  <div className="flex gap-3 flex-shrink-0 sm:items-center">
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-4 py-2.5 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all text-sm font-medium"
                      disabled={loading}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSubmit}
                      className="px-5 py-2.5 bg-gradient-to-br from-brand-green to-brand-teal text-white rounded-md hover:from-brand-green/90 hover:to-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-green focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium flex items-center gap-2 min-w-[160px] justify-center shadow-sm"
                      disabled={loading || !selectedTenant}
                    >
                      {loading ? (
                        <>
                          <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Creating...
                        </>
                      ) : (
                        'Create Lease Agreement'
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tenant Modal */}
      <AnimatePresence>
        {showTenantModal && (
          <TenantModal
            isOpen={true}
            onClose={() => setShowTenantModal(false)}
            onSave={handleTenantSaved}
            propertyId={propertyId}
          />
        )}
      </AnimatePresence>
    </>
  );
};

export default AssignTenantModal;