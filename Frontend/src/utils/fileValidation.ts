/**
 * File Validation Utility
 *
 * Provides client-side file validation for uploads to prevent:
 * - Malicious file types from being sent to the server
 * - Excessive file sizes that could cause performance issues
 * - Poor user experience from delayed server-side validation failures
 *
 * Security Note: This is CLIENT-SIDE validation only. Server-side validation
 * is still required as client-side checks can be bypassed.
 */

import * as Sentry from '@sentry/react';

/**
 * Allowed image MIME types for uploads
 * Restricts to common, safe image formats
 */
export const ALLOWED_IMAGE_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/gif',
  'image/webp',
] as const;

/**
 * Allowed image file extensions
 * Used for filename-based validation as a fallback
 */
export const ALLOWED_IMAGE_EXTENSIONS = [
  '.jpg',
  '.jpeg',
  '.png',
  '.gif',
  '.webp',
] as const;

/**
 * Maximum file size in bytes (10MB)
 * Prevents excessive uploads that could impact performance
 */
export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB in bytes

/**
 * Maximum file size in human-readable format
 */
export const MAX_FILE_SIZE_MB = 10;

/**
 * File validation error codes for consistent error handling
 */
export enum FileValidationError {
  INVALID_TYPE = 'INVALID_TYPE',
  FILE_TOO_LARGE = 'FILE_TOO_LARGE',
  NO_FILE = 'NO_FILE',
}

/**
 * Result of file validation
 */
export interface FileValidationResult {
  isValid: boolean;
  error?: FileValidationError;
  message?: string;
}

/**
 * Validates a file for image upload
 *
 * @param file - The file to validate
 * @param options - Optional validation parameters
 * @returns Validation result with error details if invalid
 *
 * @example
 * ```typescript
 * const result = validateImageFile(file);
 * if (!result.isValid) {
 *   toast.error(result.message);
 *   return;
 * }
 * // Proceed with upload
 * ```
 */
export function validateImageFile(
  file: File | null | undefined,
  options?: {
    maxSizeMB?: number;
    allowedTypes?: readonly string[];
  }
): FileValidationResult {
  const maxSize = (options?.maxSizeMB || MAX_FILE_SIZE_MB) * 1024 * 1024;
  const allowedTypes = options?.allowedTypes || ALLOWED_IMAGE_TYPES;

  // Check if file exists
  if (!file) {
    const error: FileValidationResult = {
      isValid: false,
      error: FileValidationError.NO_FILE,
      message: 'No file selected',
    };

    // Track validation failure in Sentry
    Sentry.captureMessage('File upload validation failed: No file', {
      level: 'warning',
      tags: {
        validation_type: 'file_upload',
        error_code: FileValidationError.NO_FILE,
      },
    });

    return error;
  }

  // Validate file type by MIME type
  if (!allowedTypes.includes(file.type)) {
    // Also check file extension as a fallback
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    const isExtensionAllowed = ALLOWED_IMAGE_EXTENSIONS.some(ext => ext === fileExtension);

    if (!isExtensionAllowed) {
      const error: FileValidationResult = {
        isValid: false,
        error: FileValidationError.INVALID_TYPE,
        message: `Invalid file type. Please upload an image file (${ALLOWED_IMAGE_EXTENSIONS.join(', ')})`,
      };

      // Track validation failure in Sentry with context
      Sentry.captureMessage('File upload validation failed: Invalid type', {
        level: 'warning',
        tags: {
          validation_type: 'file_upload',
          error_code: FileValidationError.INVALID_TYPE,
        },
        contexts: {
          file: {
            name: file.name,
            type: file.type,
            size: file.size,
          },
        },
      });

      return error;
    }
  }

  // Validate file size
  if (file.size > maxSize) {
    const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
    const error: FileValidationResult = {
      isValid: false,
      error: FileValidationError.FILE_TOO_LARGE,
      message: `File size (${fileSizeMB}MB) exceeds maximum allowed size of ${options?.maxSizeMB || MAX_FILE_SIZE_MB}MB`,
    };

    // Track validation failure in Sentry with file size context
    Sentry.captureMessage('File upload validation failed: File too large', {
      level: 'warning',
      tags: {
        validation_type: 'file_upload',
        error_code: FileValidationError.FILE_TOO_LARGE,
      },
      contexts: {
        file: {
          name: file.name,
          type: file.type,
          size: file.size,
          size_mb: fileSizeMB,
          max_size_mb: options?.maxSizeMB || MAX_FILE_SIZE_MB,
        },
      },
    });

    return error;
  }

  // File is valid
  return {
    isValid: true,
  };
}

/**
 * Validates multiple files for batch upload
 *
 * @param files - Array of files to validate
 * @param options - Optional validation parameters
 * @returns Array of validation results, one per file
 *
 * @example
 * ```typescript
 * const results = validateImageFiles(fileList);
 * const invalidFiles = results.filter(r => !r.result.isValid);
 * if (invalidFiles.length > 0) {
 *   // Show errors for invalid files
 * }
 * ```
 */
export function validateImageFiles(
  files: FileList | File[] | null | undefined,
  options?: {
    maxSizeMB?: number;
    allowedTypes?: readonly string[];
  }
): Array<{ file: File; result: FileValidationResult }> {
  if (!files || files.length === 0) {
    return [];
  }

  const fileArray = Array.from(files);
  return fileArray.map(file => ({
    file,
    result: validateImageFile(file, options),
  }));
}

/**
 * Type guard to check if a validation result indicates an error
 *
 * @param result - Validation result to check
 * @returns True if the result has an error
 */
export function hasValidationError(result: FileValidationResult): result is Required<FileValidationResult> {
  return !result.isValid && !!result.error && !!result.message;
}

/**
 * Gets a user-friendly error message for a validation error code
 *
 * @param errorCode - The error code from validation
 * @returns User-friendly error message
 */
export function getValidationErrorMessage(errorCode: FileValidationError): string {
  switch (errorCode) {
    case FileValidationError.NO_FILE:
      return 'Please select a file to upload';
    case FileValidationError.INVALID_TYPE:
      return `Only image files are allowed (${ALLOWED_IMAGE_EXTENSIONS.join(', ')})`;
    case FileValidationError.FILE_TOO_LARGE:
      return `File size must not exceed ${MAX_FILE_SIZE_MB}MB`;
    default:
      return 'Invalid file';
  }
}
