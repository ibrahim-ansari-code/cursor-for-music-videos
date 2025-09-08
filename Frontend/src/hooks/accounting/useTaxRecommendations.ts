import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { 
  getSmartTaxRecommendation, 
  setUserTaxDefault, 
  setPropertyTaxDefault
} from '../../utils/api/accounting';
import type { SmartTaxRecommendation, TaxDetail } from '../../types/accounting';

interface UseTaxRecommendationsProps {
  propertyId?: number | string;
  category?: string;
}

interface TaxRecommendationState {
  smartTaxRecommendation: SmartTaxRecommendation | null;
  isLoadingSmartTax: boolean;
  smartTaxError: string | null;
}

interface TaxRecommendationActions {
  loadSmartTaxRecommendation: (params?: { property_id?: number; category?: string }) => Promise<void>;
  setUserDefault: (tax: TaxDetail) => Promise<boolean>;
  setPropertyDefault: (tax: TaxDetail, propertyId: number) => Promise<boolean>;
  clearRecommendations: () => void;
}

export const useTaxRecommendations = ({ 
  propertyId, 
  category 
}: UseTaxRecommendationsProps = {}): TaxRecommendationState & TaxRecommendationActions => {
  const [smartTaxRecommendation, setSmartTaxRecommendation] = useState<SmartTaxRecommendation | null>(null);
  const [isLoadingSmartTax, setIsLoadingSmartTax] = useState<boolean>(false);
  const [smartTaxError, setSmartTaxError] = useState<string | null>(null);

  const loadSmartTaxRecommendation = useCallback(async (params?: { property_id?: number; category?: string }) => {
    const finalPropertyId = params?.property_id || (typeof propertyId === 'string' ? parseInt(propertyId, 10) : propertyId);
    const finalCategory = params?.category || category;

    if (!finalPropertyId) {
      return;
    }

    setIsLoadingSmartTax(true);
    setSmartTaxError(null);

    try {
      const response = await getSmartTaxRecommendation({
        property_id: finalPropertyId,
        category: finalCategory || 'general',
      });

      if (response.success && response.data) {
        setSmartTaxRecommendation(response.data);
      } else {
        throw new Error(response.error || 'Failed to load tax recommendations');
      }
    } catch (error) {
      console.error('Error loading smart tax recommendations:', error);
      setSmartTaxError(error instanceof Error ? error.message : 'Failed to load tax recommendations');
      // Don't show toast for failed recommendations as it's not critical
    } finally {
      setIsLoadingSmartTax(false);
    }
  }, [propertyId, category]);

  const setUserDefault = useCallback(async (tax: TaxDetail): Promise<boolean> => {
    try {
      const response = await setUserTaxDefault({
        tax_name: tax.tax_name,
        tax_rate: tax.tax_rate,
      });

      if (response && response.success) {
        // Let the calling component handle success notifications
        return true;
      } else {
        throw new Error(response?.error || 'Failed to set user default');
      }
    } catch (error) {
      console.error('Error setting user tax default:', error);
      toast.error('Failed to set tax as user default');
      return false;
    }
  }, []);

  const setPropertyDefault = useCallback(async (tax: TaxDetail, targetPropertyId: number): Promise<boolean> => {
    try {
      const response = await setPropertyTaxDefault({
        property_id: targetPropertyId,
        tax_name: tax.tax_name,
        tax_rate: tax.tax_rate,
      });

      if (response && response.success) {
        // Let the calling component handle success notifications
        return true;
      } else {
        throw new Error(response?.error || 'Failed to set property default');
      }
    } catch (error) {
      console.error('Error setting property tax default:', error);
      toast.error('Failed to set tax as property default');
      return false;
    }
  }, []);

  const clearRecommendations = useCallback(() => {
    setSmartTaxRecommendation(null);
    setSmartTaxError(null);
  }, []);

  // Auto-load recommendations when dependencies change
  useEffect(() => {
    if (propertyId) {
      loadSmartTaxRecommendation({ property_id: typeof propertyId === 'string' ? parseInt(propertyId, 10) : propertyId, category });
    } else {
      // Clear recommendations when property is deselected
      clearRecommendations();
    }
  }, [propertyId, category, loadSmartTaxRecommendation, clearRecommendations]);

  return {
    // State
    smartTaxRecommendation,
    isLoadingSmartTax,
    smartTaxError,
    
    // Actions
    loadSmartTaxRecommendation,
    setUserDefault,
    setPropertyDefault,
    clearRecommendations,
  };
};