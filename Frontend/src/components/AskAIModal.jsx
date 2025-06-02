import React from "react";

const AskAIModal = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-lg bg-white">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-800">Ask Brikli AI</h2>
          <button
            onClick={onClose}
            className="text-gray-600 hover:text-gray-800"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        <div className="text-center py-8">
          <div className="bg-green-100 text-green-600 w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-6">
            <i className="fas fa-robot text-2xl"></i>
          </div>

          <h3 className="text-2xl font-bold mb-3 text-green-600">
            Coming Soon
          </h3>

          <p className="text-gray-600 mb-6">
            Our AI assistant is learning and will be ready to help you soon.
            You'll be able to ask questions about property management, tenant
            relations, legal requirements, and more.
          </p>

          <div className="bg-green-50 p-4 rounded-lg mb-6">
            <p className="text-sm text-gray-700 italic">
              "What's the average rent for a 2-bedroom apartment in Chicago?"
            </p>
            <p className="text-sm text-gray-700 italic mt-2">
              "How do I handle a maintenance request for a broken water heater?"
            </p>
            <p className="text-sm text-gray-700 italic mt-2">
              "What are the legal requirements for security deposits in
              California?"
            </p>
          </div>

          <div className="border-t border-gray-100 pt-4 mt-4">
            <p className="text-sm text-gray-500">
              We're working hard to make our AI assistant as helpful as
              possible. Stay tuned!
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AskAIModal;
