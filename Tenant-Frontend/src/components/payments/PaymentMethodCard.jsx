import React from 'react';
import PropTypes from 'prop-types';
import { FaCreditCard, FaUniversity, FaTrash } from 'react-icons/fa';

/**
 * PaymentMethodCard Component
 * Displays a single payment method (card or bank account) with remove functionality
 */
const PaymentMethodCard = ({ method, onRemove }) => {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className="flex-shrink-0">
          {method.type === 'card' ? (
            <FaCreditCard className="text-lg text-gray-600" />
          ) : (
            <FaUniversity className="text-lg text-gray-600" />
          )}
        </div>
        <div>
          <div className="font-medium text-gray-900 text-sm">
            {method.type === 'card' 
              ? `${method.brand || 'Card'} ending in ${method.last4}`
              : `${method.bankName} (****${method.last4})`
            }
          </div>
          <div className="text-xs text-gray-500">
            {method.type === 'card' 
              ? (method.expiryDate && `Expires ${method.expiryDate}`)
              : method.ownerName
            }
          </div>
        </div>
      </div>
      <button
        onClick={() => onRemove(method.id)}
        className="text-gray-400 hover:text-red-600 transition-colors p-1"
        aria-label="Remove payment method"
      >
        <FaTrash className="text-xs" />
      </button>
    </div>
  );
};

PaymentMethodCard.propTypes = {
  method: PropTypes.shape({
    id: PropTypes.string.isRequired,
    type: PropTypes.oneOf(['card', 'bank']).isRequired,
    last4: PropTypes.string.isRequired,
    brand: PropTypes.string,
    bankName: PropTypes.string,
    expiryDate: PropTypes.string,
    ownerName: PropTypes.string
  }).isRequired,
  onRemove: PropTypes.func.isRequired
};

export default PaymentMethodCard;
