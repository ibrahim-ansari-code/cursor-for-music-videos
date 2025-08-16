import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "react-toastify";
import { fetchTenants } from "../../utils/api";
import { bulkAssignTenant } from "../../utils/api/units";
import TenantModal from "../tenants/TenantModal";

const BulkAssignTenantModal = ({
    isOpen,
    onClose,
    selectedUnits = [],
    propertyId,
    onSuccess
}) => {
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
        lease_start_date: new Date().toISOString().split('T')[0],
        end_date: "",
        monthly_rent: "",
        security_deposit: "",
        rent_due_day: 1,
        late_fee_amount: "",
        late_fee_after_days: "",
        special_terms: "",
    });

    // Add state for custom rent due day
    const [rentDueOption, setRentDueOption] = useState('1'); // '1', '15', 'last', or 'custom'
    const [customRentDueDay, setCustomRentDueDay] = useState('');

    // Child Modal State
    const [showTenantModal, setShowTenantModal] = useState(false);

    // Assignment Results
    const [assignmentResults, setAssignmentResults] = useState(null);
    const [showResults, setShowResults] = useState(false);

    // Reset state when modal opens
    useEffect(() => {
        if (isOpen) {
            loadTenants();
            setSelectedTenant(null);
            setTenantSearchTerm("");
            setLeaseData({
                lease_start_date: new Date().toISOString().split('T')[0],
                end_date: "",
                monthly_rent: "",
                security_deposit: "",
                rent_due_day: 1,
                late_fee_amount: "",
                late_fee_after_days: "",
                special_terms: "",
            });
            setError(null);
            setFieldErrors({});
            setAssignmentResults(null);
            setShowResults(false);
            setRentDueOption('1');
            setCustomRentDueDay('');
        }
    }, [isOpen]);

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
        // Clear tenant field error when selecting
        if (fieldErrors.tenant) {
            setFieldErrors(prev => {
                const updated = { ...prev };
                delete updated.tenant;
                return updated;
            });
        }
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

    const handleChange = (e) => {
        const { name, value } = e.target;

        // Clear field error when user starts typing
        if (fieldErrors[name]) {
            setFieldErrors(prev => {
                const updated = { ...prev };
                delete updated[name];
                return updated;
            });
        }

        setLeaseData(prev => ({
            ...prev,
            [name]: value
        }));
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
        setRentDueOption('custom');
        const day = parseInt(value);
        if (!isNaN(day) && day >= 1 && day <= 31) {
            setLeaseData(prev => ({ ...prev, rent_due_day: day }));
        }
    };

    const validateForm = () => {
        const errors = {};

        if (!selectedTenant) errors.tenant = "Please select a tenant";
        if (!leaseData.lease_start_date) errors.lease_start_date = "Lease start date is required";
        if (!leaseData.end_date) errors.end_date = "Lease end date is required";
        if (!leaseData.security_deposit) errors.security_deposit = "Security deposit is required";

        // Date validation using local dates to match user expectations
        if (leaseData.lease_start_date && leaseData.end_date) {
            const startLocal = new Date(leaseData.lease_start_date);
            const endLocal = new Date(leaseData.end_date);
            const now = new Date();
            const todayLocal = new Date(now.getFullYear(), now.getMonth(), now.getDate());

            if (startLocal.getTime() < todayLocal.getTime()) {
                // Allow today's date, but not past dates
                errors.lease_start_date = "Lease start date cannot be in the past";
            }

            if (startLocal.getTime() >= endLocal.getTime()) {
                errors.end_date = "End date must be after start date";
            }
        }

        // Validate rent_due_day especially for custom option
        if (rentDueOption === 'custom') {
            const day = parseInt(leaseData.rent_due_day, 10);
            if (isNaN(day) || day < 1 || day > 31) {
                errors.rent_due_day = "Rent due day must be between 1 and 31";
            }
        }

        // Validate security_deposit is non-negative number
        if (leaseData.security_deposit !== '') {
            const deposit = parseFloat(leaseData.security_deposit);
            if (isNaN(deposit) || deposit < 0) {
                errors.security_deposit = "Security deposit must be 0 or greater";
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
            // Helper function to safely parse float values
            const safeParseFloat = (value) => {
                if (!value || value.trim() === '') return null;
                const parsed = parseFloat(value);
                return isNaN(parsed) ? null : parsed;
            };

            // Helper function to safely parse integer values  
            const safeParseInt = (value) => {
                if (value === null || value === undefined) return null;
                const str = String(value).trim();
                if (str === '') return null;
                const parsed = parseInt(str, 10);
                return Number.isFinite(parsed) ? parsed : null;
            };

            const bulkData = {
                unit_ids: selectedUnits.map(unit => unit.id),
                tenant_id: selectedTenant.id,
                lease_start_date: leaseData.lease_start_date,
                end_date: leaseData.end_date,
                monthly_rent: safeParseFloat(leaseData.monthly_rent),
                security_deposit: safeParseFloat(leaseData.security_deposit) || 0, // Required field, default to 0
                rent_due_day: (() => {
                    const parsed = safeParseInt(leaseData.rent_due_day);
                    return parsed !== null ? parsed : 1; // Only default to 1 when null, preserve 0 and -1
                })(),
                late_fee_amount: safeParseFloat(leaseData.late_fee_amount),
                late_fee_after_days: safeParseInt(leaseData.late_fee_after_days),
                special_terms: leaseData.special_terms || null,
            };

            const response = await bulkAssignTenant(bulkData);
            
            // Guard against missing or malformed API responses
            if (!response || typeof response !== 'object') {
                throw new Error('Invalid or missing response from bulk assignment API');
            }

            const successfulAssignments = response.successful_assignments ?? 0;
            const failedAssignments = response.failed_assignments ?? 0;
            
            setAssignmentResults(response);
            setShowResults(true);

            if (successfulAssignments > 0) {
                toast.success(`Successfully assigned tenant to ${successfulAssignments} units`);
                if (onSuccess) {
                    onSuccess(response);
                }
            }

            if (failedAssignments > 0) {
                toast.warning(`${failedAssignments} assignments failed. Check results for details.`);
            }
        } catch (err) {
            console.error("Error during bulk assignment:", err);
            setError(err.message || "Failed to assign tenant to units");
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setSelectedTenant(null);
        setTenantSearchTerm("");
        setLeaseData({
            lease_start_date: new Date().toISOString().split('T')[0],
            end_date: "",
            monthly_rent: "",
            security_deposit: "",
            rent_due_day: 1,
            late_fee_amount: "",
            late_fee_after_days: "",
            special_terms: "",
        });
        setError(null);
        setFieldErrors({});
        setAssignmentResults(null);
        setShowResults(false);
        setRentDueOption('1');
        setCustomRentDueDay('');
        onClose();
    };

    const handleBackToForm = () => {
        setShowResults(false);
        setAssignmentResults(null);
    };

    // Filter tenants based on search
    const filteredTenants = tenants.filter(tenant =>
        `${tenant.first_name} ${tenant.last_name}`.toLowerCase().includes(tenantSearchTerm.toLowerCase()) ||
        (tenant.email && tenant.email.toLowerCase().includes(tenantSearchTerm.toLowerCase()))
    );

    if (!isOpen) return null;

    return (
        <>
            <AnimatePresence>
                {isOpen && !showTenantModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm z-[9999] flex items-center justify-center p-4"
                        onClick={handleClose}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            transition={{ type: "spring", damping: 25, stiffness: 400 }}
                            className="relative w-full max-w-3xl bg-white rounded-xl shadow-xl max-h-[85vh] overflow-hidden flex flex-col z-[10000]"
                            onClick={(e) => e.stopPropagation()}
                        >
                            {/* Header */}
                            <div className="relative px-6 py-4 bg-gradient-to-br from-brand-green to-brand-teal text-white">
                                <div className="flex justify-between items-center">
                                    <div>
                                        <h2 className="text-xl font-semibold text-white">
                                            {showResults ? "Bulk Assignment Results" : "Bulk Assign Tenant"}
                                        </h2>
                                        <p className="text-white/80 mt-0.5 text-sm">
                                            {showResults
                                                ? `Assignment completed for ${selectedUnits.length} selected units`
                                                : `Assign ${selectedTenant ? `${selectedTenant.first_name} ${selectedTenant.last_name}` : 'a tenant'} to ${selectedUnits.length} units`
                                            }
                                        </p>
                                    </div>
                                    <button
                                        onClick={handleClose}
                                        className="text-white/70 hover:text-white hover:bg-white/10 p-1.5 rounded-lg transition-all"
                                    >
                                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>
                            </div>

                            {/* Content */}
                            <div className="flex-1 overflow-y-auto bg-gray-50">
                                {!showResults ? (
                                    /* Form View */
                                    <div>
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

                                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                                            {/* Selected Units Section */}
                                            <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                                                <div className="flex items-center mb-3">
                                                    <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center mr-3">
                                                        <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                                                        </svg>
                                                    </div>
                                                    <h3 className="text-base font-medium text-gray-900">
                                                        Selected Units ({selectedUnits.length})
                                                    </h3>
                                                </div>
                                                <div className="flex flex-wrap gap-2 max-h-20 overflow-y-auto bg-gray-50 p-3 rounded-lg">
                                                    {selectedUnits.map(unit => (
                                                        <span
                                                            key={unit.id}
                                                            className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                                                        >
                                                            {unit.name || unit.id}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>

                                            {/* Tenant Selection Section */}
                                            <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                                                <div className="flex items-center mb-3">
                                                    <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center mr-3">
                                                        <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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
                                                                const newValue = e.target.value;
                                                                setTenantSearchTerm(newValue);
                                                                setIsDropdownOpen(true);
                                                                
                                                                // Only clear selection if search doesn't match current tenant
                                                                if (selectedTenant) {
                                                                    const tenantFullName = `${selectedTenant.first_name} ${selectedTenant.last_name}`;
                                                                    if (!tenantFullName.toLowerCase().includes(newValue.toLowerCase()) && 
                                                                        !selectedTenant.email?.toLowerCase().includes(newValue.toLowerCase())) {
                                                                        setSelectedTenant(null);
                                                                    }
                                                                }
                                                            }}
                                                            onFocus={() => setIsDropdownOpen(true)}
                                                            className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${fieldErrors.tenant ? 'border-red-300' : 'border-gray-200'
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
                                                    <div className="w-9 h-9 bg-yellow-50 rounded-lg flex items-center justify-center mr-3">
                                                        <svg className="w-4 h-4 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                                        </svg>
                                                    </div>
                                                    <h3 className="text-base font-medium text-gray-900">Lease Duration</h3>
                                                </div>

                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                                            Lease Start Date <span className="text-red-500">*</span>
                                                        </label>
                                                        <input
                                                            type="date"
                                                            name="lease_start_date"
                                                            value={leaseData.lease_start_date}
                                                            onChange={handleChange}
                                                            className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${fieldErrors.lease_start_date ? 'border-red-300' : 'border-gray-200'
                                                                }`}
                                                            required
                                                        />
                                                        {fieldErrors.lease_start_date && (
                                                            <p className="mt-2 text-sm text-red-600">{fieldErrors.lease_start_date}</p>
                                                        )}
                                                    </div>
                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                                            Lease End Date <span className="text-red-500">*</span>
                                                        </label>
                                                        <input
                                                            type="date"
                                                            name="end_date"
                                                            value={leaseData.end_date}
                                                            onChange={handleChange}
                                                            min={leaseData.lease_start_date}
                                                            className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white ${fieldErrors.end_date ? 'border-red-300' : 'border-gray-200'
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
                                                    <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center mr-3">
                                                        <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                        </svg>
                                                    </div>
                                                    <h3 className="text-base font-medium text-gray-900">Financial Terms</h3>
                                                </div>

                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                                            Monthly Rent (Optional)
                                                        </label>
                                                        <div className="relative">
                                                            <span className="absolute left-4 top-2.5 text-gray-500 font-medium">$</span>
                                                            <input
                                                                type="number"
                                                                name="monthly_rent"
                                                                value={leaseData.monthly_rent}
                                                                onChange={handleChange}
                                                                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                                                                placeholder="Use unit's default rent"
                                                                step="0.01"
                                                                min="0"
                                                            />
                                                        </div>
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
                                                                onChange={handleChange}
                                                                className={`w-full pl-10 pr-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none ${fieldErrors.security_deposit ? 'border-red-300' : 'border-gray-200'
                                                                    }`}
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
                                                                    onChange={handleChange}
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
                                                                    onChange={handleChange}
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
                                                    onChange={handleChange}
                                                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none bg-white"
                                                    placeholder="Enter any special conditions, pet policies, utilities arrangements, or other lease terms that will apply to all selected units..."
                                                />
                                            </div>
                                        </form>
                                    </div>
                                ) : (
                                    /* Results View */
                                    <div className="p-6">
                                        {/* Results Summary */}
                                        <div className="mb-6 grid grid-cols-3 gap-4">
                                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                                                <div className="text-2xl font-bold text-blue-600">{assignmentResults?.total_units || 0}</div>
                                                <div className="text-sm text-blue-700">Total Units</div>
                                            </div>
                                            <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                                                <div className="text-2xl font-bold text-green-600">{assignmentResults?.successful_assignments || 0}</div>
                                                <div className="text-sm text-green-700">Successful</div>
                                            </div>
                                            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                                                <div className="text-2xl font-bold text-red-600">{assignmentResults?.failed_assignments || 0}</div>
                                                <div className="text-sm text-red-700">Failed</div>
                                            </div>
                                        </div>

                                        {/* Error Details */}
                                        {assignmentResults?.errors?.length > 0 && (
                                            <div className="mb-6 bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                                                <h3 className="font-medium text-gray-900 mb-3 flex items-center">
                                                    <svg className="w-5 h-5 text-red-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                                    </svg>
                                                    Assignment Errors
                                                </h3>
                                                <div className="border border-gray-200 rounded-lg overflow-hidden">
                                                    <div className="max-h-64 overflow-auto">
                                                        <table className="min-w-full divide-y divide-gray-200">
                                                            <thead className="bg-gray-50">
                                                                <tr>
                                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Unit Number</th>
                                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Error</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody className="bg-white divide-y divide-gray-200">
                                                                {assignmentResults.errors.map((error, index) => (
                                                                    <tr key={index} className="hover:bg-gray-50">
                                                                        <td className="px-4 py-3 text-sm text-gray-900">{error.unit_number}</td>
                                                                        <td className="px-4 py-3 text-sm text-red-600">{error.error_message}</td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* Footer */}
                            <div className="px-6 py-5 bg-gray-50 border-t border-gray-200">
                                {!showResults ? (
                                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                                        <div className="text-sm text-gray-500 flex items-start flex-1 sm:max-w-md">
                                            <svg className="w-4 h-4 mr-2 text-gray-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                            </svg>
                                            <span>This will create customized leases for all selected units with the terms you've specified above. Additional lease details can be modified later on the Leases page.</span>
                                        </div>
                                        <div className="flex gap-3 flex-shrink-0 sm:items-center">
                                            <button
                                                type="button"
                                                onClick={handleClose}
                                                className="px-4 py-2.5 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all text-sm font-medium"
                                                disabled={loading}
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                onClick={handleSubmit}
                                                className="px-5 py-2.5 bg-gradient-to-br from-brand-green to-brand-teal text-white rounded-md hover:from-brand-green/90 hover:to-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-green focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium flex items-center gap-2 min-w-[180px] justify-center shadow-sm"
                                                disabled={loading || !selectedTenant}
                                            >
                                                {loading ? (
                                                    <>
                                                        <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                        </svg>
                                                        Processing...
                                                    </>
                                                ) : (
                                                    `Assign to ${selectedUnits.length} Units`
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex justify-between">
                                        <button
                                            onClick={handleBackToForm}
                                            className="px-4 py-2.5 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all text-sm font-medium"
                                        >
                                            Assign More Units
                                        </button>
                                        <button
                                            onClick={handleClose}
                                            className="px-5 py-2.5 bg-gradient-to-br from-brand-green to-brand-teal text-white rounded-md hover:from-brand-green/90 hover:to-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-green focus:ring-offset-2 transition-all text-sm font-medium shadow-sm"
                                        >
                                            Done
                                        </button>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Tenant Creation Modal */}
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

export default BulkAssignTenantModal; 