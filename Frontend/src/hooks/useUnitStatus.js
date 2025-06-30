import { useState, useEffect } from 'react';
import { fetchUnitLease } from '../utils/api';

/**
 * Custom hook to fetch and manage unit lease status
 * @param {string} unitId - The ID of the unit (UUID)
 * @returns {object} An object containing lease data, loading state, and error state
 */
export const useUnitStatus = (unitId) => {
  const [lease, setLease] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!unitId) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    const fetchLeaseInfo = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const leaseData = await fetchUnitLease(unitId);
        
        if (!cancelled) {
          setLease(leaseData);
        }
      } catch (err) {
        if (!cancelled) {
          // If it's a 404, the unit just doesn't have an active lease
          if (err.status === 404) {
            setLease(null);
            setError(null);
          } else {
            setError(err.message || 'Failed to fetch lease information');
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchLeaseInfo();

    // Cleanup function to prevent state updates on unmounted component
    return () => {
      cancelled = true;
    };
  }, [unitId]);

  // Refetch function for manual refresh
  const refetch = () => {
    if (unitId) {
      setLoading(true);
      fetchUnitLease(unitId)
        .then((leaseData) => {
          setLease(leaseData);
        })
        .catch((err) => {
          if (err.status === 404) {
            setLease(null);
            setError(null);
          } else {
            setError(err.message || 'Failed to fetch lease information');
          }
        })
        .finally(() => setLoading(false));
    }
  };

  return {
    lease,
    loading,
    error,
    refetch,
    hasActiveLease: !!lease,
  };
};

export default useUnitStatus;