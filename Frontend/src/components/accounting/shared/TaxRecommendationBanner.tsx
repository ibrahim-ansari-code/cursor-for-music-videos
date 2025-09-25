import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Lightbulb } from 'lucide-react';
import type { SmartTaxRecommendation, TaxDetail } from '../../../types/accounting';

interface TaxRecommendationBannerProps {
  smartTaxRecommendation: SmartTaxRecommendation | null;
  isLoadingSmartTax: boolean;
  onApplyTax: (tax: TaxDetail) => void;
  onSetUserDefault: (tax: TaxDetail) => Promise<boolean>;
  onSetPropertyDefault: (tax: TaxDetail, propertyId: number) => Promise<boolean>;
  propertyId?: number;
  className?: string;
  currentTaxes?: TaxDetail[];
  isInline?: boolean;
}

const TaxRecommendationBanner: React.FC<TaxRecommendationBannerProps> = ({
  smartTaxRecommendation,
  isLoadingSmartTax,
  onApplyTax,
  className = "",
  currentTaxes = [],
  isInline = false,
}) => {
  // Check if the smart tax recommendation is already in the current taxes
  const isDuplicateRecommendation = smartTaxRecommendation && currentTaxes.some(tax => 
    tax.tax_name === smartTaxRecommendation.tax_name && 
    tax.tax_rate === smartTaxRecommendation.tax_rate &&
    tax.tax_name.trim() !== "" &&
    String(tax.tax_rate).trim() !== ""
  );

  // Inline version for inside tax fields
  if (isInline) {
    if (isLoadingSmartTax) {
      return (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="absolute top-12 left-0 right-0 z-10 bg-white dark:bg-gray-800 border border-emerald-200 dark:border-emerald-700 rounded-lg shadow-lg p-3"
        >
          <div className="flex items-center space-x-2">
            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-emerald-600"></div>
            <span className="text-emerald-700 dark:text-emerald-400 text-xs font-medium">
              Finding tax recommendations...
            </span>
          </div>
        </motion.div>
      );
    }

    return (
      <AnimatePresence>
        {smartTaxRecommendation && smartTaxRecommendation.tax_name && !isDuplicateRecommendation && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            className="absolute bottom-full left-0 mb-1 z-50 bg-gradient-to-r from-emerald-50 to-green-50 dark:from-emerald-900/30 dark:to-green-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg shadow-lg pointer-events-auto"
            style={{ 
              width: 'calc(100% + 180px)', // Span across fields with room for Apply button
              transform: 'translateZ(0)' // Force GPU layer to prevent layout shifts
            }}
          >
            <div className="flex items-center justify-between px-3 py-2.5">
              <div className="flex items-center space-x-2 flex-1">
                <div className="flex-shrink-0 w-4 h-4 bg-emerald-500 rounded-full flex items-center justify-center">
                  <Lightbulb className="w-2.5 h-2.5 text-white" />
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs font-semibold text-emerald-800 dark:text-emerald-300">
                    {smartTaxRecommendation.tax_name}
                  </span>
                  <span className="text-xs text-emerald-700 dark:text-emerald-400 font-bold">
                    {(() => {
                      const rate = parseFloat(smartTaxRecommendation.tax_rate);
                      return isNaN(rate) ? '0.00' : rate.toFixed(2);
                    })()}%
                  </span>
                </div>
                <span className="text-xs text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                  Recommended for this property
                </span>
              </div>
              <button
                type="button"
                onClick={() => onApplyTax({
                  tax_name: smartTaxRecommendation.tax_name,
                  tax_rate: smartTaxRecommendation.tax_rate,
                })}
                className="flex-shrink-0 bg-emerald-500 hover:bg-emerald-600 dark:bg-emerald-600 dark:hover:bg-emerald-700 text-white px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ml-3"
              >
                Apply
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    );
  }

  // Legacy banner version for backward compatibility
  if (isLoadingSmartTax) {
    return (
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        className={`bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4 mb-4 ${className}`}
      >
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="text-blue-700 dark:text-blue-400 text-sm font-medium">
            Loading smart tax recommendations...
          </span>
        </div>
      </motion.div>
    );
  }

  return (
    <AnimatePresence>
      {smartTaxRecommendation && smartTaxRecommendation.tax_name && !isDuplicateRecommendation && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className={`bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg p-4 mb-4 ${className}`}
        >
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <svg 
                className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" 
                />
              </svg>
            </div>
            
            <div className="flex-grow">
              <h4 className="text-green-800 dark:text-green-300 font-medium text-sm mb-2">
                Smart Tax Recommendation
              </h4>
              
              <div className="bg-white dark:bg-gray-800 rounded-md p-3 border border-green-100 dark:border-green-700">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div>
                      <span className="font-medium text-gray-900 dark:text-gray-100">
                        {smartTaxRecommendation.tax_name}
                      </span>
                      <span className="text-gray-600 dark:text-gray-400 ml-2">
                        {parseFloat(smartTaxRecommendation.tax_rate).toFixed(2)}%
                      </span>
                      
                    </div>
                  </div>
                  
                  <div className="flex items-center">
                    <button
                      type="button"
                      onClick={() => onApplyTax({
                        tax_name: smartTaxRecommendation.tax_name,
                        tax_rate: smartTaxRecommendation.tax_rate,
                      })}
                      className="bg-green-600 hover:bg-green-700 dark:bg-green-700 dark:hover:bg-green-800 text-white px-3 py-1 rounded-md text-sm font-medium transition-colors"
                    >
                      Apply
                    </button>
                  </div>
                </div>
                
                {/* Reasoning */}
                {smartTaxRecommendation.reasoning && (
                  <div className="mt-2 pt-2 border-t border-green-100 dark:border-green-700">
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      {smartTaxRecommendation.reasoning}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default TaxRecommendationBanner;