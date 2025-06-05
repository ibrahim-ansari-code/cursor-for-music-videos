import React, { useState, useEffect } from "react";
import {
  fetchPayments,
  fetchInvoices,
  fetchExpenses,
  getAccountingOverview,
  fetchProperties,
  fetchOutstandingPayments,
  fetchRentTracker,
  fetchReportSummary,
  deletePaymentAPI,
  deleteExpenseAPI,
} from "../utils/api";
import { toast } from "react-toastify";
import NewPaymentModal from "../components/NewPaymentModal";
import EditPaymentModal from "../components/EditPaymentModal";
import NewExpenseModal from "../components/NewExpenseModal";
import FilePreviewModal from "../components/FilePreviewModal";
import MonthlyMetricsCard from "../components/MonthlyMetricsCard";
import YTDCard from "../components/YTDCard";
import SnapshotCard from "../components/SnapshotCard";
import RentTracker from "../components/RentTracker";
import RevenueChart from "../components/RevenueChart";
import ExpenseBreakdownChart from "../components/ExpenseBreakdownChart";
import IncomeByPropertyCard from "../components/IncomeByPropertyCard";
import EditExpenseModal from "../components/EditExpenseModal";

const Accounting = () => {
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Data states
  const [payments, setPayments] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [overviewData, setOverviewData] = useState(null);
  const [accountingData, setAccountingData] = useState({
    monthly: { revenue: 0, expenses: 0, netIncome: 0 },
    ytd: { revenue: 0, expenses: 0, netIncome: 0 },
    snapshot: { occupancyRate: 0, paidRent: 0, totalRent: 0, avgRent: 0 },
  });
  const [incomeByPropertyData, setIncomeByPropertyData] = useState([]);

  // Add state for rent tracker data
  const [rentTrackerData, setRentTrackerData] = useState([]);
  const [currentMonth] = useState(new Date().getMonth() + 1); // JavaScript months are 0-indexed
  const [currentYear] = useState(new Date().getFullYear());

  // Modal states
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState(null); // 'payment', 'invoice', 'expense'
  const [showNewPaymentModal, setShowNewPaymentModal] = useState(false);
  const [showEditPaymentModal, setShowEditPaymentModal] = useState(false);
  const [showNewExpenseModal, setShowNewExpenseModal] = useState(false);

  // State for file preview modal
  const [showFilePreviewModal, setShowFilePreviewModal] = useState(false);
  const [fileToPreviewUrl, setFileToPreviewUrl] = useState(null);
  const [filePreviewName, setFilePreviewName] = useState("File Preview");

  // Filter states
  const [paymentFilters, setPaymentFilters] = useState({
    status: "all",
    dateRange: "all_time",
  });

  const [invoiceFilters, setInvoiceFilters] = useState({
    status: "all",
    dateRange: "month",
  });

  const [expenseFilters, setExpenseFilters] = useState({
    category: "all",
    dateRange: "month",
  });

  // Add state for selected payment/expense for editing/deleting
  const [selectedItem, setSelectedItem] = useState(null);

  // Add state for outstanding payments
  const [outstandingPayments, setOutstandingPayments] = useState([]);

  // Add state for edit expense modal
  const [showEditExpenseModal, setShowEditExpenseModal] = useState(false);

  // Get overdue payments from rent tracker data
  const overduePayments = rentTrackerData.filter(
    (rent) => rent.status === "DUE" || rent.status === "PARTIAL"
  );

  useEffect(() => {
    if (activeTab === "overview") {
      loadOverviewData();
      loadOutstandingPayments();
      loadRentTrackerData(); // Load rent tracker data for overview
      loadExpensesData(); // Load expenses data for pie chart
      loadIncomeByProperty(); // Load income by property data
    } else if (activeTab === "payments") {
      loadPaymentsData();
    } else if (activeTab === "invoices") {
      loadInvoicesData();
    } else if (activeTab === "expenses") {
      loadExpensesData();
    }
  }, [activeTab, paymentFilters, invoiceFilters, expenseFilters]);

  const loadRentTrackerData = async () => {
    try {
      const data = await fetchRentTracker({
        month: currentMonth,
        year: currentYear,
      });
      setRentTrackerData(data);

      // Calculate paid and total rent
      const totalRent = data.length;
      const paidRent = data.filter((rent) => rent.status === "PAID").length;

      // Update the accounting data with rent tracking information
      setAccountingData((prevData) => ({
        ...prevData,
        snapshot: {
          ...prevData.snapshot,
          paidRent,
          totalRent,
        },
      }));
    } catch (err) {
      console.error("Error loading rent tracker data:", err);
    }
  };

  const loadOverviewData = async () => {
    try {
      setLoading(true);
      const data = await getAccountingOverview();
      setOverviewData(data);

      // Update the accounting data structure for the cards using the new API fields
      setAccountingData((prevData) => ({
        monthly: {
          revenue: data.monthly_revenue,
          expenses: data.monthly_expenses,
          netIncome: data.monthly_net_income,
        },
        ytd: {
          revenue: data.ytd_revenue,
          expenses: data.ytd_expenses,
          netIncome: data.ytd_net_income,
        },
        snapshot: {
          occupancyRate: data.occupancy_rate,
          paidRent: prevData.snapshot.paidRent,
          totalRent: prevData.snapshot.totalRent,
          avgRent: data.average_rent,
        },
      }));

      setError(null);
    } catch (err) {
      console.error("Error loading overview data:", err);
      setError("Failed to load accounting overview. Please try again.");
      toast.error("Failed to load accounting overview");
    } finally {
      setLoading(false);
    }
  };

  const loadPaymentsData = async (fetchAll = false) => {
    try {
      setLoading(true);

      const params = {};
      console.log("Loading payments with filters:", paymentFilters);

      if (paymentFilters.status !== "all") {
        // Ensure status is sent with initial cap to match backend enum
        params.payment_status =
          paymentFilters.status.charAt(0).toUpperCase() +
          paymentFilters.status.slice(1);
      }

      // Convert date range to actual date params
      const today = new Date();
      if (paymentFilters.dateRange === "week") {
        const weekAgo = new Date();
        weekAgo.setDate(today.getDate() - 7);
        params.start_date = weekAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      } else if (paymentFilters.dateRange === "month") {
        const monthAgo = new Date();
        monthAgo.setMonth(today.getMonth() - 1);
        params.start_date = monthAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      } else if (paymentFilters.dateRange === "quarter") {
        const quarterAgo = new Date();
        quarterAgo.setMonth(today.getMonth() - 3);
        params.start_date = quarterAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      } else if (paymentFilters.dateRange === "year") {
        const yearAgo = new Date();
        yearAgo.setFullYear(today.getFullYear() - 1);
        params.start_date = yearAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      } else if (paymentFilters.dateRange === "all_time") {
        // If dateRange is "all_time", no date params are set, so all payments are fetched (unless other filters apply)
      }

      console.log("API params being sent for payments:", params);
      const data = await fetchPayments(params);
      console.log("Payments received from API:", data);
      setPayments(data);
      setError(null);
    } catch (err) {
      console.error("Error loading payments data:", err);
      setError("Failed to load payments data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const loadInvoicesData = async () => {
    try {
      setLoading(true);

      const params = {};
      if (invoiceFilters.status !== "all") {
        // Ensure status is sent with initial cap to match backend enum
        params.status =
          invoiceFilters.status.charAt(0).toUpperCase() +
          invoiceFilters.status.slice(1);
      }

      // Convert date range to actual date params
      if (invoiceFilters.dateRange === "week") {
        const today = new Date();
        const weekAgo = new Date();
        weekAgo.setDate(today.getDate() - 7);
        params.start_date = weekAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      } else if (invoiceFilters.dateRange === "month") {
        const today = new Date();
        const monthAgo = new Date();
        monthAgo.setMonth(today.getMonth() - 1);
        params.start_date = monthAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      }

      const data = await fetchInvoices(params);
      setInvoices(data);
      setError(null);
    } catch (err) {
      console.error("Error loading invoices data:", err);
      setError("Failed to load invoices data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const loadExpensesData = async () => {
    try {
      setLoading(true);

      const params = {};
      if (expenseFilters.category !== "all") {
        params.category = expenseFilters.category;
      }

      // Convert date range to actual date params
      const today = new Date();
      if (expenseFilters.dateRange === "week") {
        const weekAgo = new Date();
        weekAgo.setDate(today.getDate() - 7);
        params.start_date = weekAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      } else if (expenseFilters.dateRange === "month") {
        const monthAgo = new Date();
        monthAgo.setMonth(today.getMonth() - 1);
        params.start_date = monthAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      } else if (expenseFilters.dateRange === "quarter") {
        const quarterAgo = new Date();
        quarterAgo.setMonth(today.getMonth() - 3);
        params.start_date = quarterAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      } else if (expenseFilters.dateRange === "year") {
        const yearAgo = new Date();
        yearAgo.setFullYear(today.getFullYear() - 1);
        params.start_date = yearAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      }

      const data = await fetchExpenses(params);

      // Fetch property data to get property names
      const properties = await fetchProperties();

      // Map property IDs to names
      const propertyMap = properties.reduce((map, property) => {
        map[property.id] = property.name;
        return map;
      }, {});

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

  // Add function to load outstanding payments
  const loadOutstandingPayments = async () => {
    try {
      const data = await fetchOutstandingPayments();
      setOutstandingPayments(data);
    } catch (err) {
      console.error("Error loading outstanding payments:", err);
      toast.error("Failed to load outstanding payments");
    }
  };

  // Function to load Income By Property data
  const loadIncomeByProperty = async () => {
    try {
      // Fetch using the reports summary endpoint, default to current month
      const reportParams = { date_range: "Current Month" };
      const reportData = await fetchReportSummary(reportParams);

      // Map the data to the format expected by IncomeByPropertyCard
      const mappedData = reportData.income_by_property.map((item) => ({
        id: item.property_id, // Use property_id as key
        name: item.property,
        monthlyIncome: item.monthly_income,
        occupancyRate: item.occupancy_rate,
      }));

      setIncomeByPropertyData(mappedData);
    } catch (err) {
      console.error("Error loading income by property data:", err);
      toast.error("Failed to load income by property chart data.");
      setIncomeByPropertyData([]); // Set to empty on error
    }
  };

  const handleShowModal = (type) => {
    if (type === "payment") {
      setShowNewPaymentModal(true);
    } else if (type === "expense") {
      setShowNewExpenseModal(true);
    } else {
      setModalType(type);
      setShowModal(true);
    }
  };

  const handleCloseModal = () => {
    setShowNewPaymentModal(false);
    setShowNewExpenseModal(false);
    setShowModal(false);
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case "paid":
        return "badge-success";
      case "pending":
      case "partial":
        return "badge-warning";
      case "late":
      case "overdue":
        return "badge-danger";
      default:
        return "badge-info";
    }
  };

  // Add function to handle editing a payment
  const handleEditPayment = (payment) => {
    console.log("Edit payment clicked:", payment);
    setSelectedItem(payment);
    setShowEditPaymentModal(true);
  };

  // Add function to handle deleting a payment
  const handleDeletePayment = async (paymentId) => {
    console.log("Delete payment clicked, ID:", paymentId);
    if (
      window.confirm(
        "Are you sure you want to delete this payment? This action cannot be undone."
      )
    ) {
      try {
        await deletePaymentAPI(paymentId);
        toast.success("Payment deleted successfully.");
        loadPaymentsData(true);
      } catch (err) {
        console.error("Failed to delete payment:", err);
        toast.error(err.message || "Failed to delete payment.");
      }
    }
  };

  const handlePreviewReceipt = (url, name = "Payment Receipt") => {
    setFileToPreviewUrl(url);
    setFilePreviewName(name);
    setShowFilePreviewModal(true);
  };

  const handleEditExpense = (expense) => {
    console.log("Edit expense clicked:", expense);
    setSelectedItem(expense);
    setShowEditExpenseModal(true);
  };

  const handleDeleteExpense = async (expenseId) => {
    console.log("Delete expense clicked, ID:", expenseId);
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
        await deleteExpenseAPI(expenseId);
        toast.success(`${expenseDescription} deleted successfully.`);
        loadExpensesData(); // Refresh the list
        loadOverviewData(); // Refresh overview data as expenses changed
      } catch (err) {
        console.error("Failed to delete expense:", err);
        toast.error(err.message || "Failed to delete expense.");
      }
    }
  };

  if (loading && activeTab === "overview") {
    return (
      <div className="p-4 flex justify-center items-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-3 text-gray-600">Loading accounting data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
          <button
            onClick={() => {
              if (activeTab === "overview") loadOverviewData();
              else if (activeTab === "payments") loadPaymentsData();
              else if (activeTab === "invoices") loadInvoicesData();
              else if (activeTab === "expenses") loadExpensesData();
            }}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}

      <div className="border-b border-gray-200 flex justify-between items-center">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab("overview")}
            className={`${
              activeTab === "overview"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab("payments")}
            className={`${
              activeTab === "payments"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Payments
          </button>
          <button
            onClick={() => setActiveTab("expenses")}
            className={`${
              activeTab === "expenses"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Expenses
          </button>
          <button
            onClick={() => setActiveTab("rent-tracker")}
            className={`${
              activeTab === "rent-tracker"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Rent Tracker
          </button>
          <button
            onClick={() => setActiveTab("invoices")}
            className={`${
              activeTab === "invoices"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Invoices
          </button>
        </nav>

        {activeTab !== "overview" && activeTab !== "invoices" && (
          <div className="flex space-x-3">
            <button
              onClick={() =>
                handleShowModal(
                  activeTab === "payments"
                    ? "payment"
                    : activeTab === "invoices"
                    ? "invoice"
                    : "expense"
                )
              }
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <i className="fas fa-plus mr-2"></i>
              {activeTab === "payments"
                ? "New Payment"
                : activeTab === "invoices"
                ? "New Invoice"
                : "New Expense"}
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
        )}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Financial Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <MonthlyMetricsCard data={accountingData.monthly} />
            <YTDCard data={accountingData.ytd} />
            <SnapshotCard data={accountingData.snapshot} />
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue Chart */}
            <div className="bg-white rounded-lg shadow-sm p-6 h-full">
              <div className="flex items-center mb-4">
                <h2 className="text-lg font-medium text-gray-800">
                  Revenue Breakdown
                </h2>
              </div>
              <RevenueChart
                data={
                  overviewData?.revenue_trends
                    ? {
                        months: overviewData.revenue_trends.map(
                          (month) => month.period
                        ),
                        revenue: overviewData.revenue_trends.map(
                          (month) => month.revenue
                        ),
                        expenses: overviewData.revenue_trends.map(
                          (month) => month.expenses
                        ),
                        net_income: overviewData.revenue_trends.map(
                          (month) => month.net_income
                        ),
                      }
                    : null
                }
              />
            </div>

            {/* Expense Breakdown Chart */}
            <div className="bg-white rounded-lg shadow-sm p-6 h-full">
              <div className="flex items-center mb-4">
                <h2 className="text-lg font-medium text-gray-800">
                  Expense Breakdown
                </h2>
              </div>
              <ExpenseBreakdownChart expenses={expenses} />
            </div>
          </div>

          {/* Occupancy & Outstanding Payments */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <IncomeByPropertyCard properties={incomeByPropertyData} />

            {/* Outstanding Payments Card */}
            <div className="bg-white rounded-lg shadow-sm p-6 h-full">
              <div className="flex items-center mb-4">
                <h2 className="text-lg font-medium text-gray-800">
                  Outstanding Payments
                </h2>
                {overduePayments.length > 0 && (
                  <span className="ml-2 bg-red-100 text-red-800 text-xs font-medium px-2 py-0.5 rounded-full">
                    {overduePayments.length}
                  </span>
                )}
              </div>

              {overduePayments.length > 0 ? (
                <div>
                  <div className="border-b border-gray-200 mb-2">
                    <div className="grid grid-cols-2 text-sm">
                      <div className="py-3 text-gray-500 font-medium uppercase tracking-wider">
                        Tenant
                      </div>
                      <div className="py-3 text-gray-500 font-medium uppercase tracking-wider text-right">
                        Amount Due
                      </div>
                    </div>
                  </div>
                  <div className="space-y-1">
                    {overduePayments.map((payment) => (
                      <div
                        key={payment.lease_id}
                        className="grid grid-cols-2 py-4 border-b border-gray-100 hover:bg-gray-50"
                      >
                        <div className="text-sm font-medium text-gray-900">
                          {payment.tenant_name}
                        </div>
                        <div className="text-sm font-medium text-gray-900 text-right">
                          ${payment.remaining_due.toFixed(2)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-40">
                  <div className="text-center text-gray-500">
                    <div className="text-3xl font-bold text-green-600">0</div>
                    <p className="text-sm mt-2">All payments are up to date</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === "payments" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="bg-white p-4 rounded-lg shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
            <div className="flex flex-col sm:flex-row sm:space-x-4 space-y-2 sm:space-y-0">
              <div>
                <label
                  htmlFor="payment-status"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Status
                </label>
                <select
                  id="payment-status"
                  className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={paymentFilters.status}
                  onChange={(e) =>
                    setPaymentFilters({
                      ...paymentFilters,
                      status: e.target.value,
                    })
                  }
                >
                  <option value="all">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="paid">Paid</option>
                  <option value="partial">Partial</option>
                  <option value="overdue">Overdue</option>
                  <option value="cancelled">Cancelled</option>
                  <option value="refunded">Refunded</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="payment-date-range"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Date Range
                </label>
                <select
                  id="payment-date-range"
                  className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={paymentFilters.dateRange}
                  onChange={(e) =>
                    setPaymentFilters({
                      ...paymentFilters,
                      dateRange: e.target.value,
                    })
                  }
                >
                  <option value="all_time">All Time</option>
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
                  placeholder="Search payments..."
                  className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 pr-3 py-2 border-gray-300 rounded-md text-sm"
                />
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fas fa-search text-gray-400"></i>
                </div>
              </div>
            </div>
          </div>

          {/* Payments Table */}
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Tenant
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Amount
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Date
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Method
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Status
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {loading && activeTab === "payments" ? (
                    <tr>
                      <td
                        colSpan="6"
                        className="px-6 py-12 text-center text-sm text-gray-500"
                      >
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2" />
                        Loading payments...
                      </td>
                    </tr>
                  ) : payments.length > 0 ? (
                    payments.map((payment) => (
                      <tr key={payment.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600">
                              {/* Display tenant initials */}
                              {payment.tenant_name
                                ? payment.tenant_name
                                    .split(" ")
                                    .map((name) => name[0])
                                    .join("")
                                    .toUpperCase()
                                    .substring(0, 2)
                                : "TS"}
                            </div>
                            <div className="ml-3">
                              <div className="text-sm font-medium text-gray-900">
                                {payment.tenant_name ||
                                  `Tenant #${payment.tenant_id}`}
                              </div>
                              <div className="text-sm text-gray-500">
                                {payment.property_name ||
                                  `Lease #${payment.lease_id}`}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            ${payment.amount.toFixed(2)}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {new Date(
                              payment.payment_date
                            ).toLocaleDateString()}
                          </div>
                          <div className="text-xs text-gray-500">
                            {new Date(
                              payment.payment_date
                            ).toLocaleTimeString()}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {payment.payment_method}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex justify-center">
                            <span
                              className={`badge ${getStatusBadgeClass(
                                payment.status.toLowerCase()
                              )}`}
                            >
                              {payment.status.charAt(0).toUpperCase() +
                                payment.status.slice(1).toLowerCase()}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                          <div className="flex justify-center space-x-2">
                            {payment.receipt_url && (
                              <button
                                type="button"
                                onClick={() => {
                                  const descriptiveName = `Receipt for ${
                                    payment.tenant_name || "Unknown Tenant"
                                  } ${
                                    payment.property_name
                                      ? " - " + payment.property_name
                                      : ""
                                  }`;
                                  handlePreviewReceipt(
                                    payment.receipt_url,
                                    descriptiveName
                                  );
                                }}
                                className="text-blue-600 hover:text-blue-900 p-1"
                                title="View Receipt"
                              >
                                <i className="fas fa-eye" />
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => handleEditPayment(payment)}
                              className="text-indigo-600 hover:text-indigo-900"
                              title="Edit"
                            >
                              <i className="fas fa-edit" />
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeletePayment(payment.id)}
                              className="text-red-600 hover:text-red-900"
                              title="Delete"
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
                        colSpan="6"
                        className="px-6 py-4 text-center text-sm text-gray-500"
                      >
                        No payments found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === "invoices" && (
        <div className="text-center py-16 px-4">
          <div className="bg-white rounded-lg shadow-sm p-10 max-w-lg mx-auto">
            <div className="text-blue-600 text-6xl mb-6">
              <i className="fas fa-file-invoice-dollar"></i>
            </div>
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">
              Coming Soon
            </h2>
            <div className="text-gray-600">
              <p>
                We're working on building a powerful invoice management system
                to help you keep track of all your property-related billing.
              </p>
              <p className="mt-4">
                This feature will be available in the near future. Stay tuned!
              </p>
            </div>
          </div>
        </div>
      )}

      {activeTab === "expenses" && (
        <div className="space-y-4">
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
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Property
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Category
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Amount
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Date
                    </th>
                    <th
                      scope="col"
                      className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {loading && activeTab === "expenses" ? (
                    <tr>
                      <td
                        colSpan="5"
                        className="px-6 py-12 text-center text-sm text-gray-500"
                      >
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2" />
                        Loading expenses...
                      </td>
                    </tr>
                  ) : expenses.length > 0 ? (
                    expenses.map((expense) => (
                      <tr key={expense.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {expense.property_name ||
                            `Property #${expense.property_id}` ||
                            "Unknown Property"}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {expense.category.charAt(0).toUpperCase() +
                            expense.category.slice(1)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          ${expense.total_amount.toFixed(2)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(expense.expense_date).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
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
                        colSpan="5"
                        className="px-6 py-4 text-center text-sm text-gray-500"
                      >
                        No expenses found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === "rent-tracker" && (
        <RentTracker
          onDataLoaded={(data) => {
            // Update the rent tracker metrics when data is loaded from the RentTracker component
            const totalRent = data.length;
            const paidRent = data.filter(
              (rent) => rent.status === "PAID"
            ).length;

            setAccountingData((prevData) => ({
              ...prevData,
              snapshot: {
                ...prevData.snapshot,
                paidRent,
                totalRent,
              },
            }));
          }}
        />
      )}

      {showNewPaymentModal && (
        <NewPaymentModal
          isOpen={showNewPaymentModal}
          onClose={handleCloseModal}
          onSuccess={() => {
            setShowNewPaymentModal(false);
            loadOverviewData();
            loadPaymentsData(true);
            toast.success("Payment created successfully");
          }}
        />
      )}

      {showEditPaymentModal && selectedItem && (
        <EditPaymentModal
          isOpen={showEditPaymentModal}
          onClose={() => {
            setShowEditPaymentModal(false);
            setSelectedItem(null);
          }}
          onSuccess={() => {
            setShowEditPaymentModal(false);
            setSelectedItem(null);
            loadPaymentsData(true);
            toast.success("Payment updated successfully");
          }}
          paymentData={selectedItem}
        />
      )}

      {showNewExpenseModal && (
        <NewExpenseModal
          isOpen={showNewExpenseModal}
          onClose={handleCloseModal}
          onSuccess={() => {
            setShowNewExpenseModal(false);
            loadOverviewData();
            loadExpensesData();
            toast.success("Expense created successfully");
          }}
        />
      )}

      {showFilePreviewModal && fileToPreviewUrl && (
        <FilePreviewModal
          isOpen={showFilePreviewModal}
          onClose={() => {
            setShowFilePreviewModal(false);
            setFileToPreviewUrl(null);
            setFilePreviewName("File Preview");
          }}
          fileUrl={fileToPreviewUrl}
          fileName={filePreviewName}
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

export default Accounting;
