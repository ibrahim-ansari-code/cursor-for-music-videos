import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';

// Calculate current date values outside component to prevent recalculation on every render
const CURRENT_MONTH = new Date().getMonth() + 1;
const CURRENT_YEAR = new Date().getFullYear();

const AccountingContext = createContext();

export const useAccounting = () => {
  const context = useContext(AccountingContext);
  if (!context) {
    throw new Error('useAccounting must be used within an AccountingProvider');
  }
  return context;
};

export const AccountingProvider = ({ children }) => {
  // Shared state across all accounting tabs
  const [overviewData, setOverviewData] = useState(null);
  const [accountingData, setAccountingData] = useState({
    monthly: { revenue: 0, expenses: 0, netIncome: 0 },
    ytd: { revenue: 0, expenses: 0, netIncome: 0 },
    snapshot: { occupancyRate: 0, paidRent: 0, totalRent: 0, avgRent: 0 },
  });
  const [incomeByPropertyData, setIncomeByPropertyData] = useState([]);
  
  // Global loading and error states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Shared modal states
  const [showFilePreviewModal, setShowFilePreviewModal] = useState(false);
  const [fileToPreviewUrl, setFileToPreviewUrl] = useState(null);
  const [filePreviewName, setFilePreviewName] = useState("File Preview");

  // Current month and year for rent tracker (calculated once outside component)
  const currentMonth = CURRENT_MONTH;
  const currentYear = CURRENT_YEAR;

  // Shared functions
  const refreshOverviewData = useCallback(() => {
    // This will be implemented when we extract the overview loading logic
  }, []);

  const handlePreviewReceipt = useCallback((url, name = "Receipt") => {
    setFileToPreviewUrl(url);
    setFilePreviewName(name);
    setShowFilePreviewModal(true);
  }, []);

  const closeFilePreview = useCallback(() => {
    setShowFilePreviewModal(false);
    setFileToPreviewUrl(null);
    setFilePreviewName("File Preview");
  }, []);

  const updateAccountingMetrics = useCallback((newData) => {
    setAccountingData(prev => ({ ...prev, ...newData }));
  }, []);

  const contextValue = useMemo(() => ({
    // State
    overviewData,
    setOverviewData,
    accountingData,
    setAccountingData,
    incomeByPropertyData,
    setIncomeByPropertyData,
    loading,
    setLoading,
    error,
    setError,
    
    // Modal state
    showFilePreviewModal,
    setShowFilePreviewModal,
    fileToPreviewUrl,
    setFileToPreviewUrl,
    filePreviewName,
    setFilePreviewName,
    
    // Constants
    currentMonth,
    currentYear,
    
    // Functions
    refreshOverviewData,
    handlePreviewReceipt,
    closeFilePreview,
    updateAccountingMetrics,
  }), [
    // State dependencies
    overviewData,
    accountingData,
    incomeByPropertyData,
    loading,
    error,
    showFilePreviewModal,
    fileToPreviewUrl,
    filePreviewName,
    currentMonth,
    currentYear,
    // Function dependencies (already memoized with useCallback)
    refreshOverviewData,
    handlePreviewReceipt,
    closeFilePreview,
    updateAccountingMetrics,
  ]);

  return (
    <AccountingContext.Provider value={contextValue}>
      {children}
    </AccountingContext.Provider>
  );
};

export default AccountingContext;