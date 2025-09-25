import React, { memo, useRef, useEffect, useState } from "react";
import { FixedSizeList as List } from "react-window";
import { formatCurrency, getStatusColors } from "../utils/api/rentTracker";
import { sanitizeTenantName, sanitizePropertyName, sanitizeCurrency } from "../utils/sanitization";

// Memoized row component for better performance
const RentTrackerRow = memo(({ index, style, data }) => {
  const { 
    items, 
    formatDate, 
    handleRecordPayment,
    columnWidthPercentages,
    isSmallScreen
  } = data;
  
  const rent = items[index];
  if (!rent) {
    return (
      <div style={style} className="flex items-center justify-center text-gray-500">
        Loading...
      </div>
    );
  }
  
  const statusColors = getStatusColors(rent?.status || '');
  
  // Apply zebra striping
  const bgColor = index % 2 === 0 ? "bg-white dark:bg-gray-800" : "bg-gray-50 dark:bg-gray-700";
  
  // Handle keyboard navigation for accessibility
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleRecordPayment(rent);
    }
  };
  
  return (
    <div 
      style={{...style, boxSizing: 'border-box'}} 
      className={`flex items-stretch w-full ${bgColor} hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors border-b border-gray-200 dark:border-gray-700`}
    >
      {/* Tenant */}
      <div className="px-4 py-4 flex items-center" style={{ width: `${columnWidthPercentages.tenant}%`, boxSizing: 'border-box' }}>
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate text-left">
          {sanitizeTenantName(rent?.tenant_name || '')}
        </div>
      </div>
      
      {/* Property / Unit */}
      <div className="px-4 py-4 overflow-hidden" style={{ width: `${columnWidthPercentages.property}%`, boxSizing: 'border-box' }}>
        <div className="text-sm text-gray-900 dark:text-gray-100 text-left truncate" title={sanitizePropertyName(rent?.property_name || '')}>
          {sanitizePropertyName(rent?.property_name || '')}
        </div>
        {rent?.unit_name && (
          <div className="text-xs text-gray-500 dark:text-gray-400 text-left truncate" title={sanitizePropertyName(rent?.unit_name || '')}>
            {sanitizePropertyName(rent?.unit_name || '')}
          </div>
        )}
      </div>
      
      {/* Monthly Rent */}
      <div className="px-4 py-4 flex items-center justify-center" style={{ width: `${columnWidthPercentages.monthlyRent}%`, boxSizing: 'border-box' }}>
        <div className="text-sm text-gray-900 dark:text-gray-100 text-center">
          {formatCurrency(rent?.monthly_rent ?? 0)}
        </div>
      </div>
      
      {/* Amount Paid */}
      <div className="px-4 py-4 flex items-center justify-center" style={{ width: `${columnWidthPercentages.amountPaid}%`, boxSizing: 'border-box' }}>
        <div className="text-sm text-gray-900 dark:text-gray-100 text-center">
          {formatCurrency(rent?.amount_paid ?? 0)}
        </div>
      </div>
      
      {/* Balance Due - Includes status and actions on small screens */}
      <div className={`px-4 py-4 ${isSmallScreen ? '' : 'flex items-center justify-center'}`} style={{ width: `${columnWidthPercentages.balanceDue}%`, boxSizing: 'border-box' }}>
        <div className={`${isSmallScreen ? 'space-y-2' : ''}`}>
          <div className={`text-sm font-medium text-center ${
            Number.parseFloat(rent?.remaining_due ?? 0) > 0 ? "text-red-600 dark:text-red-400" : "text-gray-500 dark:text-gray-400"
          }`}>
            {formatCurrency(rent?.remaining_due ?? 0)}
          </div>
          {isSmallScreen && (
            <div className="flex flex-col space-y-1">
              <span className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors.bg} ${statusColors.text}`}>
                {rent?.status || ''}
              </span>
              <button
                onClick={() => handleRecordPayment(rent)}
                onKeyDown={handleKeyDown}
                className="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 dark:focus:ring-offset-gray-800 rounded px-2 py-1 border border-blue-300 dark:border-blue-600 hover:border-blue-500 dark:hover:border-blue-400"
                tabIndex={0}
              >
                Record Payment
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* Due Date - Hidden on small screens */}
      {columnWidthPercentages.dueDate > 0 && (
        <div className="px-4 py-4 flex items-center justify-center" style={{ width: `${columnWidthPercentages.dueDate}%`, boxSizing: 'border-box' }}>
          <div className="text-center">
            <div className="text-sm text-gray-900 dark:text-gray-100">
              {formatDate(rent?.due_date)}
            </div>
            {rent?.days_overdue && rent.days_overdue > 0 && (
              <div className="text-xs text-red-600 dark:text-red-400">
                {rent.days_overdue} days overdue
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Last Payment - Hidden on small screens */}
      {columnWidthPercentages.lastPayment > 0 && (
        <div className="px-4 py-4 flex items-center justify-center" style={{ width: `${columnWidthPercentages.lastPayment}%`, boxSizing: 'border-box' }}>
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center">
            {formatDate(rent?.last_payment_date)}
          </div>
        </div>
      )}
      
      {/* Status - Hidden on small screens */}
      {!isSmallScreen && columnWidthPercentages.status > 0 && (
        <div className="px-4 py-4 flex items-center justify-center" style={{ width: `${columnWidthPercentages.status}%`, boxSizing: 'border-box' }}>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors.bg} ${statusColors.text}`}>
            {rent?.status || ''}
          </span>
        </div>
      )}
      
      {/* Actions - Hidden on small screens (combined with status) */}
      {!isSmallScreen && columnWidthPercentages.actions > 0 && (
        <div className="px-4 py-4 flex items-center justify-center" style={{ width: `${columnWidthPercentages.actions}%`, boxSizing: 'border-box' }}>
          <button
            onClick={() => handleRecordPayment(rent)}
            onKeyDown={handleKeyDown}
            className="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 dark:focus:ring-offset-gray-800 rounded px-2 py-1"
            tabIndex={0}
          >
            Record Payment
          </button>
        </div>
      )}
    </div>
  );
});

RentTrackerRow.displayName = 'RentTrackerRow';

const RentTrackerVirtualTable = ({ 
  rentData, 
  formatDate, 
  handleRecordPayment,
  searchTerm 
}) => {
  const listRef = useRef();
  const containerRef = useRef();
  const [containerWidth, setContainerWidth] = useState(0);
  
  // Column widths as percentages of total width (must add up to 100%)
  // Optimized responsive column widths for better alignment and space utilization
  const isSmallScreen = containerWidth < 1024; // lg breakpoint
  
  const columnWidthPercentages = isSmallScreen ? {
    tenant: 22,      // 22% - More space for tenant names
    property: 24,    // 24% - More space for property info
    monthlyRent: 16, // 16%
    amountPaid: 16,  // 16%
    balanceDue: 22,  // 22% - More space for balance due including actions
    dueDate: 0,      // Hide on small screens
    lastPayment: 0,  // Hide on small screens  
    status: 0,       // Hide on small screens - combined with balance due
    actions: 0       // Hide on small screens - combined with balance due
  } : {
    tenant: 15,      // 15%
    property: 15,    // 15%
    monthlyRent: 10, // 10%
    amountPaid: 10,  // 10%
    balanceDue: 10,  // 10%
    dueDate: 12,     // 12%
    lastPayment: 12, // 12%
    status: 8,       // 8%
    actions: 8       // 8%
  };
  
  // Note: Using columnWidthPercentages directly for consistent alignment
  
  // Row height in pixels - increased for better mobile experience
  const rowHeight = isSmallScreen ? 90 : 72;
  
  // Calculate optimal height based on data length
  const calculateOptimalHeight = () => {
    const dataHeight = rentData.length * rowHeight;
    const minHeight = 200; // Minimum height for better UX
    const maxHeight = 600; // Maximum height to prevent extremely tall tables
    
    // Use actual data height, but constrain within min/max bounds
    return Math.min(maxHeight, Math.max(minHeight, dataHeight));
  };
  
  const containerHeight = calculateOptimalHeight();
  
  // Use ResizeObserver for reliable container width tracking
  useEffect(() => {
    if (!containerRef.current) return;
    
    // Create ResizeObserver for accurate width tracking
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentBoxSize) {
          // Use contentBoxSize when available (most accurate)
          const contentBoxSize = Array.isArray(entry.contentBoxSize)
            ? entry.contentBoxSize[0]
            : entry.contentBoxSize;
          setContainerWidth(contentBoxSize.inlineSize);
        } else {
          // Fallback to contentRect
          setContainerWidth(entry.contentRect.width);
        }
      }
    });
    
    // Start observing
    resizeObserver.observe(containerRef.current);
    
    // Cleanup
    return () => {
      resizeObserver.disconnect();
    };
  }, []);
  
  // No horizontal scroll needed with percentage-based widths
  
  if (rentData.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden transition-colors duration-300">
        <div className="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
          {searchTerm
            ? `No results found for "${searchTerm}"`
            : "No rent tracking entries found"}
        </div>
      </div>
    );
  }
  
  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden transition-colors duration-300" ref={containerRef}>
      {/* Fixed Header */}
      <div className="border-b-2 border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
        <div className="flex w-full" style={{boxSizing: 'border-box'}}>
          <div className="px-4 py-3" style={{ width: `${columnWidthPercentages.tenant}%`, boxSizing: 'border-box' }}>
            <div className="text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
              Tenant
            </div>
          </div>
          <div className="px-4 py-3" style={{ width: `${columnWidthPercentages.property}%`, boxSizing: 'border-box' }}>
            <div className="text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
              Property
            </div>
          </div>
          <div className="px-4 py-3" style={{ width: `${columnWidthPercentages.monthlyRent}%`, boxSizing: 'border-box' }}>
            <div className="text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
              Rent
            </div>
          </div>
          <div className="px-4 py-3" style={{ width: `${columnWidthPercentages.amountPaid}%`, boxSizing: 'border-box' }}>
            <div className="text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
              Paid
            </div>
          </div>
          <div className="px-4 py-3" style={{ width: `${columnWidthPercentages.balanceDue}%`, boxSizing: 'border-box' }}>
            <div className="text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
              {isSmallScreen ? 'Due/Status/Actions' : 'Due'}
            </div>
          </div>
          {columnWidthPercentages.dueDate > 0 && (
            <div className="px-4 py-3" style={{ width: `${columnWidthPercentages.dueDate}%`, boxSizing: 'border-box' }}>
              <div className="text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
                Due Date
              </div>
            </div>
          )}
          {columnWidthPercentages.lastPayment > 0 && (
            <div className="px-4 py-3" style={{ width: `${columnWidthPercentages.lastPayment}%`, boxSizing: 'border-box' }}>
              <div className="text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
                Last Payment
              </div>
            </div>
          )}
          {!isSmallScreen && columnWidthPercentages.status > 0 && (
            <div className="px-4 py-3" style={{ width: `${columnWidthPercentages.status}%`, boxSizing: 'border-box' }}>
              <div className="text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
                Status
              </div>
            </div>
          )}
          {!isSmallScreen && columnWidthPercentages.actions > 0 && (
            <div className="px-4 py-3" style={{ width: `${columnWidthPercentages.actions}%`, boxSizing: 'border-box' }}>
              <div className="text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
                Actions
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Virtual Scrolling List */}
      <List
        ref={listRef}
        height={containerHeight}
        itemCount={rentData.length}
        itemSize={rowHeight}
        width="100%"
        itemData={{
          items: rentData,
          formatDate,
          handleRecordPayment,
          columnWidthPercentages: columnWidthPercentages,
          isSmallScreen: isSmallScreen
        }}
        overscanCount={5} // Render 5 extra items outside viewport for smoother scrolling
        className="scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-gray-100 dark:scrollbar-thumb-gray-600 dark:scrollbar-track-gray-800"
      >
        {RentTrackerRow}
      </List>
      
      {/* Footer with count */}
      <div className="bg-gray-50 dark:bg-gray-900 px-6 py-3 border-t border-gray-200 dark:border-gray-700">
        <div className="text-sm text-gray-600 dark:text-gray-400">
          Showing {rentData.length} {rentData.length === 1 ? 'entry' : 'entries'}
        </div>
      </div>
    </div>
  );
};

export default RentTrackerVirtualTable;