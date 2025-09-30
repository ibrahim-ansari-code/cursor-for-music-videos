import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { previewQuickBooksSync } from '../../utils/api/quickbooks';

interface SyncItem {
  entity_type: string;
  entity_id: string;
  entity_name: string;
  action: string;
  details: {
    amount?: number;
    date?: string;
    destination?: string; // "QuickBooks" or undefined (means Brikli)
    [key: string]: any;
  };
  warnings: string[];
}

interface SyncPreview {
  items: SyncItem[];
  summary: {
    create: number;
    update: number;
    skip: number;
    error: number;
    total: number;
  };
  warnings: string[];
}

interface SimpleSyncPreviewProps {
  isOpen: boolean;
  onClose: () => void;
  onSyncComplete: () => void;
  onSync: () => Promise<any>; // Pass the actual sync function
}

const SimpleSyncPreview: React.FC<SimpleSyncPreviewProps> = ({
  isOpen,
  onClose,
  onSyncComplete,
  onSync
}) => {
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [preview, setPreview] = useState<SyncPreview | null>(null);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [expandedWarnings, setExpandedWarnings] = useState<Set<string>>(new Set());

  // Load preview when modal opens
  useEffect(() => {
    if (isOpen) {
      loadPreview();
    }
  }, [isOpen]);

  // Select all actionable items by default when preview loads
  useEffect(() => {
    if (preview) {
      const actionableItems = preview.items
        .filter(item => item.action !== 'skip' && item.action !== 'error')
        .map(item => `${item.entity_type}-${item.entity_id}`);
      setSelectedItems(new Set(actionableItems));
    }
  }, [preview]);

  const loadPreview = async () => {
    try {
      setLoading(true);
      const previewData = await previewQuickBooksSync();
      setPreview(previewData);
    } catch (error) {
      console.error('Error loading sync preview:', error);
      toast.error('Failed to load sync preview');
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      const result = await onSync();

      // Handle the response properly
      if (result && typeof result === 'object') {
        if (result.success === true) {
          const successMessage = result.message && typeof result.message === 'string'
            ? result.message
            : 'Sync completed successfully!';
          toast.success(successMessage);
          onSyncComplete();
        } else {
          const errorMessage = result.message && typeof result.message === 'string'
            ? result.message
            : 'Sync operation failed';

          const errorDetails = result.errors && Array.isArray(result.errors) && result.errors.length > 0
            ? ` Details: ${result.errors.join(', ')}`
            : '';

          toast.error(errorMessage + errorDetails);
        }
      } else {
        // Handle unexpected response format
        toast.error('Sync completed but received unexpected response format');
        onSyncComplete(); // Still complete the flow
      }
    } catch (error: any) {
      console.error('Error during sync:', error);
      const errorMessage = error?.message && typeof error.message === 'string'
        ? error.message
        : 'Sync operation failed due to network or server error';
      toast.error(errorMessage);
    } finally {
      setSyncing(false);
    }
  };

  const toggleItemSelection = (itemKey: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(itemKey)) {
      newSelected.delete(itemKey);
    } else {
      newSelected.add(itemKey);
    }
    setSelectedItems(newSelected);
  };

  const toggleSelectAll = () => {
    if (!preview) return;

    const actionableItems = preview.items
      .filter(item => item.action !== 'skip' && item.action !== 'error')
      .map(item => `${item.entity_type}-${item.entity_id}`);

    const allSelected = actionableItems.every(key => selectedItems.has(key));

    if (allSelected) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(actionableItems));
    }
  };

  const toggleWarningExpansion = (itemKey: string) => {
    const newExpanded = new Set(expandedWarnings);
    if (newExpanded.has(itemKey)) {
      newExpanded.delete(itemKey);
    } else {
      newExpanded.add(itemKey);
    }
    setExpandedWarnings(newExpanded);
  };

  const getSyncDirection = (item: SyncItem): { source: string; destination: string } => {
    // If destination is explicitly "QuickBooks", it's being pushed to QuickBooks
    if (item.details.destination === 'QuickBooks') {
      return {
        source: 'Brikli',
        destination: 'QuickBooks'
      };
    }
    // Otherwise, it's being pulled from QuickBooks to Brikli
    return {
      source: 'QuickBooks',
      destination: 'Brikli'
    };
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'create': return '✅';
      case 'update': return '🔄';
      case 'skip': return '⏭️';
      case 'error': return '❌';
      default: return '❓';
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'create': return 'text-green-600 dark:text-green-400';
      case 'update': return 'text-blue-600 dark:text-blue-400';
      case 'skip': return 'text-gray-500 dark:text-gray-400';
      case 'error': return 'text-red-600 dark:text-red-400';
      default: return 'text-gray-600 dark:text-gray-300';
    }
  };

  const actionableItems = preview?.items.filter(item => item.action !== 'skip' && item.action !== 'error') || [];
  const selectedCount = selectedItems.size;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              QuickBooks Sync Preview
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <i className="fas fa-times text-xl" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6 overflow-y-auto max-h-[calc(90vh-160px)]">
          {loading ? (
            <div className="text-center py-12">
              <i className="fas fa-spinner fa-spin text-3xl text-blue-600 mb-4" />
              <p className="text-gray-600 dark:text-gray-400">Loading sync preview...</p>
            </div>
          ) : preview ? (
            <div className="space-y-6">
              {/* Summary */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  📊 Summary
                </h3>
                <div className="flex items-center space-x-6 text-sm">
                  <span className="text-green-600 dark:text-green-400">
                    {preview.summary.create} to create
                  </span>
                  <span className="text-blue-600 dark:text-blue-400">
                    {preview.summary.update} to update
                  </span>
                  <span className="text-gray-500 dark:text-gray-400">
                    {preview.summary.skip} to skip
                  </span>
                  {preview.summary.error > 0 && (
                    <span className="text-red-600 dark:text-red-400">
                      {preview.summary.error} errors
                    </span>
                  )}
                </div>
              </div>

              {/* Global Warnings */}
              {preview.warnings.length > 0 && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                  <div className="flex">
                    <i className="fas fa-exclamation-triangle text-yellow-400 mr-3 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-1">
                        Warnings
                      </h4>
                      <ul className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1">
                        {preview.warnings.map((warning, index) => (
                          <li key={index}>• {warning}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Items List */}
              {preview.items.length > 0 ? (
                <div className="space-y-4">
                  {/* Select All */}
                  <div className="flex items-center space-x-3 pb-3 border-b border-gray-200 dark:border-gray-600">
                    <input
                      type="checkbox"
                      checked={actionableItems.length > 0 && actionableItems.every(item =>
                        selectedItems.has(`${item.entity_type}-${item.entity_id}`)
                      )}
                      onChange={toggleSelectAll}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Select All ({actionableItems.length} items)
                    </label>
                  </div>

                  {/* Items Table */}
                  <div className="space-y-2">
                    {preview.items.map((item, index) => {
                      const itemKey = `${item.entity_type}-${item.entity_id}`;
                      const isActionable = item.action !== 'skip' && item.action !== 'error';
                      const isSelected = selectedItems.has(itemKey);
                      const syncDirection = getSyncDirection(item);
                      const hasWarnings = item.warnings.length > 0;
                      const warningsExpanded = expandedWarnings.has(itemKey);

                      return (
                        <div
                          key={index}
                          className={`rounded-lg border ${
                            isSelected && isActionable
                              ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                              : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600'
                          }`}
                        >
                          {/* Main Item Row */}
                          <div className="flex items-center space-x-3 p-3">
                            {/* Checkbox */}
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleItemSelection(itemKey)}
                              disabled={!isActionable}
                              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 disabled:opacity-50"
                            />

                            {/* Action Icon */}
                            <span className="text-lg">
                              {getActionIcon(item.action)}
                            </span>

                            {/* Item Details */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                                      {item.entity_name}
                                    </p>
                                    {/* Sync Direction Badge */}
                                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 whitespace-nowrap">
                                      <span>{syncDirection.source}</span>
                                      <i className="fas fa-arrow-right text-[10px]" aria-hidden="true" />
                                      <span>{syncDirection.destination}</span>
                                    </span>
                                  </div>
                                  <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                                    {item.entity_type}
                                    {item.details.amount && (
                                      <span className="ml-2 font-medium">
                                        ${typeof item.details.amount === 'number' ? item.details.amount.toFixed(2) : item.details.amount}
                                      </span>
                                    )}
                                  </p>
                                </div>
                                <div className="text-right flex items-center gap-2">
                                  <span className={`text-sm font-medium capitalize ${getActionColor(item.action)}`}>
                                    {item.action}
                                  </span>
                                  {hasWarnings && (
                                    <button
                                      onClick={() => toggleWarningExpansion(itemKey)}
                                      className="text-xs text-yellow-600 dark:text-yellow-400 hover:text-yellow-700 dark:hover:text-yellow-300 flex items-center gap-1 px-2 py-1 rounded hover:bg-yellow-50 dark:hover:bg-yellow-900/20"
                                    >
                                      <i className="fas fa-exclamation-triangle" />
                                      {item.warnings.length}
                                      <i className={`fas fa-chevron-${warningsExpanded ? 'up' : 'down'} text-xs ml-1`} />
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Expandable Warnings Section */}
                          {hasWarnings && warningsExpanded && (
                            <div className="px-3 pb-3 pt-0">
                              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-3 ml-7">
                                <div className="flex items-start">
                                  <i className="fas fa-exclamation-triangle text-yellow-500 mt-0.5 mr-2" />
                                  <div className="flex-1">
                                    <p className="text-xs font-medium text-yellow-800 dark:text-yellow-200 mb-1">
                                      Warning{item.warnings.length !== 1 ? 's' : ''}:
                                    </p>
                                    <ul className="text-xs text-yellow-700 dark:text-yellow-300 space-y-1">
                                      {item.warnings.map((warning, wIndex) => (
                                        <li key={wIndex} className="flex items-start">
                                          <span className="mr-1">•</span>
                                          <span>{warning}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <i className="fas fa-info-circle text-3xl mb-4" />
                  <p>No items found to sync</p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <i className="fas fa-exclamation-circle text-3xl mb-4" />
              <p>Failed to load sync preview</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-t dark:border-gray-600">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {selectedCount > 0 && (
                <span>{selectedCount} item{selectedCount !== 1 ? 's' : ''} selected</span>
              )}
            </div>

            <div className="flex space-x-3">
              <button
                onClick={onClose}
                disabled={syncing}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-md hover:bg-gray-50 dark:hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>

              <button
                onClick={handleSync}
                disabled={syncing || selectedCount === 0 || loading}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {syncing ? (
                  <>
                    <i className="fas fa-spinner fa-spin mr-2" />
                    Syncing...
                  </>
                ) : (
                  <>
                    Sync {selectedCount > 0 ? selectedCount : ''} Selected
                    <i className="fas fa-arrow-right ml-2" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleSyncPreview;