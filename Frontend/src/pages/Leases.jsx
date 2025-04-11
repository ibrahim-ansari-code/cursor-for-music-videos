import React, { useState, useEffect } from 'react';
import { fetchLeases, uploadLeaseDocument, updateLeaseStatus } from '../utils/api';
import ImportLeaseModal from '../components/ImportLeaseModal';

const Leases = () => {
  const [leases, setLeases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLease, setSelectedLease] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState(null); // 'create', 'edit', 'upload', 'status'
  const [statusFilter, setStatusFilter] = useState('all');
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadDocumentType, setUploadDocumentType] = useState('contract');
  const [documentUploading, setDocumentUploading] = useState(false);

  useEffect(() => {
    loadLeases();
  }, [statusFilter]);

  const loadLeases = async () => {
    try {
      setLoading(true);
      const data = await fetchLeases({ 
        status: statusFilter !== 'all' ? statusFilter : undefined 
      });
      setLeases(data);
      setError(null);
    } catch (err) {
      console.error('Error loading leases:', err);
      setError('Failed to load leases. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleShowModal = (type, lease = null) => {
    setModalType(type);
    setSelectedLease(lease);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedLease(null);
    setUploadFile(null);
    setUploadDocumentType('contract');
  };

  const handleFileChange = (e) => {
    setUploadFile(e.target.files[0]);
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    
    if (!uploadFile || !selectedLease) return;
    
    try {
      setDocumentUploading(true);
      
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('document_type', uploadDocumentType);
      
      await uploadLeaseDocument(selectedLease.id, formData);
      
      handleCloseModal();
      loadLeases();
    } catch (err) {
      console.error('Error uploading document:', err);
      setError('Failed to upload document. Please try again.');
    } finally {
      setDocumentUploading(false);
    }
  };

  const handleStatusChange = async (leaseId, newStatus) => {
    try {
      await updateLeaseStatus(leaseId, newStatus);
      loadLeases();
    } catch (err) {
      console.error('Error updating lease status:', err);
      setError('Failed to update lease status. Please try again.');
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'active':
        return 'badge-success';
      case 'pending':
        return 'badge-warning';
      case 'expired':
      case 'terminated':
        return 'badge-danger';
      case 'draft':
        return 'badge-info';
      default:
        return 'badge-info';
    }
  };

  const handleImport = () => {
    handleCloseModal();
    loadLeases();
  };

  if (loading && leases.length === 0) {
    return (
      <div className="p-4 flex justify-center items-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-3 text-gray-600">Loading leases...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end">
        <div className="mt-3 sm:mt-0 flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
          <div className="relative">
            <select
              className="block w-full rounded-md border-gray-300 pr-10 py-2 text-base focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="pending">Pending</option>
              <option value="active">Active</option>
              <option value="expired">Expired</option>
              <option value="terminated">Terminated</option>
            </select>
          </div>
          
          <button
            onClick={() => handleShowModal('create')}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-plus mr-2"></i>
            New Lease
          </button>
        </div>
      </div>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
          <button 
            onClick={loadLeases}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}
      
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tenant
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Property
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Dates
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rent
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
              {leases.length > 0 ? (
                leases.map((lease) => (
                  <tr key={lease.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-600">
                          {/* Placeholder for tenant initials */}
                          TS
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {/* Placeholder for tenant name */}
                            Tenant #{lease.tenant_id}
                          </div>
                          <div className="text-sm text-gray-500">
                            {lease.tenant_id ? `ID: ${lease.tenant_id}` : 'No tenant assigned'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {/* Placeholder for property name */}
                        Property #{lease.property_id}
                      </div>
                      <div className="text-sm text-gray-500">
                        {lease.unit_id ? `Unit: ${lease.unit_id}` : 'No unit specified'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {new Date(lease.start_date).toLocaleDateString()} - {new Date(lease.end_date).toLocaleDateString()}
                      </div>
                      <div className="text-sm text-gray-500">
                        {Math.round((new Date(lease.end_date) - new Date(lease.start_date)) / (1000 * 60 * 60 * 24 * 30))} months
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">${lease.monthly_rent.toFixed(2)}/month</div>
                      <div className="text-sm text-gray-500">Due: Day {lease.rent_due_day}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`badge ${getStatusBadgeClass(lease.status)}`}>
                        {lease.status.charAt(0).toUpperCase() + lease.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleShowModal('edit', lease)}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          <i className="fas fa-edit"></i>
                        </button>
                        <button
                          onClick={() => handleShowModal('upload', lease)}
                          className="text-green-600 hover:text-green-900"
                        >
                          <i className="fas fa-file-upload"></i>
                        </button>
                        <button
                          onClick={() => handleShowModal('status', lease)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          <i className="fas fa-tasks"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="px-6 py-4 text-center text-sm text-gray-500">
                    No leases found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Upload Document Modal */}
      {showModal && modalType === 'upload' && selectedLease && (
        <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black bg-opacity-50"></div>
          <div className="relative bg-white rounded-lg max-w-md w-full mx-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Upload Lease Document</h3>
              <button onClick={handleCloseModal} className="text-gray-400 hover:text-gray-500">
                <i className="fas fa-times"></i>
              </button>
            </div>
            
            <form onSubmit={handleUploadDocument}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Document Type
                </label>
                <select
                  className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={uploadDocumentType}
                  onChange={(e) => setUploadDocumentType(e.target.value)}
                  required
                >
                  <option value="contract">Lease Contract</option>
                  <option value="addendum">Addendum</option>
                  <option value="notice">Notice</option>
                  <option value="inspection">Inspection Report</option>
                  <option value="other">Other</option>
                </select>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  File
                </label>
                <input
                  type="file"
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  onChange={handleFileChange}
                  required
                />
              </div>
              
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!uploadFile || documentUploading}
                  className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  {documentUploading ? 'Uploading...' : 'Upload'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      
      {/* Status Change Modal */}
      {showModal && modalType === 'status' && selectedLease && (
        <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black bg-opacity-50"></div>
          <div className="relative bg-white rounded-lg max-w-md w-full mx-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Update Lease Status</h3>
              <button onClick={handleCloseModal} className="text-gray-400 hover:text-gray-500">
                <i className="fas fa-times"></i>
              </button>
            </div>
            
            <div className="mb-4">
              <p className="text-sm text-gray-500">
                Current Status: <span className={`badge ${getStatusBadgeClass(selectedLease.status)}`}>
                  {selectedLease.status.charAt(0).toUpperCase() + selectedLease.status.slice(1)}
                </span>
              </p>
            </div>
            
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">Change status to:</p>
              
              <div className="grid grid-cols-2 gap-2">
                {['draft', 'pending', 'active', 'expired', 'terminated', 'renewed'].map((status) => (
                  <button
                    key={status}
                    onClick={() => {
                      handleStatusChange(selectedLease.id, status);
                      handleCloseModal();
                    }}
                    disabled={selectedLease.status === status}
                    className={`px-4 py-2 text-sm font-medium rounded-md ${
                      selectedLease.status === status 
                        ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                        : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="mt-6 flex justify-end">
              <button
                onClick={handleCloseModal}
                className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Import Lease Modal */}
      {showModal && modalType === 'create' && (
        <ImportLeaseModal
          isOpen={showModal}
          onClose={handleCloseModal}
          onImport={handleImport}
        />
      )}
    </div>
  );
};

export default Leases;
