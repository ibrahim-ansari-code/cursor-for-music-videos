import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "react-toastify";
import {
    validateCSVFile,
    readFileAsText,
    parseCSV as parseCSVGeneric
} from "../../../utils/csvParser";

const CSVImportModal = ({ isOpen, onClose, onSuccess, config }) => {
    const [selectedFile, setSelectedFile] = useState(null);
    const [csvData, setCsvData] = useState(null);
    const [parseErrors, setParseErrors] = useState([]);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadResults, setUploadResults] = useState(null);
    const [step, setStep] = useState(1); // 1: Select file, 2: Preview, 3: Results

    const { 
        title = "CSV Import",
        description = "Import data from CSV file",
        expectedHeaders,
        apiFunction,
        sampleData = [],
        validationTips = []
    } = config;

    // Helper function for robust CSV line parsing that handles quoted fields
    const parseCSVLine = (line) => {
        const result = [];
        let current = '';
        let inQuotes = false;
        
        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            const nextChar = line[i + 1];
            
            if (char === '"' && inQuotes && nextChar === '"') {
                // Escaped quote
                current += '"';
                i++; // Skip next quote
            } else if (char === '"') {
                // Toggle quote mode
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                // End of field
                result.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        
        // Don't forget the last field
        result.push(current.trim());
        return result;
    };
    
    // Custom CSV parser for accounting data
    const parseCSV = (csvText) => {
        const lines = csvText.trim().split('\n');
        if (lines.length < 2) {
            throw new Error('CSV must contain at least a header row and one data row');
        }

        // Find the actual header row (skip metadata rows from exports)
        let headerRowIndex = 0;
        let headers = [];
        
        for (let i = 0; i < lines.length; i++) {
            const parsedLine = parseCSVLine(lines[i]);
            
            // Check if this looks like a header row by matching expected columns
            const matchesExpectedHeaders = expectedHeaders.some(({ key, aliases = [] }) => {
                const allPossibleNames = [key, ...aliases];
                return parsedLine.some(header =>
                    allPossibleNames.some(name => 
                        header.toLowerCase().replace(/[^a-z]/g, '') === name.toLowerCase().replace(/[^a-z]/g, '')
                    )
                );
            });
            
            if (matchesExpectedHeaders) {
                headerRowIndex = i;
                headers = parsedLine;
                break;
            }
        }

        if (headers.length === 0) {
            throw new Error('Could not find valid header row in CSV');
        }
        
        // Create header mapping
        const headerMap = {};
        expectedHeaders.forEach(({ key, aliases = [] }) => {
            const allPossibleNames = [key, ...aliases];
            const foundIndex = headers.findIndex(header =>
                allPossibleNames.some(name => 
                    header.toLowerCase().replace(/[^a-z]/g, '') === name.toLowerCase().replace(/[^a-z]/g, '')
                )
            );
            if (foundIndex !== -1) {
                headerMap[key] = foundIndex;
            }
        });

        // Validate required headers
        const missingHeaders = expectedHeaders.filter(({ key, required }) =>
            required && !(key in headerMap)
        );

        if (missingHeaders.length > 0) {
            const missingNames = missingHeaders.map(({ label }) => label);
            throw new Error(`Missing required columns: ${missingNames.join(', ')}`);
        }

        // Parse data rows (start after header row)
        const rows = [];
        const errors = [];

        for (let i = headerRowIndex + 1; i < lines.length; i++) {
            const values = parseCSVLine(lines[i]);
            
            // Skip empty lines and metadata rows (including marked metadata rows)
            if (!values || values.every(val => !val || !val.trim()) || 
                values[0].includes('Brikli') || values[0].includes('Exported:') ||
                values[0].includes('__METADATA__') || values[0].includes('__SEPARATOR__')) {
                continue;
            }

            try {
                const row = { rowNumber: i + 1 };
                
                expectedHeaders.forEach(({ key, type = 'string', validator }) => {
                    const value = headerMap[key] !== undefined ? values[headerMap[key]] : '';
                    
                    if (type === 'number') {
                        const numValue = parseFloat(value.replace(/[$,]/g, ''));
                        row[key] = isNaN(numValue) ? null : numValue;
                    } else if (type === 'date') {
                        if (value && value !== 'N/A') {
                            // Handle multiple date formats more robustly
                            let date = null;
                            const dateStr = value.trim();
                            
                            // Try different date formats
                            if (dateStr.includes('/')) {
                                const parts = dateStr.split('/');
                                if (parts.length === 3) {
                                    const [part1, part2, part3] = parts.map(p => parseInt(p, 10));
                                    
                                    // Determine if MM/DD/YYYY or DD/MM/YYYY based on values
                                    if (part1 > 12 && part2 <= 12) {
                                        // Likely DD/MM/YYYY
                                        date = new Date(part3, part2 - 1, part1);
                                    } else if (part2 > 12 && part1 <= 12) {
                                        // Likely MM/DD/YYYY
                                        date = new Date(part3, part1 - 1, part2);
                                    } else if (part3 > 31) {
                                        // Year is last, assume MM/DD/YYYY (US format as default)
                                        date = new Date(part3, part1 - 1, part2);
                                    } else {
                                        // Ambiguous, default to MM/DD/YYYY
                                        date = new Date(part3, part1 - 1, part2);
                                    }
                                }
                            } else if (dateStr.includes('-')) {
                                // Try ISO format (YYYY-MM-DD) or other dash-separated formats
                                const parts = dateStr.split('-');
                                if (parts.length === 3 && parts[0].length === 4) {
                                    // YYYY-MM-DD format
                                    date = new Date(dateStr + 'T00:00:00');
                                } else if (parts.length === 3) {
                                    // DD-MM-YYYY or MM-DD-YYYY
                                    const [part1, part2, part3] = parts.map(p => parseInt(p, 10));
                                    if (part1 > 12 && part2 <= 12) {
                                        // DD-MM-YYYY
                                        date = new Date(part3, part2 - 1, part1);
                                    } else {
                                        // MM-DD-YYYY
                                        date = new Date(part3, part1 - 1, part2);
                                    }
                                }
                            } else {
                                // Try native parsing as fallback
                                date = new Date(dateStr);
                            }
                            
                            row[key] = (date && !isNaN(date.getTime())) ? date.toISOString().split('T')[0] : null;
                        } else {
                            row[key] = null;
                        }
                    } else if (key === 'status') {
                        // Normalize status to correct case for backend enum
                        const statusMapping = {
                            'pending': 'Pending',
                            'paid': 'Paid', 
                            'partial': 'Partial',
                            'overdue': 'Overdue',
                            'cancelled': 'Cancelled',
                            'canceled': 'Cancelled',
                            'refunded': 'Refunded',
                            'draft': 'Draft',
                            'void': 'Void',
                            'uncollectible': 'Uncollectible'
                        };
                        const normalizedValue = value === 'N/A' ? '' : (value || '');
                        row[key] = statusMapping[normalizedValue.toLowerCase()] || normalizedValue;
                    } else {
                        row[key] = value === 'N/A' ? '' : (value || '');
                    }

                    // Run custom validator if provided
                    if (validator) {
                        validator(row[key], row, i + 1);
                    }
                });

                // Only add rows that have at least some data
                if (Object.values(row).some(val => val && val !== '')) {
                    rows.push(row);
                }
            } catch (error) {
                errors.push(`Row ${i + 1}: ${error.message}`);
            }
        }

        if (rows.length === 0) {
            throw new Error('No valid data rows found in CSV');
        }

        if (errors.length > 0) {
            throw new Error(`CSV validation errors:\n${errors.join('\n')}`);
        }

        return rows;
    };

    const handleFileSelect = async (event) => {
        event.preventDefault();
        event.stopPropagation();

        const files = event.target?.files;
        const file = files && files.length > 0 ? files[0] : null;
        if (!file) return;

        // Validate file
        const validation = validateCSVFile(file);
        if (!validation.isValid) {
            toast.error(validation.errors.join(", "));
            return;
        }

        setSelectedFile(file);

        try {
            // Read and parse file
            const csvText = await readFileAsText(file);
            const parsed = parseCSV(csvText);

            setCsvData(parsed);
            setParseErrors([]);
            setStep(2);
        } catch (error) {
            toast.error(`Failed to parse CSV: ${error.message}`);
            setSelectedFile(null);
            setCsvData(null);
            setParseErrors(error.message.split('\n').filter(msg => msg.trim()));
            setStep(1);
        }
    };

    const handleUpload = async (event) => {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        if (!csvData || csvData.length === 0) {
            toast.error("No valid data to upload");
            return;
        }

        setIsUploading(true);

        try {
            const response = await apiFunction(csvData);
            setUploadResults(response);
            setStep(3);

            if (response.successful_imports > 0) {
                toast.success(`Successfully imported ${response.successful_imports} records`);
            }

            if (response.failed_imports > 0) {
                toast.warning(`${response.failed_imports} imports failed. Check results for details.`);
            }
        } catch (error) {
            // Extract meaningful error message and preserve structured errors
            let errorMessage = 'Unknown error occurred';
            let structuredErrors = [];
            
            if (error.response) {
                // HTTP error response
                if (error.response.data?.errors && Array.isArray(error.response.data.errors)) {
                    // Backend returned structured per-row errors
                    structuredErrors = error.response.data.errors;
                    errorMessage = `Import failed with ${structuredErrors.length} errors`;
                } else if (error.response.data?.detail) {
                    errorMessage = error.response.data.detail;
                } else if (error.response.data?.message) {
                    errorMessage = error.response.data.message;
                } else {
                    errorMessage = `HTTP ${error.response.status}: ${error.response.statusText}`;
                }
            } else if (error.message) {
                errorMessage = error.message;
            }
            
            toast.error(`Upload failed: ${errorMessage}`);
            
            // Preserve structured errors if available, otherwise create generic error
            const errors = structuredErrors.length > 0 ? structuredErrors : [{
                row_number: 0,
                error_message: errorMessage
            }];
            
            // Show upload results with actual error details
            setUploadResults({
                total_rows: csvData.length,
                successful_imports: 0,
                failed_imports: csvData.length,
                errors: errors
            });
            setStep(3);
        } finally {
            setIsUploading(false);
        }
    };

    const handleClose = () => {
        if (step === 3 && uploadResults?.successful_imports > 0) {
            const shouldClose = window.confirm(
                "Are you sure you want to close? Your imports have been completed successfully."
            );
            if (!shouldClose) return;

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
            "Row,Status,Error Message",
            ...csvData.map((row, index) => {
                const rowNumber = row.rowNumber || index + 2;
                const error = uploadResults.errors?.find(e => e.row_number === rowNumber);
                const status = error ? "FAILED" : "SUCCESS";
                const errorMsg = error?.error_message || "";
                return `${rowNumber},${status},"${errorMsg}"`;
            })
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `import_results_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    };

    if (!isOpen) return null;

    const stepTitles = {
        1: "Upload CSV File",
        2: "Preview & Validate",
        3: "Import Results"
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
                                    {title}
                                </h2>
                                <p className="text-white/80 mt-0.5 text-sm">
                                    {stepTitles[step]} - {description}
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
                                    {/* Upload Area */}
                                    <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
                                        <div className="bg-gradient-to-r from-green-50 to-green-100 px-6 py-4 border-b border-green-100">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h3 className="text-lg font-semibold text-gray-900">Upload Your CSV File</h3>
                                                    <p className="text-sm text-gray-600 mt-1">
                                                        Required: {expectedHeaders.filter(h => h.required).map(h => h.label).join(', ')}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="p-6">
                                            <div className="border-2 border-dashed border-green-300 rounded-lg p-8 text-center hover:border-green-400 hover:bg-green-50/30 transition-all">
                                                <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-green-100 to-green-600 rounded-xl flex items-center justify-center">
                                                    <svg className="w-8 h-8 text-brand-green" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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
                                                    className="cursor-pointer inline-flex items-center px-8 py-4 border border-transparent text-base font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
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

                                    {/* Sample Data Section */}
                                    {sampleData.length > 0 && (
                                        <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
                                            <div className="px-6 py-4 border-b border-gray-200">
                                                <h3 className="text-lg font-semibold text-gray-900">Sample CSV Format</h3>
                                                <p className="text-sm text-gray-600 mt-1">Your CSV should look like this:</p>
                                            </div>
                                            <div className="p-6">
                                                <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
                                                    <div className="text-green-400 text-xs font-mono mb-2"># Example CSV file content:</div>
                                                    <div className="text-gray-300 font-mono text-sm space-y-1">
                                                        <div className="text-yellow-400">{expectedHeaders.map(h => h.key).join(',')}</div>
                                                        {sampleData.map((row, index) => (
                                                            <div key={index}>{expectedHeaders.map(h => row[h.key] || '').join(',')}</div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Validation Tips */}
                                    {validationTips.length > 0 && (
                                        <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
                                            <div className="px-6 py-4 border-b border-gray-200">
                                                <h3 className="text-lg font-semibold text-gray-900">💡 Important Tips</h3>
                                            </div>
                                            <div className="p-6">
                                                <div className="space-y-2">
                                                    {validationTips.map((tip, index) => (
                                                        <div key={index} className="flex items-start text-sm">
                                                            <span className="text-brand-green mr-2">•</span>
                                                            <span className="text-gray-700">{tip}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    )}

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
                                </>
                            )}

                            {step === 2 && (
                                <>
                                    {/* Data Preview */}
                                    <div className="bg-white rounded-lg p-5 shadow-sm border border-gray-100">
                                        <div className="flex items-center mb-3">
                                            <div className="w-9 h-9 bg-green-50 rounded-lg flex items-center justify-center mr-3">
                                                <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                                </svg>
                                            </div>
                                            <h3 className="text-base font-medium text-gray-900">
                                                Data Preview ({csvData?.length || 0} rows)
                                            </h3>
                                        </div>

                                        <div className="border border-gray-200 rounded-lg overflow-hidden">
                                            <div className="max-h-64 overflow-auto">
                                                <table className="min-w-full divide-y divide-gray-200">
                                                    <thead className="bg-gray-50">
                                                        <tr>
                                                            {expectedHeaders.map(header => (
                                                                <th key={header.key} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                    {header.label}
                                                                </th>
                                                            ))}
                                                        </tr>
                                                    </thead>
                                                    <tbody className="bg-white divide-y divide-gray-200">
                                                        {csvData?.map((row, index) => (
                                                            <tr key={index} className="hover:bg-gray-50">
                                                                {expectedHeaders.map(header => (
                                                                    <td key={header.key} className="px-4 py-3 text-sm text-gray-900">
                                                                        {header.type === 'number' && row[header.key] ? 
                                                                            `$${row[header.key]}` : 
                                                                            row[header.key] || 'N/A'
                                                                        }
                                                                    </td>
                                                                ))}
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
                                    {/* Results summary similar to existing CSVUploadModal */}
                                    <div className={`rounded-lg p-6 border-2 ${uploadResults.successful_imports > 0 && uploadResults.failed_imports === 0
                                        ? "bg-green-50 border-green-200"
                                        : uploadResults.successful_imports > 0 && uploadResults.failed_imports > 0
                                            ? "bg-yellow-50 border-yellow-200"
                                            : "bg-red-50 border-red-200"
                                        }`}>
                                        <div className="flex items-start">
                                            <div className={`w-12 h-12 rounded-full flex items-center justify-center mr-4 ${uploadResults.successful_imports > 0 && uploadResults.failed_imports === 0
                                                ? "bg-green-100"
                                                : uploadResults.successful_imports > 0 && uploadResults.failed_imports > 0
                                                    ? "bg-yellow-100"
                                                    : "bg-red-100"
                                                }`}>
                                                {uploadResults.successful_imports > 0 && uploadResults.failed_imports === 0 ? (
                                                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                    </svg>
                                                ) : uploadResults.successful_imports > 0 && uploadResults.failed_imports > 0 ? (
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
                                                <h3 className={`text-lg font-semibold mb-2 ${uploadResults.successful_imports > 0 && uploadResults.failed_imports === 0
                                                    ? "text-green-800"
                                                    : uploadResults.successful_imports > 0 && uploadResults.failed_imports > 0
                                                        ? "text-yellow-800"
                                                        : "text-red-800"
                                                    }`}>
                                                    {uploadResults.successful_imports > 0 && uploadResults.failed_imports === 0
                                                        ? "🎉 All Imports Completed Successfully!"
                                                        : uploadResults.successful_imports > 0 && uploadResults.failed_imports > 0
                                                            ? "⚠️ Import Partially Completed"
                                                            : "❌ Import Failed"}
                                                </h3>
                                                <p className={`text-sm ${uploadResults.successful_imports > 0 && uploadResults.failed_imports === 0
                                                    ? "text-green-700"
                                                    : uploadResults.successful_imports > 0 && uploadResults.failed_imports > 0
                                                        ? "text-yellow-700"
                                                        : "text-red-700"
                                                    }`}>
                                                    {uploadResults.successful_imports > 0 && uploadResults.failed_imports === 0
                                                        ? `Perfect! All ${uploadResults.total_rows} records have been imported successfully.`
                                                        : uploadResults.successful_imports > 0 && uploadResults.failed_imports > 0
                                                            ? `${uploadResults.successful_imports} imports completed successfully, but ${uploadResults.failed_imports} failed. Review the errors below.`
                                                            : `None of the ${uploadResults.total_rows} records could be imported. Please review the errors below and fix your CSV file.`}
                                                </p>
                                            </div>
                                        </div>
                                    </div>

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
                                                    <h3 className="text-base font-medium text-gray-900">Import Errors</h3>
                                                </div>
                                                <button
                                                    onClick={downloadResults}
                                                    className="text-sm text-brand-green hover:text-brand-green/80 underline flex items-center gap-1"
                                                >
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                    </svg>
                                                    Download Results
                                                </button>
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
                                                                    </div>
                                                                    <p className="text-sm text-red-700">
                                                                        <span className="font-medium">Error:</span> {error.error_message || error.message}
                                                                    </p>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
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
                                    <span>Review the data above before importing.</span>
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
                                        disabled={!csvData || csvData.length === 0 || isUploading}
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
                                            `Import ${csvData?.length || 0} Records`
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
                                        Import Another File
                                    </button>
                                </div>
                                <button
                                    onClick={() => {
                                        if (uploadResults?.successful_imports > 0 && onSuccess) {
                                            onSuccess(uploadResults);
                                        }
                                        handleClose();
                                    }}
                                    className={`px-5 py-2.5 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all text-sm font-medium shadow-sm ${uploadResults.successful_imports > 0
                                        ? "bg-gradient-to-br from-brand-green to-brand-teal text-white hover:from-brand-green/90 hover:to-brand-teal/90 focus:ring-brand-green"
                                        : "bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500"
                                        }`}
                                >
                                    {uploadResults.successful_imports > 0 ? "🎉 All Done!" : "Close"}
                                </button>
                            </div>
                        )}
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
};

export default CSVImportModal;