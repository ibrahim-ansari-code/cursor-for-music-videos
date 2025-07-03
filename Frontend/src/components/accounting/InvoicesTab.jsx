import React, { useState, useEffect, useMemo, useCallback } from "react";
import { 
  fetchInvoices, 
  fetchProperties, 
  fetchTenants,
  deleteInvoice,
  markInvoicePaid
} from "../../utils/api";
import { toast } from "react-toastify";
import NewInvoiceModal from "../NewInvoiceModal";
import EditInvoiceModal from "../EditInvoiceModal";
import LoadingSpinner from "../LoadingSpinner";
import { useAccounting } from "./AccountingContext";
import { INVOICE_STATUSES } from "../../utils/constants";

const invoiceTableColumns = [
  { key: "invoice_number", label: "Invoice #", align: "left" },
  { key: "property_tenant", label: "Property/Tenant", align: "left" },
  { key: "amount", label: "Amount", align: "center" },
  { key: "issue_date", label: "Issue Date", align: "center" },
  { key: "due_date", label: "Due Date", align: "center" },
  { key: "status", label: "Status", align: "center" },
  { key: "source", label: "Source", align: "center" },
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

const InvoicesTab = () => {
  const {
    loading,
    setLoading,
    error,
    setError,
  } = useAccounting();

  // Local state for invoices tab
  const [invoices, setInvoices] = useState([]);
  const [properties, setProperties] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [invoiceFilters, setInvoiceFilters] = useState({
    status: "all",
    dateRange: "all_time",
    property_id: "all",
    tenant_id: "all",
    search: "",
  });
  const [invoicesPagination, setInvoicesPagination] = useState({
    currentPage: 0,
    limit: 15,
    hasMore: true,
  });

  // Modal states
  const [showNewInvoiceModal, setShowNewInvoiceModal] = useState(false);
  const [showEditInvoiceModal, setShowEditInvoiceModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);

  const loadInvoicesData = useCallback(async () => {
    try {
      setLoading(true);

      const params = {};
      
      if (invoiceFilters.status !== "all") {
        params.status = invoiceFilters.status;
      }

      if (invoiceFilters.property_id !== "all") {
        params.property_id = invoiceFilters.property_id;
      }

      if (invoiceFilters.tenant_id !== "all") {
        params.tenant_id = invoiceFilters.tenant_id;
      }

      if (invoiceFilters.search) {
        params.search = invoiceFilters.search;
      }

      // Add pagination params
      params.limit = invoicesPagination.limit;
      params.offset = invoicesPagination.currentPage * invoicesPagination.limit;

      // Convert date range to actual date params based on issue_date
      const today = new Date();
      if (invoiceFilters.dateRange === "week") {
        const weekAgo = new Date();
        weekAgo.setDate(today.getDate() - 7);
        params.start_date = weekAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      } else if (invoiceFilters.dateRange === "month") {
        const monthAgo = new Date();
        monthAgo.setMonth(today.getMonth() - 1);
        params.start_date = monthAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      } else if (invoiceFilters.dateRange === "quarter") {
        const quarterAgo = new Date();
        quarterAgo.setMonth(today.getMonth() - 3);
        params.start_date = quarterAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      } else if (invoiceFilters.dateRange === "year") {
        const yearAgo = new Date();
        yearAgo.setFullYear(today.getFullYear() - 1);
        params.start_date = yearAgo.toISOString().split("T")[0];
        params.end_date = today.toISOString().split("T")[0];
      }

      const data = await fetchInvoices(params);
      
      // Handle pagination response structure
      if (data && Array.isArray(data)) {
        setInvoices(data);
        setInvoicesPagination((prev) => ({ ...prev, hasMore: data.length === prev.limit }));
      } else if (data && data.items) {
        setInvoices(data.items);
        setInvoicesPagination((prev) => ({ ...prev, hasMore: data.has_more }));
      } else {
        setInvoices([]);
        setInvoicesPagination((prev) => ({ ...prev, hasMore: false }));
      }
      
      setError(null);
    } catch (err) {
      setError("Failed to load invoices data. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [invoiceFilters, invoicesPagination.currentPage, invoicesPagination.limit, setLoading, setError]);

  const loadProperties = useCallback(async () => {
    try {
      const data = await fetchProperties();
      setProperties(data || []);
    } catch (err) {
      setProperties([]);
    }
  }, []);

  const loadTenants = useCallback(async () => {
    try {
      const data = await fetchTenants();
      setTenants(data || []);
    } catch (err) {
      setTenants([]);
    }
  }, []);

  // Load initial data and properties/tenants
  useEffect(() => {
    loadInvoicesData();
    loadProperties();
    loadTenants();
  }, [loadInvoicesData, loadProperties, loadTenants]);

  // Reset pagination when filters change
  useEffect(() => {
    setInvoicesPagination((prev) => ({ ...prev, currentPage: 0 }));
  }, [invoiceFilters]);

  const getStatusBadgeClass = (status) => {
    switch (status?.toLowerCase()) {
      case "paid":
        return "badge-success";
      case "pending":
        return "badge-warning";
      case "overdue":
        return "badge-danger";
      case "partial":
        return "badge-warning";
      case "cancelled":
      case "void":
        return "badge-secondary";
      case "draft":
        return "badge-info";
      default:
        return "badge-info";
    }
  };

  const getDueDateClass = (dueDate, status) => {
    if (status?.toLowerCase() === "paid") {
      return "text-gray-500";
    }
    
    const due = new Date(dueDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    due.setHours(0, 0, 0, 0);
    
    if (due < today) {
      return "text-red-600 font-medium"; // Overdue
    } else if (due.getTime() === today.getTime()) {
      return "text-yellow-600 font-medium"; // Due today
    } else {
      const daysDiff = Math.ceil((due - today) / (1000 * 60 * 60 * 24));
      if (daysDiff <= 3) {
        return "text-orange-600 font-medium"; // Due soon
      }
      return "text-gray-500"; // Normal
    }
  };

  const handleEditInvoice = (invoice) => {
    setSelectedItem(invoice);
    setShowEditInvoiceModal(true);
  };

  const handleDeleteInvoice = async (invoiceId) => {
    const invoiceToDelete = invoices.find((inv) => inv.id === invoiceId);
    const invoiceDescription = invoiceToDelete
      ? `Invoice #${invoiceToDelete.invoice_number}`
      : `Invoice ID ${invoiceId}`;

    if (
      window.confirm(
        `Are you sure you want to delete ${invoiceDescription}? This action cannot be undone.`
      )
    ) {
      try {
        await deleteInvoice(invoiceId);
        toast.success(`${invoiceDescription} deleted successfully.`);
        loadInvoicesData();
      } catch (err) {
        toast.error(err.message || "Failed to delete invoice.");
      }
    }
  };

  const handleMarkPaid = async (invoiceId) => {
    const invoiceToUpdate = invoices.find((inv) => inv.id === invoiceId);
    const invoiceDescription = invoiceToUpdate
      ? `Invoice #${invoiceToUpdate.invoice_number}`
      : `Invoice ID ${invoiceId}`;

    if (
      window.confirm(
        `Mark ${invoiceDescription} as paid?`
      )
    ) {
      try {
        await markInvoicePaid(invoiceId);
        toast.success(`${invoiceDescription} marked as paid.`);
        loadInvoicesData();
      } catch (err) {
        toast.error(err.message || "Failed to mark invoice as paid.");
      }
    }
  };

  const handleNextPage = () => {
    setInvoicesPagination((prev) => ({
      ...prev,
      currentPage: prev.currentPage + 1,
    }));
  };

  const handlePreviousPage = () => {
    setInvoicesPagination((prev) => ({
      ...prev,
      currentPage: Math.max(0, prev.currentPage - 1),
    }));
  };

  const handleShowModal = () => {
    setShowNewInvoiceModal(true);
  };

  const handleCloseModal = () => {
    setShowNewInvoiceModal(false);
    setShowEditInvoiceModal(false);
    setSelectedItem(null);
  };

  const filteredTenants = useMemo(() => {
    return tenants.filter(tenant => {
      if (invoiceFilters.property_id === "all") return true;
      return tenant.property_units?.some(unit => 
        unit.property_id === parseInt(invoiceFilters.property_id)
      );
    });
  }, [tenants, invoiceFilters.property_id]);

  return (
    <div>
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
          <button
            onClick={loadInvoicesData}
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
          New Invoice
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
      <div className="bg-white p-4 rounded-lg shadow-sm">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          {/* Status Filter */}
          <div>
            <label
              htmlFor="invoice-status"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Status
            </label>
            <select
              id="invoice-status"
              className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={invoiceFilters.status}
              onChange={(e) =>
                setInvoiceFilters({
                  ...invoiceFilters,
                  status: e.target.value,
                })
              }
            >
              <option value="all">All Statuses</option>
              {INVOICE_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>

          {/* Date Range Filter */}
          <div>
            <label
              htmlFor="invoice-date-range"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Date Range
            </label>
            <select
              id="invoice-date-range"
              className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={invoiceFilters.dateRange}
              onChange={(e) =>
                setInvoiceFilters({
                  ...invoiceFilters,
                  dateRange: e.target.value,
                })
              }
            >
              <option value="all_time">All time</option>
              <option value="week">Last 7 days</option>
              <option value="month">Last 30 days</option>
              <option value="quarter">Last 90 days</option>
              <option value="year">Last year</option>
            </select>
          </div>

          {/* Property Filter */}
          <div>
            <label
              htmlFor="invoice-property"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Property
            </label>
            <select
              id="invoice-property"
              className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={invoiceFilters.property_id}
              onChange={(e) =>
                setInvoiceFilters({
                  ...invoiceFilters,
                  property_id: e.target.value,
                  tenant_id: "all", // Reset tenant filter when property changes
                })
              }
            >
              <option value="all">All Properties</option>
              {properties.map((property) => (
                <option key={property.id} value={property.id}>
                  {property.name}
                </option>
              ))}
            </select>
          </div>

          {/* Tenant Filter */}
          <div>
            <label
              htmlFor="invoice-tenant"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Tenant
            </label>
            <select
              id="invoice-tenant"
              className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={invoiceFilters.tenant_id}
              onChange={(e) =>
                setInvoiceFilters({
                  ...invoiceFilters,
                  tenant_id: e.target.value,
                })
              }
            >
              <option value="all">All Tenants</option>
              {filteredTenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.full_name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex items-center">
          <div className="relative rounded-md shadow-sm flex-1 max-w-md">
            <input
              type="search"
              placeholder="Search invoices..."
              className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 pr-3 py-2 border-gray-300 rounded-md text-sm"
              value={invoiceFilters.search}
              onChange={(e) =>
                setInvoiceFilters({
                  ...invoiceFilters,
                  search: e.target.value,
                })
              }
            />
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <i className="fas fa-search text-gray-400"></i>
            </div>
          </div>
        </div>
      </div>

      {/* Invoices Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {invoiceTableColumns.map((col) => (
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
              {loading ? (
                <LoadingRow colSpan={invoiceTableColumns.length} loadingText="Loading invoices..." />
              ) : invoices.length > 0 ? (
                invoices.map((invoice) => (
                  <tr key={invoice.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-blue-600 hover:text-blue-900 cursor-pointer">
                        #{invoice.invoice_number}
                      </div>
                      {invoice.description && (
                        <div className="text-xs text-gray-500 mt-1 truncate max-w-32">
                          {invoice.description}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm">
                        {invoice.property && (
                          <div className="font-medium text-gray-900">
                            {invoice.property.name}
                          </div>
                        )}
                        {invoice.tenant && (
                          <div className="text-gray-500 text-xs">
                            {invoice.tenant.full_name}
                          </div>
                        )}
                        {!invoice.property && !invoice.tenant && (
                          <div className="text-gray-400 text-sm italic">
                            No property/tenant assigned
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="text-sm font-medium text-gray-900">
                        ${parseFloat(invoice.amount).toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="text-sm text-gray-500">
                        {new Date(invoice.issue_date).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className={`text-sm ${getDueDateClass(invoice.due_date, invoice.status)}`}>
                        {new Date(invoice.due_date).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex justify-center">
                        <span
                          className={`badge ${getStatusBadgeClass(invoice.status)}`}
                        >
                          {invoice.status.charAt(0).toUpperCase() +
                            invoice.status.slice(1).toLowerCase()}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">
                      {invoice.quickbooks_id != null ? "QuickBooks" : "Brikli"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                      <div className="flex justify-center space-x-2">
                        {invoice.status?.toLowerCase() !== "paid" && (
                          <button
                            type="button"
                            onClick={() => handleMarkPaid(invoice.id)}
                            className="text-green-600 hover:text-green-900 p-1"
                            title="Mark as Paid"
                          >
                            <i className="fas fa-check-circle" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleEditInvoice(invoice)}
                          className="text-indigo-600 hover:text-indigo-900 p-1"
                          title="Edit Invoice"
                        >
                          <i className="fas fa-edit" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteInvoice(invoice.id)}
                          className="text-red-600 hover:text-red-900 p-1"
                          title="Delete Invoice"
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
                    colSpan={invoiceTableColumns.length}
                    className="px-6 py-12 text-center text-sm text-gray-500"
                  >
                    <div className="flex flex-col items-center">
                      <i className="fas fa-file-invoice-dollar text-gray-300 text-4xl mb-4"></i>
                      <p className="text-lg font-medium text-gray-900 mb-2">No invoices found</p>
                      <p className="text-gray-500 mb-4">Get started by creating your first invoice.</p>
                      <button
                        onClick={handleShowModal}
                        className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                      >
                        <i className="fas fa-plus mr-2"></i>
                        Create Invoice
                      </button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination Controls */}
        {invoices.length > 0 && (
          <div className="flex justify-between items-center mt-4 p-4">
            <button
              type="button"
              onClick={handlePreviousPage}
              disabled={invoicesPagination.currentPage === 0 || loading}
              className="btn btn-secondary disabled:opacity-50"
              aria-label="Go to previous page"
            >
              <i className="fas fa-arrow-left mr-2" aria-hidden="true" />
              Previous
            </button>
            <span className="text-sm text-gray-700">
              Page {invoicesPagination.currentPage + 1}
            </span>
            <button
              type="button"
              onClick={handleNextPage}
              disabled={!invoicesPagination.hasMore || loading}
              className="btn btn-secondary disabled:opacity-50"
              aria-label="Go to next page"
            >
              Next
              <i className="fas fa-arrow-right ml-2" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>

      {/* Modals */}
      {showNewInvoiceModal && (
        <NewInvoiceModal
          isOpen={showNewInvoiceModal}
          onClose={handleCloseModal}
          onSuccess={() => {
            setShowNewInvoiceModal(false);
            loadInvoicesData();
            toast.success("Invoice created successfully");
          }}
        />
      )}

      {showEditInvoiceModal && selectedItem && (
        <EditInvoiceModal
          isOpen={showEditInvoiceModal}
          onClose={() => {
            setShowEditInvoiceModal(false);
            setSelectedItem(null);
          }}
          onSuccess={() => {
            setShowEditInvoiceModal(false);
            setSelectedItem(null);
            loadInvoicesData();
            toast.success("Invoice updated successfully");
          }}
          invoiceData={selectedItem}
        />
      )}
    </div>
  );
};

export default InvoicesTab;