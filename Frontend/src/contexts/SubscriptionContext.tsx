/**
 * Global Subscription Context
 * Provides a global subscription modal that can be triggered from anywhere
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import SubscriptionRequiredModal from '../components/billing/SubscriptionRequiredModal';
import { subscriptionHandler } from '../utils/subscriptionHandler';

interface SubscriptionContextType {
  showSubscriptionModal: (featureName?: string) => void;
  hideSubscriptionModal: () => void;
}

const SubscriptionContext = createContext<SubscriptionContextType | undefined>(undefined);

export function SubscriptionProvider({ children }: { children: ReactNode }) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [featureName, setFeatureName] = useState<string>('this feature');

  const showSubscriptionModal = (feature?: string) => {
    setFeatureName(feature || 'this feature');
    setIsModalOpen(true);
  };

  const hideSubscriptionModal = () => {
    setIsModalOpen(false);
  };

  // Register the modal callback with the global handler
  useEffect(() => {
    subscriptionHandler.setShowModalCallback(showSubscriptionModal);
  }, []);

  return (
    <SubscriptionContext.Provider value={{ showSubscriptionModal, hideSubscriptionModal }}>
      {children}
      <SubscriptionRequiredModal
        isOpen={isModalOpen}
        onClose={hideSubscriptionModal}
        featureName={featureName}
      />
    </SubscriptionContext.Provider>
  );
}

export function useSubscriptionModal() {
  const context = useContext(SubscriptionContext);
  if (!context) {
    throw new Error('useSubscriptionModal must be used within SubscriptionProvider');
  }
  return context;
}

