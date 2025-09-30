/**
 * Type definitions for the Integrations page and related components
 */

// Integration status types
export type IntegrationStatus = 'connected' | 'not_connected' | 'connecting' | 'disconnecting' | 'error';

export type SyncOperation = 'payments' | 'invoices' | 'expenses' | 'initial' | 'all';

// QuickBooks API response types
export interface QuickBooksStatus {
  connected: boolean;
  connected_at?: string;
  company_name?: string;
  last_sync?: string;
  error?: string;
}

export interface QuickBooksSyncResponse {
  success: boolean;
  message: string;
  synced_count?: number;
  failed_count?: number;
  errors?: string[];
}

export interface QuickBooksConnectResponse {
  success: boolean;
  redirect_url?: string;
  error?: string;
}

// Operation state using discriminated unions for better type safety
export type OperationState =
  | { type: 'idle' }
  | { type: 'loading'; operation?: string }
  | { type: 'syncing'; operation: SyncOperation }
  | { type: 'error'; message: string };

// Component prop interfaces
export interface ErrorMessageProps {
  error: string | null;
  onRetry: () => void;
}

export interface QuickBooksCardProps {
  status: QuickBooksStatus | null;
  operationState: OperationState;
  onConnect: () => void;
  onDisconnect: () => void;
  onSyncAll: () => void;
  disabled?: boolean; // For temporarily disabling functionality
}

export interface PlaceholderCardProps {
  title?: string;
  description?: string;
  icon?: string;
  className?: string;
}

export interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'primary' | 'secondary';
  isLoading?: boolean;
}

// Custom hook return types
export interface UseQuickBooksIntegrationReturn {
  // State
  status: QuickBooksStatus | null;
  operationState: OperationState;
  showConfirmDisconnect: boolean;

  // Actions
  handleConnect: () => Promise<void>;
  handleDisconnect: () => void;
  handleConfirmDisconnect: () => Promise<void>;
  handleCancelDisconnect: () => void;
  handleSyncAll: () => Promise<void>;

  // Utilities
  refreshStatus: () => Promise<void>;
  isOperationInProgress: boolean;
}

// URL parameter types removed as they're now handled directly in useQuickBooksIntegration

// Integration card data structure for future extensibility
export interface IntegrationProvider {
  id: string;
  name: string;
  description: string;
  logoUrl: string;
  status: IntegrationStatus;
  isEnabled: boolean;
  comingSoon?: boolean;
  features?: string[];
}

// Event types for better error handling and analytics
export interface IntegrationEvent {
  type: 'connect' | 'disconnect' | 'sync' | 'error';
  provider: string;
  operation?: SyncOperation;
  timestamp: Date;
  success: boolean;
  error?: string;
  metadata?: Record<string, any>;
}

// Performance optimization types
export interface IntegrationsPageState {
  quickBooksStatus: QuickBooksStatus | null;
  operationState: OperationState;
  showConfirmDisconnect: boolean;
  lastRefresh: Date | null;
}

// API error response structure
export interface IntegrationApiError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
  operation?: SyncOperation;
}