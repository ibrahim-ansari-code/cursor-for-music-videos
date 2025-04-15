import React, { useState, useEffect } from 'react';
import { 
  fetchPayments, 
  fetchInvoices, 
  fetchExpenses, 
  getAccountingOverview,
  createPayment,
  createInvoice,
  createExpense 
} from '../utils/api';
import { toast } from 'react-toastify';
import NewPaymentModal from '../components/NewPaymentModal';

const Accounting = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Data states
  const [payments, setPayments] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [overviewData, setOverviewData] = useState(null);
  
  // Modal states
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState(null); // 'payment', 'invoice', 'expense'
  const [showNewPaymentModal, setShowNewPaymentModal] = useState(false);
  
  // Filter states
  const [paymentFilters, setPaymentFilters] = useState({
    status: 'all',
    dateRange: 'month'
  });
  
  const [invoiceFilters, setInvoiceFilters] = useState({
    status: 'all',
    dateRange: 'month'
  });
  
  const [expenseFilters, setExpenseFilters] = useState({
    category: 'all',
    dateRange: 'month'
  });

  useEffect(() => {
    if (activeTab === 'overview') {
      loadOverviewData();
    } else if (activeTab === 'payments') {
      loadPaymentsData();
    } else if (activeTab === 'invoices') {
      loadInvoicesData();
    } else if (activeTab === 'expenses') {
      loadExpensesData();
    }
  }, [activeTab, paymentFilters, invoiceFilters, expenseFilters]);

  const loadOverviewData = async () => {
    try {
      setLoading(true);
      const data = await getAccountingOverview();
      setOverviewData(data);
      setError(null);
    } catch (err) {
      console.error('Error loading overview data:', err);
      setError('Failed to load accounting overview. Please try again.');
      toast.error('Failed to load accounting overview');
    } finally {
      setLoading(false);
    }
  };

  const loadPaymentsData = async () => {
    try {
      setLoading(true);
      
      const params = {};
      if (paymentFilters.status !== 'all') {
        params.status = paymentFilters.status;
      }
      
      // Convert date range to actual date params
      if (paymentFilters.dateRange === 'week') {
        const today = new Date();
        const weekAgo = new Date();
        weekAgo.setDate(today.getDate() - 7);
        params.start_date = weekAgo.toISOString().split('T')[0];
        params.end_date = today.toISOString().split('T')[0];
      } else if (paymentFilters.dateRange === 'month') {
        const today = new Date();
        const monthAgo = new Date();
        monthAgo.setMonth(today.getMonth() - 1);
        params.start_date = monthAgo.toISOString().split('T')[0];
        params.end_date = today.toISOString().split('T')[0];
      }
      
      const data = await fetchPayments(params);
      setPayments(data);
      setError(null);
    } catch (err) {
      console.error('Error loading payments data:', err);
      setError('Failed to load payments data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadInvoicesData = async () => {
    try {
      setLoading(true);
      
      const params = {};
      if (invoiceFilters.status !== 'all') {
        params.status = invoiceFilters.status;
      }
      
      // Convert date range to actual date params
      if (invoiceFilters.dateRange === 'week') {
        const today = new Date();
        const weekAgo = new Date();
        weekAgo.setDate(today.getDate() - 7);
        params.start_date = weekAgo.toISOString().split('T')[0];
        params.end_date = today.toISOString().split('T')[0];
      } else if (invoiceFilters.dateRange === 'month') {
        const today = new Date();
        const monthAgo = new Date();
        monthAgo.setMonth(today.getMonth() - 1);
        params.start_date = monthAgo.toISOString().split('T')[0];
        params.end_date = today.toISOString().split('T')[0];
      }
      
      const data = await fetchInvoices(params);
      setInvoices(data);
      setError(null);
    } catch (err) {
      console.error('Error loading invoices data:', err);
      setError('Failed to load invoices data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadExpensesData = async () => {
    try {
      setLoading(true);
      
      const params = {};
      if (expenseFilters.category !== 'all') {
        params.category = expenseFilters.category;
      }
      
      // Convert date range to actual date params
      if (expenseFilters.dateRange === 'week') {
        const today = new Date();
        const weekAgo = new Date();
        weekAgo.setDate(today.getDate() - 7);
        params.start_date = weekAgo.toISOString().split('T')[0];
        params.end_date = today.toISOString().split('T')[0];
      } else if (expenseFilters.dateRange === 'month') {
        const today = new Date();
        const monthAgo = new Date();
        monthAgo.setMonth(today.getMonth() - 1);
        params.start_date = monthAgo.toISOString().split('T')[0];
        params.end_date = today.toISOString().split('T')[0];
      }
      
      const data = await fetchExpenses(params);
      setExpenses(data);
      setError(null);
    } catch (err) {
      console.error('Error loading expenses data:', err);
      setError('Failed to load expenses data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleShowModal = (type) => {
    if (type === 'payment') {
      setShowNewPaymentModal(true);
    } else {
    setModalType(type);
    setShowModal(true);
    }
  };

  const handleCloseModal = () => {
    setShowNewPaymentModal(false);
    setShowModal(false);
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'paid':
        return 'badge-success';
      case 'pending':
      case 'partial':
        return 'badge-warning';
      case 'late':
      case 'overdue':
        return 'badge-danger';
      default:
        return 'badge-info';
    }
  };

  if (loading && activeTab === 'overview') {
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div className="mt-3 sm:mt-0 flex space-x-3">
          <button
            onClick={() => handleShowModal(activeTab === 'payments' ? 'payment' : activeTab === 'invoices' ? 'invoice' : 'expense')}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-plus mr-2"></i>
            {activeTab === 'payments' ? 'New Payment' : activeTab === 'invoices' ? 'New Invoice' : activeTab === 'expenses' ? 'New Expense' : 'Add New'}
          </button>
          
          <button
            onClick={() => {/* Export functionality would go here */}}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-file-export mr-2"></i>
            Export
          </button>
        </div>
      </div>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
          <button 
            onClick={() => {
              if (activeTab === 'overview') loadOverviewData();
              else if (activeTab === 'payments') loadPaymentsData();
              else if (activeTab === 'invoices') loadInvoicesData();
              else if (activeTab === 'expenses') loadExpensesData();
            }}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}
      
      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`${
              activeTab === 'overview'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('payments')}
            className={`${
              activeTab === 'payments'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Payments
          </button>
          <button
            onClick={() => setActiveTab('invoices')}
            className={`${
              activeTab === 'invoices'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Invoices
          </button>
          <button
            onClick={() => setActiveTab('expenses')}
            className={`${
              activeTab === 'expenses'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Expenses
          </button>
        </nav>
      </div>
      
      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Financial Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="dashboard-card">
              <h2 className="text-sm font-medium text-gray-500 mb-1">Total Revenue</h2>
              <div className="flex items-baseline">
                <p className="text-2xl font-semibold">
                  ${overviewData?.total_revenue?.toLocaleString() || '0'}
                </p>
              </div>
              <div className="text-xs text-gray-500 mt-1">Year to date</div>
            </div>
            
            <div className="dashboard-card">
              <h2 className="text-sm font-medium text-gray-500 mb-1">Total Expenses</h2>
              <div className="flex items-baseline">
                <p className="text-2xl font-semibold">
                  ${overviewData?.total_expenses?.toLocaleString() || '0'}
                </p>
              </div>
              <div className="text-xs text-gray-500 mt-1">Year to date</div>
            </div>
            
            <div className="dashboard-card">
              <h2 className="text-sm font-medium text-gray-500 mb-1">Net Income</h2>
              <div className="flex items-baseline">
                <p className="text-2xl font-semibold">
                  ${overviewData?.net_income?.toLocaleString() || '0'}
                </p>
              </div>
              <div className="text-xs text-gray-500 mt-1">Year to date</div>
            </div>
          </div>
          
          {/* Monthly Revenue Chart */}
          <div className="dashboard-card">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Monthly Revenue & Expenses</h2>
            
            <div className="h-80">
              {overviewData?.revenue_trends ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center text-gray-500">
                    {/* This is where the chart would go in a real implementation */}
                    <i className="fas fa-chart-bar text-6xl mb-2"></i>
                    <p>Monthly Revenue Trend Chart</p>
                    <p className="text-sm mt-2">
                      {overviewData.revenue_trends.map(month => 
                        `${month.period}: $${month.revenue.toLocaleString()}`
                      ).join(' · ')}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full">
                  <p className="text-gray-500">No revenue data available</p>
                </div>
              )}
            </div>
          </div>
          
          {/* Occupancy & Outstanding Payments */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="dashboard-card">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Occupancy Rate</h2>
              
              {overviewData?.occupancy_rate !== undefined ? (
                <div className="flex items-center justify-center h-40">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-blue-600">
                      {overviewData.occupancy_rate.toFixed(1)}%
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-40">
                  <p className="text-gray-500">No occupancy data available</p>
                </div>
              )}
            </div>
            
            <div className="dashboard-card">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Outstanding Payments</h2>
              
              {overviewData?.outstanding_payments !== undefined ? (
                <div className="flex items-center justify-center h-40">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-red-600">
                      {overviewData.outstanding_payments}
                      </div>
                    <p className="text-sm text-gray-500 mt-2">Payments pending</p>
                      </div>
                    </div>
              ) : (
                <div className="flex items-center justify-center h-40">
                  <p className="text-gray-500">No outstanding payments data available</p>
                    </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {activeTab === 'payments' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="bg-white p-4 rounded-lg shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
            <div className="flex flex-col sm:flex-row sm:space-x-4 space-y-2 sm:space-y-0">
              <div>
                <label htmlFor="payment-status" className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select
                  id="payment-status"
                  className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={paymentFilters.status}
                  onChange={(e) => setPaymentFilters({...paymentFilters, status: e.target.value})}
                >
                  <option value="all">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="paid">Paid</option>
                  <option value="late">Late</option>
                  <option value="partial">Partial</option>
                </select>
              </div>
              
              <div>
                <label htmlFor="payment-date-range" className="block text-sm font-medium text-gray-700 mb-1">Date Range</label>
                <select
                  id="payment-date-range"
                  className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={paymentFilters.dateRange}
                  onChange={(e) => setPaymentFilters({...paymentFilters, dateRange: e.target.value})}
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
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tenant
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Amount
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Method
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {payments.length > 0 ? (
                    payments.map((payment) => (
                      <tr key={payment.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600">
                              {/* Placeholder for tenant initials */}
                              TS
                            </div>
                            <div className="ml-3">
                              <div className="text-sm font-medium text-gray-900">
                                Tenant #{payment.tenant_id}
                              </div>
                              <div className="text-sm text-gray-500">
                                Lease #{payment.lease_id}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">${payment.amount.toFixed(2)}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {new Date(payment.payment_date).toLocaleDateString()}
                          </div>
                          <div className="text-xs text-gray-500">
                            {new Date(payment.payment_date).toLocaleTimeString()}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {payment.payment_method}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`badge ${getStatusBadgeClass(payment.status)}`}>
                            {payment.status.charAt(0).toUpperCase() + payment.status.slice(1)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex space-x-2">
                            <button
                              className="text-indigo-600 hover:text-indigo-900"
                              title="Edit"
                            >
                              <i className="fas fa-edit"></i>
                            </button>
                            <button
                              className="text-red-600 hover:text-red-900"
                              title="Delete"
                            >
                              <i className="fas fa-trash-alt"></i>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6" className="px-6 py-4 text-center text-sm text-gray-500">
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
      
      {activeTab === 'invoices' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="bg-white p-4 rounded-lg shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
            <div className="flex flex-col sm:flex-row sm:space-x-4 space-y-2 sm:space-y-0">
              <div>
                <label htmlFor="invoice-status" className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select
                  id="invoice-status"
                  className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={invoiceFilters.status}
                  onChange={(e) => setInvoiceFilters({...invoiceFilters, status: e.target.value})}
                >
                  <option value="all">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="paid">Paid</option>
                  <option value="overdue">Overdue</option>
                </select>
              </div>
              
              <div>
                <label htmlFor="invoice-date-range" className="block text-sm font-medium text-gray-700 mb-1">Date Range</label>
                <select
                  id="invoice-date-range"
                  className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={invoiceFilters.dateRange}
                  onChange={(e) => setInvoiceFilters({...invoiceFilters, dateRange: e.target.value})}
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
                  placeholder="Search invoices..."
                  className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 pr-3 py-2 border-gray-300 rounded-md text-sm"
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
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Invoice #
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tenant
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Amount
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Issue Date
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Due Date
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {invoices.length > 0 ? (
                    invoices.map((invoice) => (
                      <tr key={invoice.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">
                            {invoice.invoice_number}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600">
                              {/* Placeholder for tenant initials */}
                              TS
                            </div>
                            <div className="ml-3">
                              <div className="text-sm font-medium text-gray-900">
                                Tenant #{invoice.tenant_id}
                              </div>
                              <div className="text-sm text-gray-500">
                                {invoice.property_id ? `Property #${invoice.property_id}` : 'No property'}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">${invoice.amount.toFixed(2)}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {new Date(invoice.issue_date).toLocaleDateString()}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {new Date(invoice.due_date).toLocaleDateString()}
                          </div>
                          {new Date(invoice.due_date) < new Date() && invoice.status !== 'paid' && (
                            <div className="text-xs text-red-500">
                              Overdue by {Math.ceil((new Date() - new Date(invoice.due_date)) / (1000 * 60 * 60 * 24))} days
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`badge ${getStatusBadgeClass(invoice.status)}`}>
                            {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex space-x-2">
                            <button
                              className="text-indigo-600 hover:text-indigo-900"
                              title="Edit"
                            >
                              <i className="fas fa-edit"></i>
                            </button>
                            <button
                              className="text-green-600 hover:text-green-900"
                              title="Mark as Paid"
                            >
                              <i className="fas fa-check-circle"></i>
                            </button>
                            <button
                              className="text-blue-600 hover:text-blue-900"
                              title="Print"
                            >
                              <i className="fas fa-print"></i>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="7" className="px-6 py-4 text-center text-sm text-gray-500">
                        No invoices found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
      
      {activeTab === 'expenses' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="bg-white p-4 rounded-lg shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
            <div className="flex flex-col sm:flex-row sm:space-x-4 space-y-2 sm:space-y-0">
              <div>
                <label htmlFor="expense-category" className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select
                  id="expense-category"
                  className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={expenseFilters.category}
                  onChange={(e) => setExpenseFilters({...expenseFilters, category: e.target.value})}
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
                <label htmlFor="expense-date-range" className="block text-sm font-medium text-gray-700 mb-1">Date Range</label>
                <select
                  id="expense-date-range"
                  className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  value={expenseFilters.dateRange}
                  onChange={(e) => setExpenseFilters({...expenseFilters, dateRange: e.target.value})}
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
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Property
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Category
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Amount
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Vendor
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {expenses.length > 0 ? (
                    expenses.map((expense) => (
                      <tr key={expense.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">
                            Property #{expense.property_id}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {expense.category.charAt(0).toUpperCase() + expense.category.slice(1)}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">${expense.amount.toFixed(2)}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {new Date(expense.expense_date).toLocaleDateString()}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {expense.vendor_id ? `Vendor #${expense.vendor_id}` : 'No vendor'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex space-x-2">
                            <button
                              className="text-indigo-600 hover:text-indigo-900"
                              title="Edit"
                            >
                              <i className="fas fa-edit"></i>
                            </button>
                            <button
                              className="text-green-600 hover:text-green-900"
                              title="View Receipt"
                            >
                              <i className="fas fa-receipt"></i>
                            </button>
                            <button
                              className="text-red-600 hover:text-red-900"
                              title="Delete"
                            >
                              <i className="fas fa-trash-alt"></i>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6" className="px-6 py-4 text-center text-sm text-gray-500">
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
      
      {showNewPaymentModal && (
        <NewPaymentModal
          isOpen={showNewPaymentModal}
          onClose={handleCloseModal}
          onSuccess={() => {
            setShowNewPaymentModal(false);
            loadOverviewData(); // Refresh overview data after payment creation
          }}
        />
      )}
    </div>
  );
};

export default Accounting;
