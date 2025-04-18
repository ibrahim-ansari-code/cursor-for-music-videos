import React from 'react';

const InviteModal = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-lg bg-white">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-800">Invite Collaborators</h2>
          <button
            onClick={onClose}
            className="text-gray-600 hover:text-gray-800"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        <div className="text-center py-8">
          <div className="bg-purple-100 text-purple-600 w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-6">
            <i className="fas fa-user-plus text-2xl"></i>
          </div>
          
          <h3 className="text-2xl font-bold mb-3 text-purple-600">Coming Soon</h3>
          
          <p className="text-gray-600 mb-6">
            Our invite system is currently under development. Soon you'll be able to invite team members, tenants, and service providers to collaborate.
          </p>
          
          <div className="border-t border-gray-100 pt-4 mt-4">
            <p className="text-sm text-gray-500">
              In the meantime, you can reach us at <a href="mailto:support@brikli.com" className="text-purple-600 hover:underline">support@brikli.com</a> for any assistance.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InviteModal; 