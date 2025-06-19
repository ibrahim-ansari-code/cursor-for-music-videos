# Frontend Architecture Documentation

## Overview

This document outlines the architecture patterns and shared components used throughout the Brikli frontend application.

## Shared Receipt Upload Pattern

### Architecture Overview

The receipt upload functionality has been refactored into a reusable, consistent pattern that can be used across different modals (expenses, payments, invoices, etc.). This pattern provides:

- **Consistent UI/UX** across all receipt upload interfaces
- **Centralized receipt parsing logic** with AI-powered data extraction
- **Reusable state management** for upload, parsing, and preview workflows
- **Type-safe integration** with different API endpoints

### Core Components

#### 1. `ReceiptUploadAndPreview` Component

Located in: `src/components/ui/SharedModalComponents.jsx`

**Purpose**: Main UI component that provides file upload, parsing feedback, and preview toggle functionality.

**Props**:
- State props: `isParsingReceipt`, `receiptParseError`, `currentReceiptUrl`, `showReceiptPreview`
- Handler props: `onReceiptFileChange`, `setShowReceiptPreview`
- Configuration props: `disabled`, `title`, `subtitle`, `acceptedFileTypes`, `className`

**Features**:
- File upload input with validation
- Loading states with AI parsing feedback
- Error handling and display
- Success states with preview toggle
- Configurable titles and accepted file types

#### 2. `ReceiptPreview` Component

Located in: `src/components/ui/SharedModalComponents.jsx`

**Purpose**: Displays receipt previews with support for different file types (PDF, images).

**Security Features**:
- Sandboxed iframes with `allow-same-origin allow-scripts` attributes
- Safe rendering of different file types
- Animated show/hide transitions

#### 3. `useReceiptUpload` Hook

Located in: `src/components/ui/SharedModalComponents.jsx`

**Purpose**: Centralized state management for receipt upload workflows.

**State Management**:
```javascript
const receiptState = useReceiptUpload(initialReceiptUrl);
// Returns:
// - State: receiptFile, isParsingReceipt, receiptParseError, currentReceiptUrl, showReceiptPreview
// - Setters: setReceiptFile, setIsParsingReceipt, setReceiptParseError, etc.
// - Actions: resetReceiptState
```

**Features**:
- Automatic cleanup of abort controllers
- Reset functionality for modal reuse
- Consistent state structure across components

#### 4. `createReceiptFileChangeHandler` Helper

Located in: `src/components/ui/SharedModalComponents.jsx`

**Purpose**: Factory function that creates file change handlers for different API endpoints.

**Parameters**:
- `parseReceiptAPI`: API function for parsing receipts
- `receiptState`: State object from `useReceiptUpload` hook
- `onDataExtracted`: Callback function for handling extracted data

**Features**:
- Generic API integration
- Automatic error handling
- Abort controller management
- Customizable data extraction callbacks

### Implementation Pattern

#### Step 1: Import Required Components

```javascript
import {
  ReceiptUploadAndPreview,
  useReceiptUpload,
  createReceiptFileChangeHandler
} from './ui/SharedModalComponents';
import { parseExpenseReceiptAPI } from '../utils/api';
```

#### Step 2: Initialize Receipt State

```javascript
const receiptState = useReceiptUpload(existingReceiptUrl);
```

#### Step 3: Create File Change Handler

```javascript
const handleReceiptFileChange = createReceiptFileChangeHandler(
  parseExpenseReceiptAPI, // API endpoint for parsing
  receiptState,           // State management object
  (parsedDetails, receiptUrl) => {
    // Handle extracted data with functional setState to avoid stale closures
    setFormData((prev) => {
      const extractedData = extractExpenseReceiptData(parsedDetails, prev);
      
      // Show success message
      toast.success(extractedData.successMessage);
      
      // Return updated form data
      return {
        ...prev,
        amount: extractedData.amount,
        taxes: extractedData.taxes,
        expense_date: extractedData.expense_date,
        description: extractedData.description,
      };
    });
  }
);
```

#### Step 4: Render Component

```javascript
<ReceiptUploadAndPreview
  {...receiptState}
  onReceiptFileChange={handleReceiptFileChange}
  title="Upload and Parse Receipt (Optional)"
  subtitle="Auto-extracts tax, amount, date & description"
  disabled={isLoading}
/>
```

### Best Practices

#### 1. Functional setState Pattern

Always use functional form of `setState` in the `onDataExtracted` callback to avoid stale closure issues:

```javascript
// ✅ Correct - Uses latest state
setFormData((prev) => {
  const extractedData = extractExpenseReceiptData(parsedDetails, prev);
  return { ...prev, ...extractedData };
});

// ❌ Incorrect - May use stale state
const extractedData = extractExpenseReceiptData(parsedDetails, formData);
setFormData(prev => ({ ...prev, ...extractedData }));
```

#### 2. API-Specific Extraction Utilities

Create utility functions for each domain to handle data extraction:

```javascript
// For expenses
import { extractExpenseReceiptData } from '../utils/receiptUtils';

// For payments  
import { extractPaymentReceiptData } from '../utils/receiptUtils';
```

#### 3. Error Handling

The pattern automatically handles:
- File upload errors
- API parsing errors
- Network timeouts
- User cancellation (abort controllers)

#### 4. State Reset

Always reset receipt state when modals open/close:

```javascript
useEffect(() => {
  if (isOpen) {
    receiptState.resetReceiptState();
  }
}, [isOpen]);
```

### Security Considerations

1. **Iframe Sandboxing**: All iframe previews use `sandbox="allow-same-origin allow-scripts"` attributes
2. **File Type Validation**: Strict file type checking on both frontend and backend. Accepted types are: `image/jpeg`, `image/png`, `application/pdf`.
3. **File Size Limits**: Enforced limits to prevent abuse. Maximum file size is 10MB.
4. **Abort Controllers**: Proper cleanup prevents memory leaks and race conditions

### Example Implementations

#### Expense Modal Usage

File: `src/components/NewExpenseModal.jsx`

```javascript
const handleReceiptFileChange = createReceiptFileChangeHandler(
  parseExpenseReceiptAPI,
  receiptState,
  (parsedDetails, receiptUrl) => {
    setFormData((prev) => {
      const extractedData = extractExpenseReceiptData(parsedDetails, prev);
      toast.success(extractedData.successMessage);
      return {
        ...prev,
        amount: extractedData.amount,
        taxes: extractedData.taxes,
        expense_date: extractedData.expense_date,
        description: extractedData.description,
      };
    });
  }
);
```

#### Payment Modal Usage

File: `src/components/EditPaymentModal.jsx`

```javascript
const handleReceiptFileChange = createReceiptFileChangeHandler(
  parsePaymentReceiptAPI,
  receiptState,
  (parsedDetails, receiptUrl) => {
    setFormData((prev) => {
      const extractedData = extractPaymentReceiptData(parsedDetails, prev);
      toast.success("Receipt parsed and ready to save.");
      return {
        ...prev,
        amount: extractedData.amount,
        payment_method: extractedData.payment_method,
        // ... other payment fields
      };
    });
  }
);
```

### Data Flow

1. **User selects file** → `ReceiptUploadAndPreview` triggers `onReceiptFileChange`
2. **File validation** → `createReceiptFileChangeHandler` validates file type/size
3. **API call** → Sends file to appropriate parsing API (expenses, payments, etc.)
4. **AI processing** → Backend uses LLM to extract structured data
5. **Data extraction** → `onDataExtracted` callback processes parsed data
6. **State update** → Form data updated with extracted information
7. **User feedback** → Success message shown, preview available

### Extension Points

To add receipt upload to a new modal:

1. **Create API endpoint** for your domain (e.g., `parseInvoiceReceiptAPI`)
2. **Create extraction utility** (e.g., `extractInvoiceReceiptData`)
3. **Follow implementation pattern** as shown above
4. **Configure domain-specific** titles, subtitles, and accepted file types

This pattern ensures consistency while remaining flexible for different business domains within the application.