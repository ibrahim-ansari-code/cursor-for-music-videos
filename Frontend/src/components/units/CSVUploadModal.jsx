import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "react-toastify";
import {
    validateCSVFile,
    readFileAsText,
    parseCSV
} from "../../utils/csvParser";
import { bulkAssignFromCSV } from "../../utils/api/units";

const CSVUploadModal = ({ propertyId, isOpen, onClose, onSuccess }) => {
    const [selectedFile, setSelectedFile] = useState(null);
    const [csvData, setCsvData] = useState(null);
    const [parseErrors, setParseErrors] = useState([]);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadResults, setUploadResults] = useState(null);
    const [step, setStep] = useState(1); // 1: Select file, 2: Preview, 3: Results

    const handleFileSelect = (event) => {
        // Prevent any form submission
        event.preventDefault();
        event.stopPropagation();

        const file = event.target.files[0];
        if (!file) return;

        console.log("File selected:", file.name, file.size);

        // Validate file
        const validation = validateCSVFile(file);
        if (!validation.isValid) {
            toast.error(validation.errors.join(", "));
            return;
        }

        setSelectedFile(file);

        const processFile = async () => {
            try {
                // Read and parse file
                const csvText = await readFileAsText(file);
                const parsed = parseCSV(csvText);

                console.log("CSV parsed:", { rows: parsed.rows?.length, errors: parsed.errors?.length });

                setCsvData(parsed.rows);
                setParseErrors(parsed.errors);
                setStep(2);
            } catch (error) {
                console.error("CSV parsing failed:", error);
                toast.error(`Failed to parse CSV: ${error.message}`);
                // Reset all state on error to ensure clean state
                setSelectedFile(null);
                setCsvData(null);
                setParseErrors([]);
                setStep(1);
            }
        };

        processFile();
    };

    const handleUpload = async (event) => {
        // Prevent any form submission or default behavior
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        console.log("Starting upload process...", { csvData: csvData?.length, propertyId });

        if (!csvData || csvData.length === 0) {
            toast.error("No valid data to upload");
            return;
        }

        setIsUploading(true);

        try {
            // Format and normalize data for API
            const assignments = csvData.map(row => {
                // Normalize lease_start_date to ISO date format (YYYY-MM-DD)
                const normalizeDate = (dateStr) => {
                    if (!dateStr || dateStr.trim() === '') return dateStr;
                    
                    // Try to coerce to YYYY-MM-DD if common formats are used
                    const isoDate = (() => {
                        // Already ISO-like
                        if (/^\d{4}-\d{1,2}-\d{1,2}$/.test(dateStr.trim())) {
                            return new Date(`${dateStr.trim()}T00:00:00.000Z`);
                        }
                        // Only support MM/DD/YYYY format to avoid ambiguity
                        const mdyMatch = dateStr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
                        if (mdyMatch) {
                            const [, m, d, y] = mdyMatch;
                            return new Date(`${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}T00:00:00.000Z`);
                        }
                        // fallback
                        return new Date(dateStr);
                    })();
                    
                    // Format as YYYY-MM-DD (date only, no time component)
                    if (!isNaN(isoDate.getTime())) {
                        const year = isoDate.getUTCFullYear();
                        const month = String(isoDate.getUTCMonth() + 1).padStart(2, "0");
                        const day = String(isoDate.getUTCDate()).padStart(2, "0");
                        return `${year}-${month}-${day}`;
                    }
                    
                    return dateStr; // fallback
                };
                // Strip currency symbols and commas
                const cleanRent = String(row.monthly_rent || "")
                    .replace(/[$,]/g, "")
                    .trim();

                return {
                    unit_number: row.unit_number,
                    tenant_email: (row.tenant_email || "").toLowerCase().trim(),
                    lease_start_date: normalizeDate(row.lease_start_date),
                    monthly_rent: cleanRent
                };
            });

            console.log("Sending assignments to API...", assignments);

            const response = await bulkAssignFromCSV(propertyId, { assignments });

            console.log("Upload response received:", response);

            setUploadResults(response);
            setStep(3);

            if (response.successful_assignments > 0) {
                toast.success(`Successfully assigned ${response.successful_assignments} units`);
            }

            if (response.failed_assignments > 0) {
                toast.warning(`${response.failed_assignments} assignments failed. Check results for details.`);
            }
        } catch (error) {
            console.error("Upload failed:", error);
            toast.error(`Upload failed: ${error.message || 'Unknown error occurred'}`);
        } finally {
            setIsUploading(false);
        }
    };

    const handleClose = () => {
        if (step === 3 && uploadResults?.successful_assignments > 0) {
            // Show confirmation if there were successful assignments
            const shouldClose = window.confirm(
                "Are you sure you want to close? Your assignments have been completed successfully."
            );
            if (!shouldClose) return;

            // Call onSuccess callback when user confirms closing after successful upload
            if (onSuccess) {
                onSuccess(uploadResults);
            }
        }

        setSelectedFile(null);
        setCsvData(null);
        setParseErrors([]);
        setUploadResults(null);
        setStep(1);
        onClose();
    };

    const handleStartOver = () => {
        setSelectedFile(null);
        setCsvData(null);
        setParseErrors([]);
        setUploadResults(null);
        setStep(1);
    };

    const downloadResults = () => {
        if (!uploadResults) return;

        const csvContent = [
            "Row,Unit Number,Status,Error Message",
            ...csvData.map((row, index) => {
                const rowNumber = row.rowNumber || index + 2; // Fallback to index + 2 (accounting for header)
                const error = uploadResults.errors?.find(e => e.row_number === rowNumber);
                const status = error ? "FAILED" : "SUCCESS";
                const errorMsg = error?.error_message || "";
                return `${rowNumber},"${row.unit_number}",${status},"${errorMsg}"`;
            })
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `bulk_assignment_results_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    };

    if (!isOpen) return null;

    const stepTitles = {
        1: "Upload CSV File",
        2: "Preview & Validate",
        3: "Assignment Results"
    };

    return (
        <AnimatePresence>
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
                    className="relative w-full max-w-4xl bg-white rounded-xl shadow-xl max-h-[85vh] overflow-hidden flex flex-col z-[10000]"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header */}
                    <div className="relative px-6 py-4 bg-gradient-to-br from-brand-green to-brand-teal text-white">
                        <div className="flex justify-between items-center">
                            <div>
                                <h2 className="text-xl font-semibold text-white">
                                    CSV Bulk Assignment
                                </h2>
                                <p className="text-white/80 mt-0.5 text-sm">
                                    {stepTitles[step]} - Import tenant assignments from spreadsheet
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

                    {/* Progress Steps */}
                    <div className="px-6 py-4 bg-white border-b border-gray-200">
                        <div className="flex items-center space-x-4">
                            {[1, 2, 3].map((stepNumber) => (
                                <div key={stepNumber} className="flex items-center">
                                    <div
                                        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${step >= stepNumber
                                            ? "bg-brand-green text-white shadow-sm"
                                            : "bg-gray-300 text-gray-600"
                                            }`}
                                    >
                                        {step > stepNumber ? (
                                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                            </svg>
                                        ) : (
                                            stepNumber
                                        )}
                                    </div>
                                    <span className={`ml-2 text-sm transition-colors ${step >= stepNumber ? "text-brand-green font-medium" : "text-gray-500"
                                        }`}>
                                        {stepNumber === 1 && "Select File"}
                                        {stepNumber === 2 && "Preview Data"}
                                        {stepNumber === 3 && "Results"}
                                    </span>
                                    {stepNumber < 3 && (
                                        <div className={`w-12 h-0.5 ml-4 transition-colors ${step > stepNumber ? "bg-brand-green" : "bg-gray-300"
                                            }`} />
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto bg-gray-50">
                        <div className="p-6 space-y-4">
                            {step === 1 && (
                                <>
                                    {/* Primary Upload Area - Now at the very top */}
                                    <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
                                        {/* Upload Header */}
                                        <div className="bg-gradient-to-r from-purple-50 to-indigo-50 px-6 py-4 border-b border-purple-100">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h3 className="text-lg font-semibold text-gray-900">Upload Your CSV File</h3>
                                                    <p className="text-sm text-gray-600 mt-1">Required: unit_number, tenant_email, lease_start_date, monthly_rent</p>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Upload Area */}
                                        <div className="p-6">
                                            <div className="border-2 border-dashed border-purple-300 rounded-lg p-8 text-center hover:border-purple-400 hover:bg-purple-50/30 transition-all">
                                                <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-xl flex items-center justify-center">
                                                    <svg className="w-8 h-8 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                                    </svg>
                                                </div>

                                                <input
                                                    type="file"
                                                    accept=".csv"
                                                    onChange={handleFileSelect}
                                                    className="hidden"
                                                    id="csv-upload"
                                                />
                                                <label
                                                    htmlFor="csv-upload"
                                                    className="cursor-pointer inline-flex items-center px-8 py-4 border border-transparent text-base font-medium rounded-lg text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
                                                >
                                                    <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                                    </svg>
                                                    Choose Your CSV File
                                                </label>

                                                <p className="mt-4 text-sm text-gray-600">
                                                    Or drag and drop your file here
                                                </p>
                                                <p className="text-xs text-gray-500 mt-2">
                                                    Supports .csv files up to 5MB
                                                </p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Enhanced Detailed Help Section */}
                                    <details className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
                                        <summary className="p-5 cursor-pointer hover:bg-gradient-to-r hover:from-gray-50 hover:to-blue-50 select-none transition-all list-none [&::-webkit-details-marker]:hidden">
                                            <div className="flex items-center">
                                                <div className="w-10 h-10 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-xl flex items-center justify-center mr-4">
                                                    <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                                    </svg>
                                                </div>
                                                <div className="flex-1">
                                                    <h3 className="text-lg font-semibold text-gray-900 mb-1">📋 Complete CSV Formatting Guide</h3>
                                                    <p className="text-sm text-gray-600">Everything you need to know about formatting your bulk assignment file</p>
                                                </div>
                                                <div className="flex items-center text-blue-600">
                                                    <span className="text-sm font-medium mr-2">View Guide</span>
                                                    <svg className="w-5 h-5 details-chevron transition-transform duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                                    </svg>
                                                </div>
                                            </div>
                                        </summary>

                                        <div className="border-t border-gray-100">
                                            <div className="p-6 space-y-6">
                                                {/* Required Columns Section */}
                                                <div>
                                                    <div className="flex items-center mb-4">
                                                        <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center mr-3">
                                                            <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                            </svg>
                                                        </div>
                                                        <h4 className="text-base font-semibold text-gray-900">Required Columns</h4>
                                                    </div>

                                                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                                        <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200">
                                                            <div className="flex items-start">
                                                                <div className="w-8 h-8 bg-blue-600 text-white rounded-lg flex items-center justify-center mr-3 flex-shrink-0 text-sm font-bold">1</div>
                                                                <div className="flex-1">
                                                                    <h5 className="font-semibold text-blue-900 mb-1">unit_number</h5>
                                                                    <p className="text-sm text-blue-800 mb-2">Must match exactly as shown in your property units</p>
                                                                    <div className="bg-white bg-opacity-60 rounded p-2 text-xs">
                                                                        <span className="text-green-700 font-medium">✓ Good:</span> "Unit 101", "Penthouse A", "Studio 5B"<br />
                                                                        <span className="text-red-700 font-medium">✗ Bad:</span> "unit 101", "101", "apt 101"
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg border border-purple-200">
                                                            <div className="flex items-start">
                                                                <div className="w-8 h-8 bg-purple-600 text-white rounded-lg flex items-center justify-center mr-3 flex-shrink-0 text-sm font-bold">2</div>
                                                                <div className="flex-1">
                                                                    <h5 className="font-semibold text-purple-900 mb-1">tenant_email</h5>
                                                                    <p className="text-sm text-purple-800 mb-2">Email of existing tenant in your system</p>
                                                                    <div className="bg-white bg-opacity-60 rounded p-2 text-xs">
                                                                        <span className="text-green-700 font-medium">✓ Good:</span> "john.doe@email.com"<br />
                                                                        <span className="text-red-700 font-medium">✗ Bad:</span> "John Doe", "john", invalid emails
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-lg border border-orange-200">
                                                            <div className="flex items-start">
                                                                <div className="w-8 h-8 bg-orange-600 text-white rounded-lg flex items-center justify-center mr-3 flex-shrink-0 text-sm font-bold">3</div>
                                                                <div className="flex-1">
                                                                    <h5 className="font-semibold text-orange-900 mb-1">lease_start_date</h5>
                                                                    <p className="text-sm text-orange-800 mb-2">Future date in accepted formats</p>
                                                                    <div className="bg-white bg-opacity-60 rounded p-2 text-xs">
                                                                        <span className="text-green-700 font-medium">✓ Good:</span> "01/15/2024", "2024-01-15"<br />
                                                                        <span className="text-red-700 font-medium">✗ Bad:</span> "Jan 15", past dates, "15/01/24"
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border border-green-200">
                                                            <div className="flex items-start">
                                                                <div className="w-8 h-8 bg-green-600 text-white rounded-lg flex items-center justify-center mr-3 flex-shrink-0 text-sm font-bold">4</div>
                                                                <div className="flex-1">
                                                                    <h5 className="font-semibold text-green-900 mb-1">monthly_rent</h5>
                                                                    <p className="text-sm text-green-800 mb-2">Numeric value only, no currency symbols</p>
                                                                    <div className="bg-white bg-opacity-60 rounded p-2 text-xs">
                                                                        <span className="text-green-700 font-medium">✓ Good:</span> "1200", "1200.00", "2500"<br />
                                                                        <span className="text-red-700 font-medium">✗ Bad:</span> "$1,200", "1200 USD", "twelve hundred"
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Sample CSV Data */}
                                                <div>
                                                    <div className="flex items-center mb-4">
                                                        <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center mr-3">
                                                            <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                                <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                                                            </svg>
                                                        </div>
                                                        <h4 className="text-base font-semibold text-gray-900">Sample CSV Data</h4>
                                                    </div>

                                                    <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
                                                        <div className="text-green-400 text-xs font-mono mb-2"># Example CSV file content:</div>
                                                        <div className="text-gray-300 font-mono text-sm space-y-1">
                                                            <div className="text-yellow-400">unit_number,tenant_email,lease_start_date,monthly_rent</div>
                                                            <div>Unit 101,john.doe@email.com,01/15/2024,1200</div>
                                                            <div>Penthouse A,sarah.smith@email.com,02/01/2024,2500</div>
                                                            <div>Studio 3B,mike.jones@email.com,01/20/2024,950</div>
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Common Issues & Solutions */}
                                                <div>
                                                    <div className="flex items-center mb-4">
                                                        <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center mr-3">
                                                            <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                                            </svg>
                                                        </div>
                                                        <h4 className="text-base font-semibold text-gray-900">Common Issues & Quick Fixes</h4>
                                                    </div>

                                                    <div className="space-y-3">
                                                        <div className="border border-red-200 bg-red-50 rounded-lg p-4">
                                                            <div className="flex items-start">
                                                                <div className="w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center mr-3 flex-shrink-0 text-xs font-bold">!</div>
                                                                <div>
                                                                    <h5 className="font-medium text-red-900 mb-1">"Unit not found" errors</h5>
                                                                    <p className="text-sm text-red-800 mb-2">Unit names don't match exactly</p>
                                                                    <p className="text-xs text-red-700">💡 <strong>Fix:</strong> Copy unit names directly from your property's unit list - check for extra spaces, capitalization, and special characters</p>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-4">
                                                            <div className="flex items-start">
                                                                <div className="w-6 h-6 bg-yellow-500 text-white rounded-full flex items-center justify-center mr-3 flex-shrink-0 text-xs font-bold">!</div>
                                                                <div>
                                                                    <h5 className="font-medium text-yellow-900 mb-1">"Tenant not found" errors</h5>
                                                                    <p className="text-sm text-yellow-800 mb-2">Email doesn't belong to existing tenant</p>
                                                                    <p className="text-xs text-yellow-700">💡 <strong>Fix:</strong> Create tenants first in your tenant management section, then use their exact email addresses</p>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <div className="border border-blue-200 bg-blue-50 rounded-lg p-4">
                                                            <div className="flex items-start">
                                                                <div className="w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center mr-3 flex-shrink-0 text-xs font-bold">!</div>
                                                                <div>
                                                                    <h5 className="font-medium text-blue-900 mb-1">"Unit already occupied" errors</h5>
                                                                    <p className="text-sm text-blue-800 mb-2">Unit has an active lease</p>
                                                                    <p className="text-xs text-blue-700">💡 <strong>Fix:</strong> Check unit status in property management - end existing leases first or use different units</p>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Pro Tips */}
                                                <div className="bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-5">
                                                    <div className="flex items-center mb-4">
                                                        <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center mr-3">
                                                            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                                <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                                            </svg>
                                                        </div>
                                                        <h4 className="text-base font-semibold text-emerald-900">💡 Pro Tips for Success</h4>
                                                    </div>

                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                        <div className="space-y-2">
                                                            <div className="flex items-start text-sm">
                                                                <span className="text-emerald-600 mr-2">•</span>
                                                                <span className="text-emerald-800">Export your current unit list to get exact unit names</span>
                                                            </div>
                                                            <div className="flex items-start text-sm">
                                                                <span className="text-emerald-600 mr-2">•</span>
                                                                <span className="text-emerald-800">Test with 2-3 rows first before uploading large files</span>
                                                            </div>
                                                            <div className="flex items-start text-sm">
                                                                <span className="text-emerald-600 mr-2">•</span>
                                                                <span className="text-emerald-800">Keep a backup copy of your CSV file</span>
                                                            </div>
                                                        </div>
                                                        <div className="space-y-2">
                                                            <div className="flex items-start text-sm">
                                                                <span className="text-emerald-600 mr-2">•</span>
                                                                <span className="text-emerald-800">Use future lease start dates (at least tomorrow)</span>
                                                            </div>
                                                            <div className="flex items-start text-sm">
                                                                <span className="text-emerald-600 mr-2">•</span>
                                                                <span className="text-emerald-800">Check tenant emails are spelled correctly</span>
                                                            </div>
                                                            <div className="flex items-start text-sm">
                                                                <span className="text-emerald-600 mr-2">•</span>
                                                                <span className="text-emerald-800">Save as .csv format, not .xlsx or .xls</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </details>
                                </>
                            )}

                            {step === 2 && (
                                <>
                                    {/* Parse Errors */}
                                    {parseErrors.length > 0 && (
                                        <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                                            <div className="flex items-center mb-3">
                                                <div className="w-9 h-9 bg-red-50 rounded-lg flex items-center justify-center mr-3">
                                                    <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                                    </svg>
                                                </div>
                                                <h3 className="text-base font-medium text-gray-900">
                                                    Validation Errors ({parseErrors.length})
                                                </h3>
                                            </div>
                                            <div className="bg-red-50 rounded-lg p-4 max-h-32 overflow-y-auto">
                                                {parseErrors.map((error, index) => (
                                                    <div key={index} className="text-sm text-red-700 py-1">
                                                        {error}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Data Preview */}
                                    <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                                        <div className="flex items-center mb-3">
                                            <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center mr-3">
                                                <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                                </svg>
                                            </div>
                                            <h3 className="text-base font-medium text-gray-900">
                                                Data Preview ({csvData?.length || 0} valid rows)
                                            </h3>
                                        </div>

                                        <div className="border border-gray-200 rounded-lg overflow-hidden">
                                            <div className="max-h-64 overflow-auto">
                                                <table className="min-w-full divide-y divide-gray-200">
                                                    <thead className="bg-gray-50">
                                                        <tr>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Unit Number</th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tenant Email</th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Start Date</th>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Monthly Rent</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="bg-white divide-y divide-gray-200">
                                                        {csvData?.map((row, index) => (
                                                            <tr key={index} className="hover:bg-gray-50">
                                                                <td className="px-4 py-3 text-sm text-gray-900">{row.unit_number}</td>
                                                                <td className="px-4 py-3 text-sm text-gray-900">{row.tenant_email}</td>
                                                                <td className="px-4 py-3 text-sm text-gray-900">{row.lease_start_date}</td>
                                                                <td className="px-4 py-3 text-sm text-gray-900">${row.monthly_rent}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </div>
                                </>
                            )}

                            {step === 3 && uploadResults && (
                                <>
                                    {/* Overall Success/Failure Banner */}
                                    <div className={`rounded-lg p-6 border-2 ${uploadResults.successful_assignments > 0 && uploadResults.failed_assignments === 0
                                        ? "bg-green-50 border-green-200"
                                        : uploadResults.successful_assignments > 0 && uploadResults.failed_assignments > 0
                                            ? "bg-yellow-50 border-yellow-200"
                                            : "bg-red-50 border-red-200"
                                        }`}>
                                        <div className="flex items-start">
                                            <div className={`w-12 h-12 rounded-full flex items-center justify-center mr-4 ${uploadResults.successful_assignments > 0 && uploadResults.failed_assignments === 0
                                                ? "bg-green-100"
                                                : uploadResults.successful_assignments > 0 && uploadResults.failed_assignments > 0
                                                    ? "bg-yellow-100"
                                                    : "bg-red-100"
                                                }`}>
                                                {uploadResults.successful_assignments > 0 && uploadResults.failed_assignments === 0 ? (
                                                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                    </svg>
                                                ) : uploadResults.successful_assignments > 0 && uploadResults.failed_assignments > 0 ? (
                                                    <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                                    </svg>
                                                ) : (
                                                    <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                    </svg>
                                                )}
                                            </div>
                                            <div className="flex-1">
                                                <h3 className={`text-lg font-semibold mb-2 ${uploadResults.successful_assignments > 0 && uploadResults.failed_assignments === 0
                                                    ? "text-green-800"
                                                    : uploadResults.successful_assignments > 0 && uploadResults.failed_assignments > 0
                                                        ? "text-yellow-800"
                                                        : "text-red-800"
                                                    }`}>
                                                    {uploadResults.successful_assignments > 0 && uploadResults.failed_assignments === 0
                                                        ? "🎉 All Assignments Completed Successfully!"
                                                        : uploadResults.successful_assignments > 0 && uploadResults.failed_assignments > 0
                                                            ? "⚠️ Bulk Assignment Partially Completed"
                                                            : "❌ Bulk Assignment Failed"}
                                                </h3>
                                                <p className={`text-sm ${uploadResults.successful_assignments > 0 && uploadResults.failed_assignments === 0
                                                    ? "text-green-700"
                                                    : uploadResults.successful_assignments > 0 && uploadResults.failed_assignments > 0
                                                        ? "text-yellow-700"
                                                        : "text-red-700"
                                                    }`}>
                                                    {uploadResults.successful_assignments > 0 && uploadResults.failed_assignments === 0
                                                        ? `Perfect! All ${uploadResults.total_rows} tenant assignments have been created successfully. Your units are now leased and ready to generate income.`
                                                        : uploadResults.successful_assignments > 0 && uploadResults.failed_assignments > 0
                                                            ? `${uploadResults.successful_assignments} assignments completed successfully, but ${uploadResults.failed_assignments} failed. Review the errors below and consider fixing the failed assignments.`
                                                            : `None of the ${uploadResults.total_rows} assignments could be completed. Please review the errors below and fix your CSV file.`}
                                                </p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Detailed Results Summary */}
                                    <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="flex items-center">
                                                <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center mr-3">
                                                    <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                                    </svg>
                                                </div>
                                                <h3 className="text-base font-medium text-gray-900">Assignment Summary</h3>
                                            </div>
                                            {(uploadResults.successful_assignments > 0 || uploadResults.failed_assignments > 0) && (
                                                <button
                                                    onClick={downloadResults}
                                                    className="text-sm text-blue-600 hover:text-blue-800 underline flex items-center gap-1"
                                                >
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                    </svg>
                                                    Download Results
                                                </button>
                                            )}
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                                                <div className="text-3xl font-bold text-blue-600 mb-1">{uploadResults.total_rows}</div>
                                                <div className="text-sm text-blue-700 font-medium">Total Rows Processed</div>
                                                <div className="text-xs text-blue-600 mt-1">from your CSV file</div>
                                            </div>
                                            <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                                                <div className="text-3xl font-bold text-green-600 mb-1">{uploadResults.successful_assignments}</div>
                                                <div className="text-sm text-green-700 font-medium">Successfully Assigned</div>
                                                <div className="text-xs text-green-600 mt-1">
                                                    {uploadResults.created_leases?.length > 0 ? `${uploadResults.created_leases.length} new leases created` : "leases created"}
                                                </div>
                                            </div>
                                            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                                                <div className="text-3xl font-bold text-red-600 mb-1">{uploadResults.failed_assignments}</div>
                                                <div className="text-sm text-red-700 font-medium">Failed Assignments</div>
                                                <div className="text-xs text-red-600 mt-1">
                                                    {uploadResults.failed_assignments > 0 ? "see details below" : "no errors"}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Success Rate Progress Bar */}
                                        {uploadResults.total_rows > 0 && (
                                            <div className="mt-4">
                                                <div className="flex justify-between items-center mb-2">
                                                    <span className="text-sm font-medium text-gray-700">Success Rate</span>
                                                    <span className="text-sm text-gray-600">
                                                        {Math.round((uploadResults.successful_assignments / uploadResults.total_rows) * 100)}%
                                                    </span>
                                                </div>
                                                <div className="w-full bg-gray-200 rounded-full h-2">
                                                    <div
                                                        className="bg-green-500 h-2 rounded-full transition-all duration-300"
                                                        style={{ width: `${(uploadResults.successful_assignments / uploadResults.total_rows) * 100}%` }}
                                                    ></div>
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Success Details */}
                                    {uploadResults.successful_assignments > 0 && uploadResults.created_leases?.length > 0 && (
                                        <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                                            <div className="flex items-center justify-between mb-4">
                                                <div className="flex items-center">
                                                    <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center mr-3">
                                                        <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                                        </svg>
                                                    </div>
                                                    <h3 className="text-base font-medium text-gray-900">Successfully Created Leases</h3>
                                                </div>
                                                <span className="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-1 rounded-full">
                                                    {uploadResults.created_leases.length} lease{uploadResults.created_leases.length !== 1 ? 's' : ''}
                                                </span>
                                            </div>

                                            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                                    {uploadResults.created_leases.slice(0, 6).map((leaseId, index) => (
                                                        <div key={index} className="bg-white rounded-lg p-3 border border-green-200">
                                                            <div className="flex items-center">
                                                                <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3">
                                                                    <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                                    </svg>
                                                                </div>
                                                                <div>
                                                                    <div className="text-sm font-medium text-gray-900">Lease #{leaseId}</div>
                                                                    <div className="text-xs text-green-600">Active lease created</div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                                {uploadResults.created_leases.length > 6 && (
                                                    <div className="mt-3 text-center">
                                                        <span className="text-sm text-green-700">
                                                            And {uploadResults.created_leases.length - 6} more leases...
                                                        </span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}

                                    {/* Error Details */}
                                    {uploadResults.errors?.length > 0 && (
                                        <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                                            <div className="flex items-center justify-between mb-4">
                                                <div className="flex items-center">
                                                    <div className="w-9 h-9 bg-red-50 rounded-lg flex items-center justify-center mr-3">
                                                        <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                                        </svg>
                                                    </div>
                                                    <h3 className="text-base font-medium text-gray-900">Assignment Errors</h3>
                                                </div>
                                                <span className="bg-red-100 text-red-800 text-xs font-medium px-2.5 py-1 rounded-full">
                                                    {uploadResults.errors.length} error{uploadResults.errors.length !== 1 ? 's' : ''}
                                                </span>
                                            </div>

                                            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                                <div className="space-y-3">
                                                    {uploadResults.errors.map((error, index) => (
                                                        <div key={index} className="bg-white rounded-lg p-4 border border-red-200">
                                                            <div className="flex items-start">
                                                                <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
                                                                    <span className="text-red-600 text-sm font-medium">{error.row_number || index + 1}</span>
                                                                </div>
                                                                <div className="flex-1 min-w-0">
                                                                    <div className="flex items-center gap-3 mb-2">
                                                                        <span className="text-sm font-medium text-gray-900">Row {error.row_number || index + 1}</span>
                                                                        {error.unit_number && (
                                                                            <span className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded">
                                                                                {error.unit_number}
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                    <p className="text-sm text-red-700">
                                                                        <span className="font-medium">Error:</span> {error.error_message || error.message}
                                                                    </p>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>

                                                <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                                                    <div className="flex items-start">
                                                        <svg className="w-5 h-5 text-blue-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                        </svg>
                                                        <div>
                                                            <p className="text-sm text-blue-800 font-medium">💡 Quick Fixes:</p>
                                                            <ul className="text-sm text-blue-700 mt-1 space-y-1">
                                                                <li>• Double-check unit names match exactly as they appear in your property</li>
                                                                <li>• Ensure tenant emails belong to existing tenants in your system</li>
                                                                <li>• Verify units are not already occupied by other tenants</li>
                                                                <li>• Check that dates are in the future and properly formatted</li>
                                                            </ul>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="px-6 py-5 bg-gray-50 border-t border-gray-200">
                        {step === 1 && (
                            <div className="flex justify-end">
                                <button
                                    type="button"
                                    onClick={handleClose}
                                    className="px-4 py-2.5 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all text-sm font-medium"
                                >
                                    Cancel
                                </button>
                            </div>
                        )}

                        {step === 2 && (
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                                <div className="text-sm text-gray-500 flex items-start flex-1 sm:max-w-md">
                                    <svg className="w-4 h-4 mr-2 text-gray-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <span>Review the data above before uploading. Fix any validation errors first.</span>
                                </div>
                                <div className="flex gap-3 flex-shrink-0 sm:items-center">
                                    <button
                                        onClick={handleStartOver}
                                        className="px-4 py-2.5 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all text-sm font-medium"
                                    >
                                        Select Different File
                                    </button>
                                    <button
                                        type="button"
                                        onClick={handleUpload}
                                        disabled={!csvData || csvData.length === 0 || isUploading || parseErrors.length > 0}
                                        className="px-5 py-2.5 bg-gradient-to-br from-brand-green to-brand-teal text-white rounded-md hover:from-brand-green/90 hover:to-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-green focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium flex items-center gap-2 min-w-[180px] justify-center shadow-sm"
                                    >
                                        {isUploading ? (
                                            <>
                                                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                </svg>
                                                Processing...
                                            </>
                                        ) : (
                                            `Upload ${csvData?.length || 0} Assignments`
                                        )}
                                    </button>
                                </div>
                            </div>
                        )}

                        {step === 3 && (
                            <div className="flex flex-col sm:flex-row sm:justify-between gap-3">
                                <div className="flex gap-3">
                                    <button
                                        onClick={handleStartOver}
                                        className="px-4 py-2.5 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all text-sm font-medium"
                                    >
                                        Upload Another File
                                    </button>
                                </div>
                                <button
                                    onClick={() => {
                                        // Call onSuccess for successful uploads before closing
                                        if (uploadResults?.successful_assignments > 0 && onSuccess) {
                                            onSuccess(uploadResults);
                                        }
                                        handleClose();
                                    }}
                                    className={`px-5 py-2.5 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all text-sm font-medium shadow-sm ${uploadResults.successful_assignments > 0
                                        ? "bg-gradient-to-br from-brand-green to-brand-teal text-white hover:from-brand-green/90 hover:to-brand-teal/90 focus:ring-brand-green"
                                        : "bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500"
                                        }`}
                                >
                                    {uploadResults.successful_assignments > 0 ? "🎉 All Done!" : "Close"}
                                </button>
                            </div>
                        )}
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
};

export default CSVUploadModal;