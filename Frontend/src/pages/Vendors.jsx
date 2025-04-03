import React, { useState, useEffect } from 'react';
import { fetchVendors, updateVendorStatus, uploadVendorDocument, assignVendorToProperty } from '../utils/api';

const Vendors = () => {
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedVendor, setSelectedVendor] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState(null); // 'create', 'edit', 'upload', 'approve', 'assign'
  const [statusFilter, setStatusFilter] = useState('all');
  const [businessTypeFilter, setBusinessTypeFilter] = useState('all');
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadDocumentType, setUploadDocumentType] = useState('license');
  const [documentUploading, setDocumentUploading] = useState(false);
  const [properties, setProperties] = useState([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState('');
  const [chatQuery, setChatQuery] = useState('');
  const [chatResponse, setChatResponse] = useState('');
  const [showChat, setShowChat] = useState(false);

  useEffect(() => {
    loadVendors();
    // In a real app, we would also load properties here
    setProperties([
      { id: 1, name: 'Oceanview Apartments' },
      { id: 2, name: 'Downtown Lofts' },
      { id: 3, name: 'Sunset Heights' },
    ]);
  }, [statusFilter, businessTypeFilter]);

  const loadVendors = async () => {
    try {
      setLoading(true);
      const data = await fetchVendors({ 
        status: statusFilter !== 'all' ? statusFilter : undefined,
        business_type: businessTypeFilter !== 'all' ? businessTypeFilter : undefined 
      });
      setVendors(data);
      setError(null);
    } catch (err) {
      console.error('Error loading vendors:', err);
      setError('Failed to load vendors. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleShowModal = (type, vendor = null) => {
    setModalType(type);
    setSelectedVendor(vendor);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedVendor(null);
    setUploadFile(null);
    setUploadDocumentType('license');
    setSelectedPropertyId('');
  };

  const handleStatusChange = async (vendorId, newStatus) => {
    try {
      await updateVendorStatus(vendorId, newStatus);
      loadVendors();
    } catch (err) {
      console.error('Error updating vendor status:', err);
      setError('Failed to update vendor status. Please try again.');
    }
  };

  const handleFileChange = (e) => {
    setUploadFile(e.target.files[0]);
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    
    if (!uploadFile || !selectedVendor) return;
    
    try {
      setDocumentUploading(true);
      
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('document_type', uploadDocumentType);
      
      await uploadVendorDocument(selectedVendor.id, formData);
      
      handleCloseModal();
      loadVendors();
    } catch (err) {
      console.error('Error uploading document:', err);
      setError('Failed to upload document. Please try again.');
    } finally {
      setDocumentUploading(false);
    }
  };

  const handleAssignToProperty = async (e) => {
    e.preventDefault();
    
    if (!selectedPropertyId || !selectedVendor) return;
    
    try {
      await assignVendorToProperty(selectedVendor.id, {
        property_id: parseInt(selectedPropertyId),
        is_active: true
      });
      
      handleCloseModal();
      loadVendors();
    } catch (err) {
      console.error('Error assigning vendor to property:', err);
      setError('Failed to assign vendor to property. Please try again.');
    }
  };

  const handleAskAI = async () => {
    if (!chatQuery) return;
    
    try {
      // In a real app, we would call an API here
      setChatResponse("I'm here to help with your onboarding process. You can ask about insurance requirements, payment terms, required documents, or the approval process.");
    } catch (err) {
      console.error('Error getting AI response:', err);
      setChatResponse('Sorry, I encountered an error. Please try again.');
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'approved':
        return 'badge-success';
      case 'pending':
        return 'badge-warning';
      case 'denied':
      case 'inactive':
        return 'badge-danger';
      default:
        return 'badge-info';
    }
  };

  if (loading && vendors.length === 0) {
    return (
      <div className="p-4 flex justify-center items-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-3 text-gray-600">Loading vendors...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Vendor Management</h1>
        
        <div className="mt-3 sm:mt-0 flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
          <div className="sm:flex sm:space-x-2">
            <select
              className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm mb-2 sm:mb-0"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="denied">Denied</option>
              <option value="inactive">Inactive</option>
            </select>
            
            <select
              className="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              value={businessTypeFilter}
              onChange={(e) => setBusinessTypeFilter(e.target.value)}
            >
              <option value="all">All Business Types</option>
              <option value="plumbing">Plumbing</option>
              <option value="electrical">Electrical</option>
              <option value="cleaning">Cleaning</option>
              <option value="landscaping">Landscaping</option>
              <option value="general">General Contractor</option>
            </select>
          </div>
          
          <button
            onClick={() => setShowChat(!showChat)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
          >
            <i className="fas fa-robot mr-2"></i>
            AI Assistant
          </button>
          
          <button
            onClick={() => handleShowModal('create')}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i className="fas fa-plus mr-2"></i>
            New Vendor
          </button>
        </div>
      </div>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
          <button 
            onClick={loadVendors}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}
      
      {/* AI Chatbot Assistant */}
      {showChat && (
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-medium text-gray-900">AI Vendor Assistant</h2>
            <button 
              onClick={() => setShowChat(false)}
              className="text-gray-400 hover:text-gray-500"
            >
              <i className="fas fa-times"></i>
            </button>
          </div>
          
          <div className="border border-gray-200 rounded-lg p-4 mb-4 h-32 overflow-y-auto bg-gray-50">
            {chatResponse ? (
              <div className="flex items-start mb-3">
                <div className="flex-shrink-0 h-8 w-8 rounded-full bg-purple-100 flex items-center justify-center text-purple-500">
                  <i className="fas fa-robot"></i>
                </div>
                <div className="ml-3 bg-white p-3 rounded-lg shadow-sm">
                  <p className="text-sm text-gray-800">{chatResponse}</p>
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-sm text-center p-4">
                Ask the AI assistant for help with vendor onboarding, requirements, or processes.
              </div>
            )}
          </div>
          
          <div className="flex">
            <input
              type="text"
              value={chatQuery}
              onChange={(e) => setChatQuery(e.target.value)}
              placeholder="Ask a question about vendor onboarding..."
              className="flex-1 focus:ring-blue-500 focus:border-blue-500 block w-full min-w-0 rounded-md sm:text-sm border-gray-300"
            />
            <button
              onClick={handleAskAI}
              className="ml-3 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <i className="fas fa-paper-plane mr-2"></i>
              Send
            </button>
          </div>
        </div>
      )}
      
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Company
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Business Type
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Contact
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Insurance
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
              {vendors.length > 0 ? (
                vendors.map((vendor) => (
                  <tr key={vendor.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-600">
                          {vendor.company_name.charAt(0)}
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {vendor.company_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {vendor.website || 'No website'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {vendor.business_type.charAt(0).toUpperCase() + vendor.business_type.slice(1)}
                      </div>
                      <div className="text-sm text-gray-500">
                        {vendor.tax_id || 'No Tax ID'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {/* Placeholder for contact info */}
                        User #{vendor.user_id}
                      </div>
                      <div className="text-sm text-gray-500">
                        {/* Placeholder for email */}
                        vendor{vendor.id}@example.com
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {vendor.insurance_provider || 'Not provided'}
                      </div>
                      <div className="text-sm text-gray-500">
                        {vendor.insurance_expiry_date 
                          ? `Expires: ${new Date(vendor.insurance_expiry_date).toLocaleDateString()}`
                          : 'No expiry date'
                        }
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`badge ${getStatusBadgeClass(vendor.status)}`}>
                        {vendor.status.charAt(0).toUpperCase() + vendor.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleShowModal('edit', vendor)}
                          className="text-indigo-600 hover:text-indigo-900"
                          title="Edit"
                        >
                          <i className="fas fa-edit"></i>
                        </button>
                        <button
                          onClick={() => handleShowModal('upload', vendor)}
                          className="text-green-600 hover:text-green-900"
                          title="Upload Documents"
                        >
                          <i className="fas fa-file-upload"></i>
                        </button>
                        <button
                          onClick={() => handleShowModal('approve', vendor)}
                          className="text-blue-600 hover:text-blue-900"
                          title="Change Status"
                        >
                          <i className="fas fa-check-circle"></i>
                        </button>
                        <button
                          onClick={() => handleShowModal('assign', vendor)}
                          className="text-purple-600 hover:text-purple-900"
                          title="Assign to Property"
                        >
                          <i className="fas fa-building"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="px-6 py-4 text-center text-sm text-gray-500">
                    No vendors found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Status Change Modal */}
      {showModal && modalType === 'approve' && selectedVendor && (
        <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black bg-opacity-50"></div>
          <div className="relative bg-white rounded-lg max-w-md w-full mx-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Update Vendor Status</h3>
              <button onClick={handleCloseModal} className="text-gray-400 hover:text-gray-500">
                <i className="fas fa-times"></i>
              </button>
            </div>
            
            <div className="mb-4">
              <p className="text-sm text-gray-500">
                Current Status: <span className={`badge ${getStatusBadgeClass(selectedVendor.status)}`}>
                  {selectedVendor.status.charAt(0).toUpperCase() + selectedVendor.status.slice(1)}
                </span>
              </p>
            </div>
            
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">Change status to:</p>
              
              <div className="grid grid-cols-2 gap-2">
                {['pending', 'approved', 'denied', 'inactive'].map((status) => (
                  <button
                    key={status}
                    onClick={() => {
                      handleStatusChange(selectedVendor.id, status);
                      handleCloseModal();
                    }}
                    disabled={selectedVendor.status === status}
                    className={`px-4 py-2 text-sm font-medium rounded-md ${
                      selectedVendor.status === status 
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
      
      {/* Upload Document Modal */}
      {showModal && modalType === 'upload' && selectedVendor && (
        <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black bg-opacity-50"></div>
          <div className="relative bg-white rounded-lg max-w-md w-full mx-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Upload Vendor Document</h3>
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
                  <option value="license">Business License</option>
                  <option value="insurance">Insurance Certificate</option>
                  <option value="certification">Professional Certification</option>
                  <option value="tax">Tax Document</option>
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
      
      {/* Assign to Property Modal */}
      {showModal && modalType === 'assign' && selectedVendor && (
        <div className="fixed inset-0 overflow-y-auto z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black bg-opacity-50"></div>
          <div className="relative bg-white rounded-lg max-w-md w-full mx-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Assign Vendor to Property</h3>
              <button onClick={handleCloseModal} className="text-gray-400 hover:text-gray-500">
                <i className="fas fa-times"></i>
              </button>
            </div>
            
            <form onSubmit={handleAssignToProperty}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Select Property
                </label>
                <select
                  className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={selectedPropertyId}
                  onChange={(e) => setSelectedPropertyId(e.target.value)}
                  required
                >
                  <option value="">Select a property</option>
                  {properties.map((property) => (
                    <option key={property.id} value={property.id}>
                      {property.name}
                    </option>
                  ))}
                </select>
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
                  disabled={!selectedPropertyId}
                  className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  Assign
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Vendors;
