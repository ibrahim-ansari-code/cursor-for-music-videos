import React, { useState, useEffect, useMemo } from "react";
import { 
  fetchExpenses, 
  fetchProperties, 
  deleteExpense 
} from "../../utils/api";
import { toast } from "react-toastify";
import NewExpenseModal from "../NewExpenseModal";
import EditExpenseModal from "../EditExpenseModal";
import LoadingSpinner from "../LoadingSpinner";
import { useAccounting } from "./AccountingContext";
import { getDateRangeParams } from "../../utils/dateHelpers";

const expenseTableColumns = [
  { key: "property", label: "Property", align: "left" },
  { key: "category", label: "Category", align: "left" },
  { key: "amount", label: "Amount", align: "left" },
  { key: "date", label: "Date", align: "left" },
  { key: "source", label: "Source", align: "left" },
  { key: "actions", label: "Actions", align: "center" },
];

// Reusable loading spinner row for tables
const LoadingRow = ({ colSpan, loadingText }) => (
  <tr>
    <td
      colSpan={colSpan}
      className="px-6 py-12 text-center text-sm text-gray-500"
    >
      <LoadingSpinner message={loadingText} size="medium" center={false} />
    </td>
  </tr>
);

const ExpensesTab = () => {
  const {
    loading,
    setLoading,
    error,
    setError,
    handlePreviewReceipt,
  } = useAccounting();

  // Local state for expenses tab
  const [expenses, setExpenses] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [expenseFilters, setExpenseFilters] = useState({
    category: "all",
    dateRange: "month",
  });

  // Modal states
  const [showNewExpenseModal, setShowNewExpenseModal] = useState(false);
  const [showEditExpenseModal, setShowEditExpenseModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);

  useEffect(() => {
    loadExpensesData();
  }, [expenseFilters]);

  const loadExpensesData = async () => {
    try {
      setLoading(true);

      const params = {};
      if (expenseFilters.category !== "all") {
        params.category = expenseFilters.category;
      }

      // Convert date range to actual date params using utility function
      const dateRangeParams = getDateRangeParams(expenseFilters.dateRange);
      Object.assign(params, dateRangeParams);

      const data = await fetchExpenses(params);

      // Try to fetch property data for names, but don't fail if user has no properties
      let propertyMap = {};
      try {
        const properties = await fetchProperties();
        // Map property IDs to names
        propertyMap = properties.reduce((map, property) => {
          map[property.id] = property.name;
          return map;
        }, {});
      } catch (propErr) {
        console.log("No properties found, using property IDs instead of names");
        // Continue without property names
      }

      // Enhance expense data with property names
      const enhancedExpenses = data.map((expense) => ({
        ...expense,
        property_name:
          propertyMap[expense.property_id] ||
          `Property #${expense.property_id}`,
      }));

      setExpenses(enhancedExpenses);
      setError(null);
    } catch (err) {
      console.error("Error loading expenses data:", err);
      setError("Failed to load expenses data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleEditExpense = (expense) => {
    setSelectedItem(expense);
    setShowEditExpenseModal(true);
  };

  const handleDeleteExpense = async (expenseId) => {
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
        await deleteExpense(expenseId);
        toast.success(`${expenseDescription} deleted successfully.`);
        loadExpensesData(); // Refresh the list
      } catch (err) {
        console.error("Failed to delete expense:", err);
        toast.error(err.message || "Failed to delete expense.");
      }
    }
  };

  const handleShowModal = () => {
    setShowNewExpenseModal(true);
  };

  const handleCloseModal = () => {
    setShowNewExpenseModal(false);
    setShowEditExpenseModal(false);
    setSelectedItem(null);
  };

  // Filter expenses based on search query
  const filteredExpenses = useMemo(() => {
    if (!searchQuery.trim()) {
      return expenses;
    }

    const query = searchQuery.toLowerCase();
    return expenses.filter(expense => {
      const propertyName = (expense.property_name || `Property #${expense.property_id}` || "").toLowerCase();
      const category = (expense.category || "").toLowerCase();
      const amount = expense.total_amount ? parseFloat(expense.total_amount).toFixed(2) : "";
      const date = expense.expense_date ? new Date(expense.expense_date).toLocaleDateString() : "";
      
      return propertyName.includes(query) ||
             category.includes(query) ||
             amount.includes(query) ||
             date.includes(query);
    });
  }, [expenses, searchQuery]);

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
          <button
            onClick={loadExpensesData}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end space-x-3">
        <button
          onClick={handleShowModal}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <i className="fas fa-plus mr-2"></i>
          New Expense
        </button>

        <button
          onClick={() => {
            /* Export functionality would go here */
          }}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <i className="fas fa-file-export mr-2"></i>
          Export
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
        <div className="flex flex-col sm:flex-row sm:space-x-4 space-y-2 sm:space-y-0">
          <div>
            <label
              htmlFor="expense-category"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Category
            </label>
            <select
              id="expense-category"
              className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
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
            </select>
          </div>

          <div>
            <label
              htmlFor="expense-date-range"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Date Range
            </label>
            <select
              id="expense-date-range"
              className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
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
            </select>
          </div>
        </div>

        <div className="flex items-center">
          <div className="relative rounded-md shadow-sm">
            <input
              type="search"
              placeholder="Search expenses..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 pr-3 py-2 border-gray-300 rounded-md text-sm"
            />
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <i className="fas fa-search text-gray-400"></i>
            </div>
          </div>
        </div>
      </div>

      {/* Expenses Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
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
                    } text-xs font-medium text-gray-500 uppercase tracking-wider`}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <LoadingRow colSpan={expenseTableColumns.length} loadingText="Loading expenses..." />
              ) : filteredExpenses.length > 0 ? (
                filteredExpenses.map((expense) => (
                  <tr key={expense.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-left">
                      <div className="text-sm font-medium text-gray-900">
                        {expense.property_name ||
                          `Property #${expense.property_id}` ||
                          "Unknown Property"}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-left">
                      <div className="text-sm text-gray-500">
                        {expense.category.charAt(0).toUpperCase() +
                          expense.category.slice(1)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-left">
                      <div className="text-sm text-gray-900">
                        ${parseFloat(expense.total_amount).toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-left">
                      <div className="text-sm text-gray-500">
                        {new Date(expense.expense_date).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-left">
                      <div className="text-sm text-gray-500">
                        {expense.quickbooks_id != null ? 'QuickBooks' : 'Brikli'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="flex justify-center space-x-2">
                        {expense.receipt_url && (
                          <button
                            type="button"
                            onClick={() =>
                              handlePreviewReceipt(
                                expense.receipt_url,
                                `Receipt: ${expense.category} on ${
                                  expense.property_name ||
                                  "Property " + expense.property_id
                                } - ${new Date(
                                  expense.expense_date
                                ).toLocaleDateString()}`
                              )
                            }
                            className="text-blue-600 hover:text-blue-900 p-1"
                            title="View Receipt"
                          >
                            <i className="fas fa-eye" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleEditExpense(expense)}
                          className="text-indigo-600 hover:text-indigo-900 p-1"
                          title="Edit Expense"
                        >
                          <i className="fas fa-edit" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteExpense(expense.id)}
                          className="text-red-600 hover:text-red-900 p-1"
                          title="Delete Expense"
                        >
                          <i className="fas fa-trash-alt" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={expenseTableColumns.length}
                    className="px-6 py-4 text-center text-sm text-gray-500"
                  >
                    {searchQuery.trim() ? `No expenses found matching "${searchQuery}"` : "No expenses found"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modals */}
      {showNewExpenseModal && (
        <NewExpenseModal
          isOpen={showNewExpenseModal}
          onClose={handleCloseModal}
          onSuccess={() => {
            setShowNewExpenseModal(false);
            loadExpensesData();
            toast.success("Expense created successfully");
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
            loadExpensesData();
            toast.success("Expense updated successfully");
          }}
          expenseData={selectedItem}
        />
      )}
    </div>
  );
};

export default ExpensesTab;