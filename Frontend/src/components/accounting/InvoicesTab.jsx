import React from 'react';

const InvoicesTab = () => {
  return (
    <div className="h-full flex items-center justify-center p-6">
      <div className="text-center max-w-lg mx-auto p-6 bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="bg-blue-100 text-blue-600 w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-6">
          <i className="fas fa-file-invoice-dollar text-2xl"></i>
        </div>
        
        <h2 className="text-3xl font-bold mb-3 text-blue-600">Invoices Coming Soon</h2>
        
        <p className="text-gray-600 mb-8">
          We're building a powerful invoicing system to help you manage your property-related expenses. Create, send, and track invoices with ease.
        </p>
        
        <div className="bg-gray-50 p-4 rounded-lg mb-6">
          <div className="flex items-center mb-2">
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
              <i className="fas fa-check text-blue-600 text-sm"></i>
            </div>
            <p className="text-gray-700 text-left">Create and send professional invoices</p>
          </div>
          
          <div className="flex items-center mb-2">
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
              <i className="fas fa-check text-blue-600 text-sm"></i>
            </div>
            <p className="text-gray-700 text-left">Track payment status in real-time</p>
          </div>
          
          <div className="flex items-center">
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
              <i className="fas fa-check text-blue-600 text-sm"></i>
            </div>
            <p className="text-gray-700 text-left">Set up automatic payment reminders</p>
          </div>
        </div>
        
        <div className="pt-4 border-t border-gray-100 mt-6">
          <p className="text-sm text-gray-500">
            Have questions? Contact us at <a href="mailto:support@brikli.com" className="text-blue-600 hover:underline">support@brikli.com</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default InvoicesTab; 