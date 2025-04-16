import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { 
  fetchProperties, 
  createExpense
} from '../utils/api';

const EXPENSE_CATEGORIES = [
  'maintenance',
  'utilities',
  'taxes',
  'insurance',
  'administrative',
  'other'
];

const NewExpenseModal = ({ isOpen, onClose, onSuccess }) => {
  // Form state
  const [formData, setFormData] = useState({
    property_id: '',
    category: '',
    amount: '',
    expense_date: new Date().toISOString().split('T')[0],
    vendor_id: '',
    description: '',
    receipt_url: null
  });

  // UI state
  const [properties, setProperties] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Dropdown states
  const [dropdownOpen, setDropdownOpen] = useState('');
  const [propertySearchTerm, setPropertySearchTerm] = useState('');

  // Load properties on mount
  useEffect(() => {
    const loadProperties = async () => {
      try {
        const data = await fetchProperties();
        setProperties(data);
      } catch (err) {
        console.error('Failed to load properties:', err);
        setError('Failed to load properties. Please try again.');
      }
    };

    if (isOpen) {
      loadProperties();
    }
  }, [isOpen]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.property_id) {
      setError('Please select a property.');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Properly format the expense data to match backend expectations
      const expenseData = {
        property_id: parseInt(formData.property_id),
        category: formData.category,
        amount: parseFloat(formData.amount),
        expense_date: formData.expense_date,
        description: formData.description || '',
        vendor_id: formData.vendor_id ? parseInt(formData.vendor_id) : null,
        receipt_url: formData.receipt_url
      };

      console.log('Submitting expense with data:', expenseData);
      await createExpense(expenseData);
      // Success notification is handled by the parent component
      onSuccess?.();
      handleClose();
    } catch (err) {
      console.error('Failed to create expense:', err);
      setError(err.message || 'Failed to create expense. Please try again.');
      toast.error('Failed to create expense');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({
      property_id: '',
      category: '',
      amount: '',
      expense_date: new Date().toISOString().split('T')[0],
      vendor_id: '',
      description: '',
      receipt_url: null
    });
    setError(null);
    setPropertySearchTerm('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-lg bg-white">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-800">New Expense</h2>
          <button
            onClick={handleClose}
            className="text-gray-600 hover:text-gray-800"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Property Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Property *
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="Search properties..."
                value={propertySearchTerm}
                onChange={(e) => {
                  setPropertySearchTerm(e.target.value);
                  setDropdownOpen('property');
                }}
                className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              />
              {dropdownOpen === 'property' && (
                <div className="absolute z-10 mt-1 w-full bg-white shadow-lg rounded-md">
                  <ul className="max-h-60 overflow-auto rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                    {properties
                      .filter(property => 
                        property.name.toLowerCase().includes(propertySearchTerm.toLowerCase())
                      )
                      .map((property) => (
                        <li
                          key={property.id}
                          className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-blue-100"
                          onClick={() => {
                            setFormData(prev => ({ ...prev, property_id: property.id }));
                            setPropertySearchTerm(property.name);
                            setDropdownOpen('');
                          }}
                        >
                          <span className="font-normal block truncate">
                            {property.name}
                          </span>
                        </li>
                      ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Category Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category *
            </label>
            <select
              name="category"
              value={formData.category}
              onChange={handleInputChange}
              required
              className="block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="">Select a category</option>
              {EXPENSE_CATEGORIES.map(category => (
                <option key={category} value={category}>
                  {category.charAt(0).toUpperCase() + category.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Amount *
            </label>
            <div className="relative rounded-md shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="text-gray-500 sm:text-sm">$</span>
              </div>
              <input
                type="number"
                name="amount"
                value={formData.amount}
                onChange={handleInputChange}
                min="0"
                step="0.01"
                required
                className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-7 pr-3 py-2 border-gray-300 rounded-md text-sm"
                placeholder="0.00"
              />
            </div>
          </div>

          {/* Expense Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date *
            </label>
            <input
              type="date"
              name="expense_date"
              value={formData.expense_date}
              onChange={handleInputChange}
              required
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 border-gray-300 rounded-md text-sm"
            />
          </div>

          {/* Vendor */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Vendor
            </label>
            <input
              type="text"
              name="vendor_id"
              value={formData.vendor_id}
              onChange={handleInputChange}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 border-gray-300 rounded-md text-sm"
              placeholder="Optional vendor name or ID"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              rows="2"
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 border-gray-300 rounded-md text-sm"
              placeholder="Description of the expense..."
            />
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
              <span className="block sm:inline">{error}</span>
            </div>
          )}

          {/* Form Actions */}
          <div className="mt-6 flex justify-end space-x-3">
            <button
              type="button"
              onClick={handleClose}
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating...
                </>
              ) : (
                'Create Expense'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default NewExpenseModal; 