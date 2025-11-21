import React, { useState, useEffect, useMemo } from "react";
import { toast } from "react-toastify";
import { CSVLink } from "react-csv";
import NewExpenseModal from "./modals/NewExpenseModal";
import EditExpenseModal from "./modals/EditExpenseModal";
import CSVImportModal from "./modals/CSVImportModal";
import { ExpensesTableSkeleton } from "../ui/skeletons";
import { useAccounting } from "./AccountingContext";
import { getDateRangeParams } from "../../utils/dateHelpers";
import { useExpenses, useDeleteExpense } from "../../hooks/useAccountingQueries";
import { importExpensesFromCSV } from "../../utils/api/accounting";
import useProperties from "../../hooks/useProperties";
import useDebounce from "../../hooks/useDebounce";
import { useSubscriptionGuard } from "../../hooks/useSubscriptionGuard";
import type { Expense, ExpenseQueryParams } from "../../types/accounting";
import type { DateRange } from "../../utils/dateHelpers";

interface TableColumn {
  key: string;
  label: string;
  align: "left" | "center" | "right";
}

const expenseTableColumns: TableColumn[] = [
  { key: "property", label: "Property", align: "left" },
  { key: "category", label: "Category", align: "center" },
  { key: "amount", label: "Amount", align: "center" },
  { key: "date", label: "Date", align: "center" },
  { key: "payment_method", label: "Payment Method", align: "center" },
  { key: "receipt", label: "Receipt", align: "center" },
  { key: "source", label: "Source", align: "center" },
  { key: "actions", label: "Actions", align: "center" },
];



interface ExpenseFilters {
  category: string;
  dateRange: string;
}

interface ExpensesPagination {
  currentPage: number;
  limit: number;
  hasMore: boolean;
}

interface CSVHeader {
  label: string;
  key: string;
}

interface CSVDataRow {
  property_name: string;
  category: string;
  total_amount: string;
  expense_date: string;
  payment_method: string;
  description: string;
  subtotal_amount: string;
  tax_amount: string;
  has_receipt: string;
  source: string;
}

const ExpensesTab: React.FC = () => {
  // Subscription guard for premium features
  const guardAction = useSubscriptionGuard({ featureName: 'creating expenses' });

  const { handlePreviewReceipt } = useAccounting();

  // Local state for expenses tab
  const [searchQuery, setSearchQuery] = useState<string>("");
  const debouncedSearchQuery = useDebounce(searchQuery, 500);
  const [expensesPagination, setExpensesPagination] = useState<ExpensesPagination>({
    currentPage: 0,
    limit: 15,
    hasMore: true,
  });
  const [expenseFilters, setExpenseFilters] = useState<ExpenseFilters>({
    category: "all",
    dateRange: "month",
  });

  // Build query parameters
  const queryParams = useMemo<ExpenseQueryParams>(() => {
    const params: ExpenseQueryParams = {
      limit: expensesPagination.limit,
      offset: expensesPagination.currentPage * expensesPagination.limit,
    };

    if (expenseFilters.category !== "all") {
      params.category = expenseFilters.category;
    }

    if (debouncedSearchQuery.trim()) {
      params.search = debouncedSearchQuery.trim();
    }

    // Convert date range to actual date params using utility function
    if (expenseFilters.dateRange !== "all") {
      const dateRangeParams = getDateRangeParams(expenseFilters.dateRange as DateRange);
      Object.assign(params, dateRangeParams);
    }

    return params;
  }, [expenseFilters, expensesPagination.currentPage, expensesPagination.limit, debouncedSearchQuery]);

  // TanStack Query hooks
  const { data: expensesData, isLoading: loading, error, refetch } = useExpenses(queryParams);
  const { properties } = useProperties();
  const deleteExpenseMutation = useDeleteExpense();

  // Extract expenses from paginated response and enhance with property names
  const expenses = useMemo<Expense[]>(() => {
    const expensesList = expensesData?.items || [];
    
    // Create property map for names - ensure properties is an array
    const safeProperties = Array.isArray(properties) ? properties : [];
    const propertyMap = safeProperties.reduce<Record<number, string>>((map, property) => {
      if (property?.id) {
        map[property.id] = property.name;
      }
      return map;
    }, {});

    // Enhance expense data with property names
    return expensesList.map((expense) => ({
      ...expense,
      property_name:
        propertyMap[expense.property_id] ||
        `Property #${expense.property_id}`,
    }));
  }, [expensesData, properties]);

  const hasMore = expensesData?.has_more || false;

  // Modal states
  const [showNewExpenseModal, setShowNewExpenseModal] = useState<boolean>(false);
  const [showEditExpenseModal, setShowEditExpenseModal] = useState<boolean>(false);
  const [showCSVImportModal, setShowCSVImportModal] = useState<boolean>(false);
  const [selectedItem, setSelectedItem] = useState<Expense | null>(null);

  // Effect for handling filter changes - reset to first page
  useEffect(() => {
    setExpensesPagination((prev) => ({ ...prev, currentPage: 0 }));
  }, [expenseFilters]);

  // Update pagination state when query data changes
  useEffect(() => {
    if (expensesData) {
      setExpensesPagination((prev) => ({ ...prev, hasMore: expensesData.has_more || false }));
    }
  }, [expensesData]);

  const handleEditExpense = (expense: Expense) => {
    setSelectedItem(expense);
    setShowEditExpenseModal(true);
  };

  const handleDeleteExpense = async (expenseId: number) => {
    // Find the expense to get its details for the toast message
    const expenseToDelete = expenses.find((exp) => exp.id === expenseId);
    const expenseDescription = expenseToDelete
      ? `${expenseToDelete.category} for ${
          expenseToDelete.property_name ||
          `Property #${expenseToDelete.property_id}`
        }`
      : `Expense ID ${expenseId}`;

    if (
      window.confirm(
        `Are you sure you want to delete this expense: ${expenseDescription}? This action cannot be undone.`
      )
    ) {
      try {
        await deleteExpenseMutation.mutateAsync(expenseId);
        await refetch();
        toast.success(`${expenseDescription} deleted successfully.`);
      } catch (err: unknown) {
        console.error("Failed to delete expense:", err);
        const errorMessage = err instanceof Error ? err.message : "Failed to delete expense.";
        toast.error(errorMessage);
      }
    }
  };

  const handleNextPage = () => {
    setExpensesPagination((prev) => ({
      ...prev,
      currentPage: prev.currentPage + 1,
    }));
  };

  const handlePreviousPage = () => {
    setExpensesPagination((prev) => ({
      ...prev,
      currentPage: Math.max(0, prev.currentPage - 1),
    }));
  };

  const handleShowModal = guardAction(() => {
    setShowNewExpenseModal(true);
  });

  const handleCSVImportSuccess = () => {
    // Refresh the expenses data after successful import
    refetch();
    setShowCSVImportModal(false);
  };

  const handleCloseModal = () => {
    setShowNewExpenseModal(false);
    setShowEditExpenseModal(false);
    setSelectedItem(null);
  };

  // Reset pagination when debounced search query changes
  useEffect(() => {
    setExpensesPagination((prev) => ({ ...prev, currentPage: 0 }));
  }, [debouncedSearchQuery]);

  // CSV Export configuration
  const csvHeaders: CSVHeader[] = [
    { label: 'Property', key: 'property_name' },
    { label: 'Category', key: 'category' },
    { label: 'Amount', key: 'total_amount' },
    { label: 'Date', key: 'expense_date' },
    { label: 'Payment Method', key: 'payment_method' },
    { label: 'Description', key: 'description' },
    { label: 'Subtotal', key: 'subtotal_amount' },
    { label: 'Tax Amount', key: 'tax_amount' },
    { label: 'Has Receipt', key: 'has_receipt' },
    { label: 'Source', key: 'source' },
  ];

  // Format data for CSV export with clean headers
  const getFilterDescription = (): string => {
    const filters: string[] = [];
    if (expenseFilters.category !== 'all') filters.push(`Category: ${expenseFilters.category}`);
    if (expenseFilters.dateRange !== 'all') filters.push(`Date Range: ${expenseFilters.dateRange.replace('_', ' ')}`);
    if (searchQuery) filters.push(`Search: "${searchQuery}"`);
    return filters.length > 0 ? filters.join(', ') : 'No filters applied';
  };

  const csvData: CSVDataRow[] = [
    // Clean header with metadata in a single row
    { 
      property_name: 'Brikli Expenses Report', 
      category: `Exported: ${new Date().toLocaleDateString()}`,
      total_amount: `Filters: ${getFilterDescription()}`,
      expense_date: `Records: ${expenses.length}`,
      payment_method: '', 
      description: '', 
      subtotal_amount: '', 
      tax_amount: '', 
      has_receipt: '', 
      source: '' 
    },
    // Empty separator row
    { property_name: '', category: '', total_amount: '', expense_date: '', payment_method: '', description: '', subtotal_amount: '', tax_amount: '', has_receipt: '', source: '' },
    // Actual data
    ...expenses.map(expense => {
      const totalAmt = Number(expense?.total_amount ?? 0);
      const subtotalAmt = Number(expense?.subtotal_amount ?? 0);
      const taxAmt = Number(expense?.tax_amount ?? 0);
      const expenseDate = expense?.expense_date ? new Date(expense.expense_date) : null;
      return {
        property_name: expense?.property_name || 'N/A',
        category: expense?.category ? expense.category.charAt(0).toUpperCase() + expense.category.slice(1) : 'N/A',
        total_amount: Number.isFinite(totalAmt) ? totalAmt.toFixed(2) : '0.00',
        expense_date: expenseDate && !isNaN(expenseDate.getTime()) ? expenseDate.toLocaleDateString() : 'N/A',
        payment_method: expense?.payment_method || 'Other',
        description: expense?.description || 'N/A',
        subtotal_amount: Number.isFinite(subtotalAmt) ? subtotalAmt.toFixed(2) : '0.00',
        tax_amount: Number.isFinite(taxAmt) ? taxAmt.toFixed(2) : '0.00',
        has_receipt: expense?.receipt_url ? 'Yes' : 'No',
        source: expense?.quickbooks_id ? 'QuickBooks' : 'Brikli',
      };
    })
  ];

  // Generate professional filename with current date and filters
  const generateFilename = (): string => {
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0];
    const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '');
    const filterSuffix = expenseFilters.category !== 'all' ? `-${expenseFilters.category}` : '';
    const searchSuffix = searchQuery ? `-search` : '';
    return `Brikli-Expenses-Report${filterSuffix}${searchSuffix}-${dateStr}-${timeStr}.csv`;
  };

  // CSV Import configuration
  const csvImportConfig = {
    title: "Import Expenses",
    description: "Upload your expense data",
    apiFunction: importExpensesFromCSV,
    expectedHeaders: [
      { key: "category", label: "Category", required: true, aliases: ["category", "expense_category", "type"] },
      { key: "subtotal_amount", label: "Subtotal Amount", required: true, type: "number", aliases: ["subtotal", "amount", "subtotal_amount"] },
      { key: "expense_date", label: "Expense Date", required: true, type: "date", aliases: ["date", "expense_date", "payment_date"] },
      { key: "description", label: "Description", required: false, aliases: ["description", "notes", "memo"] },
      { key: "total_tax_amount", label: "Tax Amount", required: false, type: "number", aliases: ["tax_amount", "tax", "total_tax_amount"] },
      { key: "payment_method", label: "Payment Method", required: false, aliases: ["payment_method", "method", "payment_type"] },
      { key: "property_name", label: "Property Name", required: false, aliases: ["property", "property_name", "property_id"] }
    ],
    sampleData: [
      {
        category: "Maintenance",
        subtotal_amount: 500.00,
        expense_date: "2024-01-15",
        description: "HVAC repair",
        total_tax_amount: 50.00,
        payment_method: "Credit Card",
        property_name: "123 Main St"
      },
      {
        category: "Utilities",
        subtotal_amount: 200.00,
        expense_date: "2024-01-20",
        description: "Electric bill",
        total_tax_amount: 20.00,
        payment_method: "Bank Transfer",
        property_name: "123 Main St"
      }
    ],
    validationTips: [
      "Category is required (e.g., Maintenance, Utilities, Insurance)",
      "Amounts should be positive numbers without currency symbols",
      "Dates should be in YYYY-MM-DD format or MM/DD/YYYY",
      "Payment methods: Credit Card, Debit Card, Bank Transfer, Cash, Check, Other",
      "Property name should match exactly as it appears in your properties list"
    ]
  };

  if (loading) {
    return <ExpensesTableSkeleton rowCount={8} />;
  }

  return (
    <div>
      {error && (
        <div className="bg-red-100 dark:bg-red-900/20 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-400 px-4 py-3 rounded">
          <p>{String(error)}</p>
          <button
            onClick={() => refetch()}
            className="mt-2 bg-red-500 dark:bg-red-600 hover:bg-red-700 dark:hover:bg-red-500 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0 transition-colors duration-300">
        <div className="flex flex-col sm:flex-row sm:space-x-4 space-y-2 sm:space-y-0">
          <div>
            <label
              htmlFor="expense-category"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Category
            </label>
            <select
              id="expense-category"
              className="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={expenseFilters.category}
              onChange={(e) =>
                setExpenseFilters({
                  ...expenseFilters,
                  category: e.target.value,
                })
              }
            >
              <option value="all">All Categories</option>
              <option value="maintenance">Maintenance</option>
              <option value="utilities">Utilities</option>
              <option value="taxes">Taxes</option>
              <option value="insurance">Insurance</option>
              <option value="administrative">Administrative</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="expense-date-range"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Date Range
            </label>
            <select
              id="expense-date-range"
              className="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={expenseFilters.dateRange}
              onChange={(e) =>
                setExpenseFilters({
                  ...expenseFilters,
                  dateRange: e.target.value,
                })
              }
            >
              <option value="week">Last 7 days</option>
              <option value="month">Last 30 days</option>
              <option value="quarter">Last 90 days</option>
              <option value="year">Last year</option>
              <option value="all">All Time</option>
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="relative rounded-md shadow-sm">
            <input
              type="search"
              placeholder="Search expenses..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 pr-3 py-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-md text-sm"
            />
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <i className="fas fa-search text-gray-400 dark:text-gray-500"></i>
            </div>
          </div>
          
          {/* Import CSV Button */}
          <button
            onClick={() => setShowCSVImportModal(true)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-upload mr-2"></i>
            Import CSV
          </button>

          {/* Export CSV Button */}
          <CSVLink
            data={csvData}
            headers={csvHeaders}
            filename={generateFilename()}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-download mr-2"></i>
            Export CSV
          </CSVLink>
          
          {/* New Expense Button */}
          <button
            onClick={handleShowModal}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-plus mr-2"></i>
            New Expense
          </button>
        </div>
      </div>

      {/* Expenses Table */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden transition-colors duration-300">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                {expenseTableColumns.map((col) => (
                  <th
                    key={col.key}
                    scope="col"
                    className={`px-6 py-3 ${
                      col.align === "left"
                        ? "text-left"
                        : col.align === "center"
                        ? "text-center"
                        : "text-right"
                    } text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider`}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {expenses.length > 0 ? (
                expenses.map((expense, index) => {
                  // Zebra striping with alternating dark grays
                  const isEven = index % 2 === 0;
                  const bgColor = isEven 
                    ? "bg-white dark:bg-gray-800" 
                    : "bg-gray-50 dark:bg-gray-700/50";
                  
                  return (
                  <tr key={expense.id} className={`${bgColor} hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors duration-150`}>
                    <td className="px-6 py-4 whitespace-nowrap text-left">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {expense.property_name ||
                          `Property #${expense.property_id}` ||
                          "Unknown Property"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {expense.category.charAt(0).toUpperCase() +
                          expense.category.slice(1)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="text-sm text-gray-900 dark:text-gray-100">
                        ${parseFloat(String(expense.total_amount)).toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {new Date(expense.expense_date).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {expense.payment_method || "Other"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {expense.receipt_url ? (
                          <button
                            type="button"
                            onClick={() => expense.receipt_url && handlePreviewReceipt(
                              expense.receipt_url,
                              `Receipt: ${expense.category} on ${
                                expense.property_name ||
                                "Property " + expense.property_id
                              } - ${new Date(
                                expense.expense_date
                              ).toLocaleDateString()}`
                            )}
                            disabled={!expense.receipt_url}
                            className={`font-medium ${
                              expense.receipt_url
                                ? "text-emerald-600 dark:text-emerald-400 hover:text-emerald-800 dark:hover:text-emerald-300"
                                : "text-gray-400 dark:text-gray-500 cursor-not-allowed"
                            }`}
                            aria-disabled={!expense.receipt_url}
                            title={expense.receipt_url ? "View Receipt" : "No receipt available"}
                          >
                            <i className="fas fa-eye" />
                          </button>
                        ) : (
                          <span className="text-gray-400 dark:text-gray-500 text-xs">None Uploaded</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {expense.quickbooks_id != null
                          ? "QuickBooks"
                          : "Brikli"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="flex justify-center space-x-2">
                        <button
                          type="button"
                          onClick={() => handleEditExpense(expense)}
                          className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300 p-1"
                          title="Edit Expense"
                        >
                          <i className="fas fa-edit" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteExpense(expense.id)}
                          className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 p-1"
                          title="Delete Expense"
                        >
                          <i className="fas fa-trash-alt" />
                        </button>
                      </div>
                    </td>
                  </tr>
                  );
                })
              ) : (
                <tr>
                  <td
                    colSpan={expenseTableColumns.length}
                    className="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400"
                  >
                    {searchQuery.trim()
                      ? `No expenses found matching "${searchQuery}"`
                      : "No expenses found"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {/* Pagination Controls */}
        <div className="flex justify-between items-center mt-4 p-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          <button
            type="button"
            onClick={handlePreviousPage}
            disabled={expensesPagination.currentPage === 0 || loading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Go to previous page"
          >
            <i className="fas fa-arrow-left mr-2" aria-hidden="true" />
            Previous
          </button>
          <span className="text-sm text-gray-700 dark:text-gray-300">
            Page {expensesPagination.currentPage + 1}
          </span>
          <button
            type="button"
            onClick={handleNextPage}
            disabled={!hasMore || loading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Go to next page"
          >
            Next
            <i className="fas fa-arrow-right ml-2" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Modals */}
      {showNewExpenseModal && (
        <NewExpenseModal
          isOpen={showNewExpenseModal}
          onClose={handleCloseModal}
          onSuccess={() => {
            setShowNewExpenseModal(false);
            refetch();
          }}
        />
      )}

      {showEditExpenseModal && selectedItem && (
        <EditExpenseModal
          isOpen={showEditExpenseModal}
          onClose={() => {
            setShowEditExpenseModal(false);
            setSelectedItem(null);
          }}
          onSuccess={() => {
            setShowEditExpenseModal(false);
            setSelectedItem(null);
            refetch();
          }}
          expenseData={selectedItem ? {
            ...selectedItem,
            receipt_url: selectedItem.receipt_url || undefined
          } : undefined}
        />
      )}

      {showCSVImportModal && (
        <CSVImportModal
          isOpen={showCSVImportModal}
          onClose={() => setShowCSVImportModal(false)}
          onSuccess={handleCSVImportSuccess}
          config={csvImportConfig}
        />
      )}
    </div>
  );
};

export default ExpensesTab;
