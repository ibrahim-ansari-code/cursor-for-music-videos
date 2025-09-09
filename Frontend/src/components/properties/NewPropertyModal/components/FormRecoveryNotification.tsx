import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RotateCcw, X, Clock, CheckCircle, Sparkles, Shield, Database } from 'lucide-react';

interface FormRecoveryNotificationProps {
  isVisible: boolean;
  onRestore: () => void;
  onDismiss: () => void;
  lastSavedAt: Date | null;
  formType?: string;
}

const FormRecoveryNotification: React.FC<FormRecoveryNotificationProps> = ({
  isVisible,
  onRestore,
  onDismiss,
  lastSavedAt,
  formType = 'property form'
}) => {
  const [isRestoring, setIsRestoring] = useState(false);
  const [isRestored, setIsRestored] = useState(false);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [showPulse, setShowPulse] = useState(true);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const handleRestore = async () => {
    setIsRestoring(true);
    
    // Add a slight delay for better UX
    await new Promise(resolve => setTimeout(resolve, 500));
    
    try {
      setRestoreError(null); // Clear any previous errors
      onRestore();
      setIsRestored(true);
      
      // Auto-dismiss after showing success
      timeoutRef.current = setTimeout(() => {
        onDismiss();
        setIsRestored(false);
      }, 2000);
    } catch (error) {
      console.warn('Failed to restore form data:', error);
      setRestoreError('Failed to restore form data. Please try again.');
      // Don't auto-dismiss on error, let user manually handle it
    } finally {
      setIsRestoring(false);
    }
  };

  const formatLastSaved = (date: Date): string => {
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'just now';
    if (diffInMinutes < 60) return `${diffInMinutes} minute${diffInMinutes !== 1 ? 's' : ''} ago`;
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours} hour${diffInHours !== 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString();
  };

  // Premium success state with enterprise-grade visual feedback
  if (isRestored) {
    return (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0, y: -60, scale: 0.8 }}
          animate={{ 
            opacity: 1, 
            y: 0, 
            scale: 1,
            transition: { 
              type: "spring", 
              stiffness: 300, 
              damping: 25 
            }
          }}
          exit={{ 
            opacity: 0, 
            y: -60, 
            scale: 0.9,
            transition: { duration: 0.3, ease: "easeIn" }
          }}
          className="fixed top-6 left-1/2 transform -translate-x-1/2 z-50"
        >
          {/* Premium success notification with glassmorphism */}
          <motion.div 
            className="relative bg-white/95 backdrop-blur-xl border border-emerald-200/50 rounded-2xl shadow-2xl overflow-hidden"
            initial={{ boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1)" }}
            animate={{ 
              boxShadow: [
                "0 10px 25px -5px rgba(0, 0, 0, 0.1)",
                "0 20px 40px -5px rgba(16, 185, 129, 0.2)",
                "0 10px 25px -5px rgba(0, 0, 0, 0.1)"
              ],
              transition: { duration: 2, repeat: 1 }
            }}
          >
            {/* Animated gradient background */}
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-emerald-50 via-green-50 to-teal-50"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
            />
            
            {/* Success sparkle effects */}
            <motion.div
              className="absolute top-2 right-2"
              initial={{ opacity: 0, scale: 0 }}
              animate={{ 
                opacity: [0, 1, 0], 
                scale: [0, 1.2, 1],
                rotate: [0, 180, 360]
              }}
              transition={{ 
                duration: 1.5, 
                times: [0, 0.5, 1],
                repeat: 1
              }}
            >
              <Sparkles className="h-4 w-4 text-emerald-500" />
            </motion.div>
            
            <div className="relative px-6 py-4 flex items-center space-x-4">
              {/* Success icon with premium animation */}
              <motion.div 
                className="flex-shrink-0 p-2 bg-emerald-500 rounded-full shadow-lg"
                initial={{ scale: 0, rotate: -180 }}
                animate={{ 
                  scale: 1, 
                  rotate: 0,
                  transition: { 
                    type: "spring", 
                    stiffness: 400, 
                    damping: 20,
                    delay: 0.1 
                  }
                }}
              >
                <CheckCircle className="h-5 w-5 text-white" />
              </motion.div>
              
              <div className="flex-1">
                <motion.h4 
                  className="font-semibold text-emerald-900 text-sm"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  Form Data Restored
                </motion.h4>
                <motion.p 
                  className="text-xs text-emerald-700"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  Your progress has been successfully recovered
                </motion.p>
              </div>
              
              {/* Premium status indicator */}
              <motion.div 
                className="flex items-center space-x-1 px-3 py-1 bg-emerald-100 rounded-full"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.4 }}
              >
                <Shield className="h-3 w-3 text-emerald-600" />
                <span className="text-xs font-medium text-emerald-800">Secure</span>
              </motion.div>
            </div>
          </motion.div>
        </motion.div>
      </AnimatePresence>
    );
  }

  // Add subtle pulse effect for attention
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => setShowPulse(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [isVisible]);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: -60, scale: 0.9, rotateX: 15 }}
          animate={{ 
            opacity: 1, 
            y: 0, 
            scale: 1, 
            rotateX: 0,
            transition: { 
              type: "spring", 
              stiffness: 280, 
              damping: 20,
              duration: 0.6
            }
          }}
          exit={{ 
            opacity: 0, 
            y: -60, 
            scale: 0.95,
            rotateX: -10,
            transition: { duration: 0.3, ease: "easeInOut" }
          }}
          className="fixed top-6 left-1/2 transform -translate-x-1/2 z-50"
          style={{ perspective: "1000px" }}
        >
          {/* Premium glassmorphism notification card */}
          <motion.div 
            className="relative bg-white/95 backdrop-blur-2xl border border-slate-200/60 rounded-2xl shadow-2xl overflow-hidden max-w-md"
            animate={showPulse ? {
              boxShadow: [
                "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
                "0 25px 50px -12px rgba(59, 130, 246, 0.25), 0 15px 20px -5px rgba(59, 130, 246, 0.1)",
                "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
              ]
            } : {
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
            }}
            transition={{ duration: 2, repeat: showPulse ? Infinity : 0 }}
          >
            {/* Animated gradient border effect */}
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-indigo-500/20 to-purple-500/20 rounded-2xl"
              initial={{ opacity: 0 }}
              animate={{ opacity: showPulse ? [0.3, 0.6, 0.3] : 0.3 }}
              transition={{ duration: 2, repeat: showPulse ? Infinity : 0 }}
            />
            
            {/* Subtle animated background pattern */}
            <motion.div
              className="absolute inset-0 bg-gradient-to-br from-slate-50 via-blue-50/50 to-indigo-50/50"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
            />
            
            <div className="relative p-5">
              <div className="flex items-start space-x-4">
                {/* Premium icon with data visualization */}
                <motion.div 
                  className="flex-shrink-0 relative"
                  initial={{ scale: 0, rotate: -45 }}
                  animate={{ 
                    scale: 1, 
                    rotate: 0,
                    transition: { 
                      type: "spring", 
                      stiffness: 300, 
                      damping: 15,
                      delay: 0.2 
                    }
                  }}
                >
                  <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl shadow-lg">
                    <Database className="h-5 w-5 text-white" />
                  </div>
                  {/* Subtle pulse indicator */}
                  <motion.div
                    className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full"
                    animate={showPulse ? { scale: [1, 1.3, 1], opacity: [1, 0.6, 1] } : { scale: 1, opacity: 1 }}
                    transition={{ duration: 1.5, repeat: showPulse ? Infinity : 0 }}
                  />
                </motion.div>
                
                <div className="flex-1 min-w-0">
                  {/* Premium typography with staggered animation */}
                  <motion.h4 
                    className="text-sm font-bold text-slate-900 mb-1 leading-tight"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                  >
                    Recovery Available
                  </motion.h4>
                  <motion.p 
                    className="text-xs text-slate-600 mb-3 leading-relaxed"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                  >
                    We've securely saved your {formType} progress from a previous session
                  </motion.p>
                  
                  {/* Enhanced timestamp with premium styling */}
                  {lastSavedAt && (
                    <motion.div 
                      className="flex items-center text-xs text-slate-500 mb-4 px-3 py-2 bg-slate-50 rounded-lg border border-slate-100"
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 }}
                    >
                      <Clock className="h-3.5 w-3.5 mr-2 text-slate-400" />
                      <span className="font-medium">Saved {formatLastSaved(lastSavedAt)}</span>
                      <div className="ml-2 w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                    </motion.div>
                  )}
                  
                  {/* Premium action buttons with enhanced interactions */}
                  <motion.div 
                    className="flex space-x-3"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                  >
                    <motion.button
                      whileHover={!isRestoring ? { scale: 1.02, boxShadow: "0 8px 25px -8px rgba(59, 130, 246, 0.5)" } : {}}
                      whileTap={!isRestoring ? { scale: 0.98 } : {}}
                      onClick={handleRestore}
                      disabled={isRestoring}
                      className={`inline-flex items-center px-4 py-2.5 text-xs font-semibold rounded-xl transition-all ${
                        isRestoring 
                          ? 'bg-blue-400 text-white cursor-not-allowed shadow-inner'
                          : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 shadow-lg'
                      }`}
                    >
                      <motion.div
                        animate={isRestoring ? { rotate: 360 } : { rotate: 0 }}
                        transition={{ duration: 1, repeat: isRestoring ? Infinity : 0, ease: "linear" }}
                      >
                        <RotateCcw className="h-3.5 w-3.5 mr-2" />
                      </motion.div>
                      {isRestoring ? 'Restoring...' : 'Restore Progress'}
                    </motion.button>
                    
                    <motion.button
                      whileHover={{ scale: 1.02, backgroundColor: "#f8fafc" }}
                      whileTap={{ scale: 0.98 }}
                      onClick={onDismiss}
                      disabled={isRestoring}
                      className="inline-flex items-center px-4 py-2.5 bg-white text-slate-600 text-xs font-semibold rounded-xl border border-slate-200 hover:border-slate-300 transition-all shadow-sm disabled:opacity-50"
                    >
                      Start Fresh
                    </motion.button>
                  </motion.div>
                  
                  {/* Error display */}
                  {restoreError && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-3 p-2 bg-red-50 border border-red-200 rounded-lg"
                      role="alert"
                    >
                      <p className="text-xs text-red-600 font-medium">{restoreError}</p>
                    </motion.div>
                  )}
                </div>
                
                {/* Premium close button with enhanced micro-interactions */}
                <motion.button
                  whileHover={{ 
                    scale: 1.1, 
                    rotate: 90,
                    backgroundColor: "#fee2e2",
                    borderRadius: "50%" 
                  }}
                  whileTap={{ scale: 0.9 }}
                  onClick={onDismiss}
                  className="flex-shrink-0 p-2 text-slate-400 hover:text-red-500 transition-all duration-200 rounded-lg hover:bg-red-50"
                  aria-label="Close notification"
                  disabled={isRestoring}
                >
                  <X className="h-4 w-4" />
                </motion.button>
              </div>
            </div>
            
            {/* Subtle loading bar during restoration */}
            <AnimatePresence>
              {isRestoring && (
                <motion.div
                  className="absolute bottom-0 left-0 h-1 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-b-2xl"
                  initial={{ width: "0%" }}
                  animate={{ width: "100%" }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.5, ease: "easeInOut" }}
                />
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default FormRecoveryNotification;