import React, { useState, useEffect } from 'react';
import { fetchLeases, uploadLeaseDocument } from '../utils/api';
import ImportLeaseModal from '../components/ImportLeaseModal';
import UpdateLeaseStatusModal from '../components/UpdateLeaseStatusModal';

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

  const getStatusBadgeClass = (status) => {
    switch (status.toLowerCase()) {
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

  // Get the tenant's full name or construct it from first and last name
  const getTenantName = (tenant) => {
    if (!tenant) return 'No tenant assigned';
    if (tenant.full_name) return tenant.full_name;
    if (tenant.first_name || tenant.last_name) {
      return `${tenant.first_name || ''} ${tenant.last_name || ''}`.trim();
    }
    return `Tenant #${tenant.id}`;
  };

  // Get tenant initials for the avatar
  const getTenantInitials = (tenant) => {
    if (!tenant) return 'T';
    
    if (tenant.full_name) {
      return tenant.full_name.split(' ').map(n => n[0]).join('').toUpperCase();
    }
    
    if (tenant.first_name && tenant.last_name) {
      return (tenant.first_name[0] + tenant.last_name[0]).toUpperCase();
    }
    
    if (tenant.first_name) return tenant.first_name[0].toUpperCase();
    if (tenant.last_name) return tenant.last_name[0].toUpperCase();
    
    return 'T';
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
              <option value="DRAFT">Draft</option>
              <option value="PENDING">Pending</option>
              <option value="ACTIVE">Active</option>
              <option value="EXPIRED">Expired</option>
              <option value="TERMINATED">Terminated</option>
              <option value="RENEWED">Renewed</option>
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
                          {/* Tenant initials */}
                          {getTenantInitials(lease.tenant)}
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {getTenantName(lease.tenant)}
                          </div>
                          <div className="text-sm text-gray-500">
                            {lease.tenant?.email || ''}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {lease.property?.name || `Property #${lease.property_id}`}
                      </div>
                      <div className="text-sm text-gray-500">
                        {lease.unit?.name ? `Unit: ${lease.unit.name}` : (lease.unit_id ? `Unit ID: ${lease.unit_id}` : 'No unit specified')}
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
                        {lease.status.charAt(0).toUpperCase() + lease.status.slice(1).toLowerCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleShowModal('edit', lease)}
                          className="text-indigo-600 hover:text-indigo-900"
                          title="Edit lease"
                        >
                          <i className="fas fa-edit"></i>
                        </button>
                        <button
                          onClick={() => handleShowModal('upload', lease)}
                          className="text-green-600 hover:text-green-900"
                          title="Upload document"
                        >
                          <i className="fas fa-file-upload"></i>
                        </button>
                        <button
                          onClick={() => handleShowModal('status', lease)}
                          className="text-blue-600 hover:text-blue-900"
                          title="Update status"
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
      
      {/* Status Change Modal - Using the new component */}
      {showModal && modalType === 'status' && selectedLease && (
        <UpdateLeaseStatusModal
          isOpen={true}
          onClose={handleCloseModal}
          lease={selectedLease}
          onUpdate={loadLeases}
        />
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
