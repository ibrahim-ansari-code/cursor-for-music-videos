import Papa from 'papaparse';

/**
 * CSV Parser Utility for Bulk Unit Assignment
 * 
 * Handles parsing CSV files and validating data for bulk unit assignments.
 * Expected CSV format: Unit Number,Tenant Email,Lease Start Date,Monthly Rent,Security Deposit (optional)
 * 
 * Uses papaparse library for robust CSV parsing that handles:
 * - Quoted fields containing commas
 * - Escaped quotes
 * - Various CSV formats and edge cases
 */

/**
 * Parse CSV text content into structured data
 * @param {string} csvText - Raw CSV content
 * @returns {Array} Array of parsed row objects
 */
export const parseCSV = (csvText) => {
    // Use papaparse for robust CSV parsing
    const parseResult = Papa.parse(csvText.trim(), {
        header: false, // We'll handle headers manually for better control
        skipEmptyLines: true,
        trimHeaders: true,
        delimiter: ',',
        quoteChar: '"',
        escapeChar: '"'
    });

    if (parseResult.errors.length > 0) {
        const errorMessages = parseResult.errors.map(err => `Row ${err.row + 1}: ${err.message}`).join('; ');
        throw new Error(`CSV parsing errors: ${errorMessages}`);
    }

    const lines = parseResult.data;
    if (lines.length < 2) {
        throw new Error('CSV must contain at least a header row and one data row');
    }

    // Parse header row
    const headers = lines[0].map(header => (header || '').trim());

    // Support both user-friendly and technical column names
    const expectedHeaders = [
        { userFriendly: 'Unit Number', technical: 'unit_number', required: true },
        { userFriendly: 'Tenant Email', technical: 'tenant_email', required: true },
        { userFriendly: 'Lease Start Date', technical: 'lease_start_date', required: true },
        { userFriendly: 'Monthly Rent', technical: 'monthly_rent', required: true },
        { userFriendly: 'Security Deposit', technical: 'security_deposit', required: false }
    ];

    // Create header mapping (supports both formats)
    const headerMap = {};
    expectedHeaders.forEach(({ userFriendly, technical }) => {
        const friendlyIndex = headers.findIndex(header =>
            header.toLowerCase().replace(/[^a-z]/g, '') === userFriendly.toLowerCase().replace(/[^a-z]/g, '')
        );
        const technicalIndex = headers.findIndex(header =>
            header.toLowerCase() === technical.toLowerCase()
        );

        const foundIndex = friendlyIndex !== -1 ? friendlyIndex : technicalIndex;
        if (foundIndex !== -1) {
            headerMap[technical] = foundIndex;
        }
    });

    // Validate required headers
    const missingHeaders = expectedHeaders.filter(({ technical, required }) =>
        required && !(technical in headerMap)
    );

    if (missingHeaders.length > 0) {
        const friendlyNames = missingHeaders.map(({ userFriendly }) => userFriendly);
        throw new Error(`Missing required columns: ${friendlyNames.join(', ')}`);
    }

    // Parse data rows
    const rows = [];
    const errors = [];

    for (let i = 1; i < lines.length; i++) {
        const values = lines[i];
        if (!values || values.every(val => !val || !val.trim())) continue; // Skip empty lines

        try {
            const row = {
                rowNumber: i + 1,
                unit_number: (values[headerMap.unit_number] || '').trim(),
                tenant_email: (values[headerMap.tenant_email] || '').trim(),
                lease_start_date: (values[headerMap.lease_start_date] || '').trim(),
                monthly_rent: (() => {
                    const value = parseFloat((values[headerMap.monthly_rent] || '').replace(/[$,]/g, ''));
                    return isNaN(value) ? null : value;
                })(),
                security_deposit: headerMap.security_deposit !== undefined ? 
                    parseFloat((values[headerMap.security_deposit] || '').replace(/[$,]/g, '')) || null : null
            };

            // Basic validation
            if (!row.unit_number) {
                errors.push(`Row ${i + 1}: Unit number is required (must match exactly how the unit appears in your property)`);
                continue;
            }

            if (!row.tenant_email) {
                errors.push(`Row ${i + 1}: Tenant email is required`);
                continue;
            }

            // Validate email format
            if (!isValidEmail(row.tenant_email)) {
                errors.push(`Row ${i + 1}: Invalid email format for '${row.tenant_email}'`);
                continue;
            }

            if (!row.lease_start_date) {
                errors.push(`Row ${i + 1}: Lease start date is required`);
                continue;
            }

            if (row.monthly_rent === null || row.monthly_rent <= 0) {
                errors.push(`Row ${i + 1}: Valid monthly rent is required`);
                continue;
            }

            // Normalize and validate date - require ISO format to avoid ambiguity
            const normalizedDate = normalizeDateString(row.lease_start_date);
            if (!normalizedDate) {
                errors.push(`Row ${i + 1}: Invalid date format '${row.lease_start_date}'. Please use YYYY-MM-DD format to avoid ambiguity (e.g., 2024-12-31)`);
                continue;
            }

            // Validate date is not in the past (timezone-safe)
            const leaseDate = new Date(`${normalizedDate}T00:00:00.000Z`);
            const now = new Date();
            const todayUTC = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
            
            if (leaseDate.getTime() < todayUTC.getTime()) {
                errors.push(`Row ${i + 1}: Lease start date cannot be in the past`);
                continue;
            }

            row.lease_start_date = normalizedDate;
            rows.push(row);

        } catch (error) {
            errors.push(`Row ${i + 1}: ${error.message}`);
        }
    }

    if (errors.length > 0) {
        throw new Error(`CSV validation errors:\n${errors.join('\n')}`);
    }

    return rows;
};

/**
 * Validate email format
 * @param {string} email 
 * @returns {boolean}
 */
export const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
};

/**
 * Normalize date string to YYYY-MM-DD format
 * Now requires ISO format to avoid MM/DD vs DD/MM ambiguity
 * @param {string} dateStr 
 * @returns {string|null} Normalized date string or null if invalid
 */
export const normalizeDateString = (dateStr) => {
    if (!dateStr) return null;

    const cleanedDate = dateStr.trim();

    // First, try ISO format (YYYY-MM-DD) - preferred format
    if (/^\d{4}-\d{2}-\d{2}$/.test(cleanedDate)) {
        const date = new Date(cleanedDate + 'T00:00:00.000Z');
        if (date instanceof Date && !isNaN(date)) {
            return cleanedDate;
        }
    }

    // For backward compatibility, still support common formats but with warnings
    // However, we'll be strict about format to avoid ambiguity
    
    // Try MM/DD/YYYY format (US format)
    const usDateMatch = cleanedDate.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (usDateMatch) {
        const [, month, day, year] = usDateMatch;
        const paddedMonth = month.padStart(2, '0');
        const paddedDay = day.padStart(2, '0');
        const normalizedDate = `${year}-${paddedMonth}-${paddedDay}`;
        const date = new Date(normalizedDate + 'T00:00:00.000Z');
        if (date instanceof Date && !isNaN(date)) {
            // Log warning about ambiguous format
            console.warn(`Date ${cleanedDate} interpreted as MM/DD/YYYY. Consider using YYYY-MM-DD format to avoid ambiguity.`);
            return normalizedDate;
        }
    }

    // Try DD/MM/YYYY format (International format) - only if month > 12
    const intlDateMatch = cleanedDate.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (intlDateMatch) {
        const [, day, month, year] = intlDateMatch;
        // Only interpret as DD/MM if first number > 12 (can't be month)
        if (parseInt(day) > 12) {
            const paddedMonth = month.padStart(2, '0');
            const paddedDay = day.padStart(2, '0');
            const normalizedDate = `${year}-${paddedMonth}-${paddedDay}`;
            const date = new Date(normalizedDate + 'T00:00:00.000Z');
            if (date instanceof Date && !isNaN(date)) {
                console.warn(`Date ${cleanedDate} interpreted as DD/MM/YYYY. Consider using YYYY-MM-DD format to avoid ambiguity.`);
                return normalizedDate;
            }
        }
    }

    return null;
};

/**
 * Read file content as text
 * @param {File} file 
 * @returns {Promise<string>}
 */
export const readFileAsText = (file) => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(new Error('Failed to read file'));
        reader.readAsText(file);
    });
};

/**
 * Generate sample CSV content for download
 * @returns {string} Sample CSV content
 */
export const generateSampleCSV = () => {
    const headers = ['Unit Number', 'Tenant Email', 'Lease Start Date', 'Monthly Rent', 'Security Deposit'];
    const sampleRows = [
        ['101', 'john.doe@example.com', '2024-12-01', '1500.00', '1500.00'],
        ['102', 'jane.smith@example.com', '2024-12-15', '1600.00', '3200.00'],
        ['Unit-A', 'tenant@example.com', '2025-01-01', '1400.00', '']  // Empty security deposit will default to null
    ];

    const csvContent = [
        headers.join(','),
        ...sampleRows.map(row => row.join(','))
    ].join('\n');

    return csvContent;
};

/**
 * Download sample CSV file
 */
export const downloadSampleCSV = () => {
    const csvContent = generateSampleCSV();
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', 'bulk_assignment_sample.csv');
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
};

/**
 * Validate CSV file
 * @param {File} file 
 * @returns {Object} Validation result
 */
export const validateCSVFile = (file) => {
    const errors = [];
    
    if (!file) {
        errors.push('No file selected');
        return { isValid: false, errors };
    }

    if (file.type !== 'text/csv' && !file.name.toLowerCase().endsWith('.csv')) {
        errors.push('File must be a CSV file');
    }

    if (file.size > 5 * 1024 * 1024) { // 5MB limit
        errors.push('File size must be less than 5MB');
    }

    if (file.size === 0) {
        errors.push('File cannot be empty');
    }

    return {
        isValid: errors.length === 0,
        errors
    };
};