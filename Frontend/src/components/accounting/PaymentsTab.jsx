import React, { useState, useEffect, useRef, useMemo } from "react";
import { toast } from "react-toastify";
import { CSVLink } from "react-csv";
import NewPaymentModal from "../accounting/modals/NewPaymentModal";
import EditPaymentModal from "../accounting/modals/EditPaymentModal";
import CSVImportModal from "./modals/CSVImportModal";
import { PaymentsTableSkeleton } from "../ui/skeletons";
import { useAccounting } from "./AccountingContext";
import { usePayments, useDeletePayment } from "../../hooks/useAccountingQueries";
import { importPaymentsFromCSV } from "../../utils/api/accounting";

const paymentTableColumns = [
  { key: "tenant", label: "Tenant", align: "left" },
  { key: "amount", label: "Amount", align: "center" },
  { key: "date", label: "Date", align: "center" },
  { key: "method", label: "Method", align: "center" },
  { key: "status", label: "Status", align: "center" },
  { key: "source", label: "Source", align: "center" },
  { key: "actions", label: "Actions", align: "center" },
];



const PaymentsTab = () => {
  const { handlePreviewReceipt } = useAccounting();

  // Local state for payments tab
  const [paymentsPagination, setPaymentsPagination] = useState({
    currentPage: 0,
    limit: 15,
    hasMore: true,
  });
  
  const [paymentFilters, setPaymentFilters] = useState({
    status: "all",
    dateRange: "all_time",
    search: "",
  });

  // Build query parameters
  const queryParams = useMemo(() => {
    const params = {};
    
    if (paymentFilters.status !== "all") {
      params.payment_status =
        paymentFilters.status.charAt(0).toUpperCase() +
        paymentFilters.status.slice(1);
    }

    if (paymentFilters.search && paymentFilters.search.trim()) {
      params.search = paymentFilters.search.trim();
    }

    params.limit = paymentsPagination.limit;
    params.offset = paymentsPagination.currentPage * paymentsPagination.limit;

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
    }

    return params;
  }, [paymentFilters, paymentsPagination.currentPage, paymentsPagination.limit]);

  // TanStack Query hooks
  const { data: paymentsData, isLoading: loading, error, refetch } = usePayments(queryParams);
  const deletePaymentMutation = useDeletePayment();

  // Extract payments and pagination info
  const payments = paymentsData?.items || [];

  // Modal states
  const [showNewPaymentModal, setShowNewPaymentModal] = useState(false);
  const [showEditPaymentModal, setShowEditPaymentModal] = useState(false);
  const [showCSVImportModal, setShowCSVImportModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);

  // Effect for handling filter changes - reset to first page
  useEffect(() => {
    setPaymentsPagination((prev) => ({ ...prev, currentPage: 0 }));
  }, [paymentFilters]);

  // Update pagination state when query data changes
  useEffect(() => {
    if (paymentsData) {
      setPaymentsPagination((prev) => ({ ...prev, hasMore: paymentsData.has_more || false }));
    }
  }, [paymentsData]);

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

  const handleEditPayment = (payment) => {
    console.log("Edit payment clicked:", payment);
    setSelectedItem(payment);
    setShowEditPaymentModal(true);
  };

  const handleDeletePayment = async (paymentId) => {
    console.log("Delete payment clicked, ID:", paymentId);
    if (
      window.confirm(
        "Are you sure you want to delete this payment? This action cannot be undone."
      )
    ) {
      try {
        await deletePaymentMutation.mutateAsync(paymentId);
        toast.success("Payment deleted successfully.");
      } catch (err) {
        console.error("Failed to delete payment:", err);
        toast.error(err.message || "Failed to delete payment.");
      }
    }
  };

  const handleNextPage = () => {
    setPaymentsPagination((prev) => ({
      ...prev,
      currentPage: prev.currentPage + 1,
    }));
  };

  const handlePreviousPage = () => {
    setPaymentsPagination((prev) => ({
      ...prev,
      currentPage: Math.max(0, prev.currentPage - 1),
    }));
  };

  const handleShowModal = () => {
    setShowNewPaymentModal(true);
  };

  const handleCloseModal = () => {
    setShowNewPaymentModal(false);
    setShowEditPaymentModal(false);
    setSelectedItem(null);
  };

  const handleCSVImportSuccess = () => {
    // Refresh the payments data after successful import
    refetch();
    setShowCSVImportModal(false);
  };

  // CSV Export configuration
  const csvHeaders = [
    { label: 'Tenant', key: 'tenant_name' },
    { label: 'Property', key: 'property_name' },
    { label: 'Amount', key: 'amount' },
    { label: 'Payment Date', key: 'payment_date' },
    { label: 'Payment Method', key: 'payment_method' },
    { label: 'Status', key: 'status' },
    { label: 'Transaction Reference', key: 'transaction_reference' },
    { label: 'Description', key: 'description' },
    { label: 'Source', key: 'source' },
  ];

  // Format data for CSV export with clean headers
  const getFilterDescription = () => {
    const filters = [];
    if (paymentFilters.status !== 'all') filters.push(`Status: ${paymentFilters.status}`);
    if (paymentFilters.dateRange !== 'all_time') filters.push(`Date Range: ${paymentFilters.dateRange.replace('_', ' ')}`);
    if (paymentFilters.search) filters.push(`Search: "${paymentFilters.search}"`);
    return filters.length > 0 ? filters.join(', ') : 'No filters applied';
  };

  const csvData = [
    // Clean header with metadata in a single row
    { 
      tenant_name: 'Brikli Payments Report', 
      property_name: `Exported: ${new Date().toLocaleDateString()}`,
      amount: `Filters: ${getFilterDescription()}`,
      payment_date: `Records: ${payments.length}`,
      payment_method: '', 
      status: '', 
      transaction_reference: '', 
      description: '', 
      source: '' 
    },
    // Empty separator row
    { tenant_name: '', property_name: '', amount: '', payment_date: '', payment_method: '', status: '', transaction_reference: '', description: '', source: '' },
    // Actual data
    ...payments.map(payment => {
      const amt = Number(payment?.amount ?? 0);
      const paymentDate = payment?.payment_date ? new Date(payment.payment_date) : null;
      return {
        tenant_name: payment?.tenant_name || 'N/A',
        property_name: payment?.property_name || 'N/A',
        amount: Number.isFinite(amt) ? amt.toFixed(2) : '0.00',
        payment_date: paymentDate && !isNaN(paymentDate) ? paymentDate.toLocaleDateString() : 'N/A',
        payment_method: payment?.payment_method || 'N/A',
        status: payment?.status || 'N/A',
        transaction_reference: payment?.transaction_reference || 'N/A',
        description: payment?.description || 'N/A',
        source: payment?.quickbooks_id ? 'QuickBooks' : 'Brikli',
      };
    })
  ];

  // Generate professional filename with current date and filters
  const generateFilename = () => {
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0];
    const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '');
    const filterSuffix = paymentFilters.status !== 'all' ? `-${paymentFilters.status}` : '';
    const searchSuffix = paymentFilters.search ? `-search` : '';
    return `Brikli-Payments-Report${filterSuffix}${searchSuffix}-${dateStr}-${timeStr}.csv`;
  };

  // CSV Import configuration
  const csvImportConfig = {
    title: "Import Payments",
    description: "Upload your payment data",
    apiFunction: importPaymentsFromCSV,
    expectedHeaders: [
      { key: "amount", label: "Amount", required: true, type: "number", aliases: ["amount", "payment_amount", "total"] },
      { key: "payment_date", label: "Payment Date", required: true, type: "date", aliases: ["date", "payment_date", "received_date"] },
      { key: "tenant_name", label: "Tenant Name", required: false, aliases: ["tenant", "tenant_name", "payer"] },
      { key: "property_name", label: "Property Name", required: false, aliases: ["property", "property_name", "address"] },
      { key: "payment_method", label: "Payment Method", required: false, aliases: ["method", "payment_method", "payment_type"] },
      { key: "status", label: "Status", required: false, aliases: ["status", "payment_status", "state"] },
      { key: "transaction_reference", label: "Transaction Reference", required: false, aliases: ["reference", "transaction_reference", "confirmation"] },
      { key: "description", label: "Description", required: false, aliases: ["description", "notes", "memo"] },
      { key: "reduction_amount", label: "Reduction Amount", required: false, type: "number", aliases: ["reduction", "reduction_amount", "discount"] },
      { key: "reduction_reason", label: "Reduction Reason", required: false, aliases: ["reduction_reason", "discount_reason", "adjustment_reason"] }
    ],
    sampleData: [
      {
        amount: 1500.00,
        payment_date: "2024-01-15",
        tenant_name: "John Smith",
        property_name: "123 Main St",
        payment_method: "Bank Transfer",
        status: "Paid",
        transaction_reference: "TXN123456",
        description: "Monthly rent payment"
      },
      {
        amount: 1200.00,
        payment_date: "2024-01-20",
        tenant_name: "Jane Doe",
        property_name: "456 Oak Ave",
        payment_method: "Credit Card",
        status: "Pending",
        description: "Rent payment"
      }
    ],
    validationTips: [
      "Amount is required and should be a positive number without currency symbols",
      "Payment date is required in YYYY-MM-DD format or MM/DD/YYYY",
      "Either tenant name or property name should be provided for proper matching",
      "Payment methods: Credit Card, Debit Card, Bank Transfer, Cash, Check, PayPal, Other",
      "Status options: Pending, Paid, Partial, Overdue, Cancelled, Refunded, Draft, Void",
      "Tenant and property names should match exactly as they appear in your system"
    ]
  };

  if (loading) {
    return <PaymentsTableSkeleton rowCount={8} />;
  }

  return (
    <div>
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
          <button
            onClick={refetch}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}



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
              <option value="week">Last 7 Days</option>
              <option value="month">Last 30 Days</option>
              <option value="quarter">Last 3 Months</option>
              <option value="year">Last 12 Months</option>
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="relative rounded-md shadow-sm">
            <input
              type="search"
              placeholder="Search payments..."
              value={paymentFilters.search}
              onChange={(e) =>
                setPaymentFilters({
                  ...paymentFilters,
                  search: e.target.value,
                })
              }
              className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 pr-3 py-2 border-gray-300 rounded-md text-sm"
            />
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <i className="fas fa-search text-gray-400"></i>
            </div>
          </div>
          
          {/* Import CSV Button */}
          <button
            onClick={() => setShowCSVImportModal(true)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-upload mr-2"></i>
            Import CSV
          </button>

          {/* Export CSV Button */}
          <CSVLink
            data={csvData}
            headers={csvHeaders}
            filename={generateFilename()}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-download mr-2"></i>
            Export CSV
          </CSVLink>
          
          {/* New Payment Button */}
          <button
            onClick={handleShowModal}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-plus mr-2"></i>
            New Payment
          </button>
        </div>
      </div>

      {/* Payments Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {paymentTableColumns.map((col) => (
                  <th
                    key={col.key}
                    scope="col"
                    className={`px-6 py-3 ${
                      col.align === "center" ? "text-center" : "text-left"
                    } text-xs font-medium text-gray-500 uppercase tracking-wider`}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {payments.length > 0 ? (
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
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="text-sm text-gray-900">
                        ${Number.parseFloat(payment.amount).toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
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
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
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
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                      {payment.quickbooks_id != null
                        ? "QuickBooks"
                        : "Brikli"}
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
                    colSpan={paymentTableColumns.length}
                    className="px-6 py-4 text-center text-sm text-gray-500"
                  >
                    No payments found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {/* Pagination Controls */}
        <div className="flex justify-between items-center mt-4 p-4">
          <button
            type="button"
            onClick={handlePreviousPage}
            disabled={paymentsPagination.currentPage === 0 || loading}
            className="btn btn-secondary disabled:opacity-50"
            aria-label="Go to previous page"
          >
            <i className="fas fa-arrow-left mr-2" aria-hidden="true" />
            Previous
          </button>
          <span className="text-sm text-gray-700">
            Page {paymentsPagination.currentPage + 1}
          </span>
          <button
            type="button"
            onClick={handleNextPage}
            disabled={!paymentsPagination.hasMore || loading}
            className="btn btn-secondary disabled:opacity-50"
            aria-label="Go to next page"
          >
            Next
            <i className="fas fa-arrow-right ml-2" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Modals */}
      {showNewPaymentModal && (
        <NewPaymentModal
          isOpen={showNewPaymentModal}
          onClose={handleCloseModal}
          onSuccess={() => {
            setShowNewPaymentModal(false);
            refetch();
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
            refetch();
            toast.success("Payment updated successfully");
          }}
          paymentData={selectedItem}
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

export default PaymentsTab;