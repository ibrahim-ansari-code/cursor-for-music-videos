import React, { useState, useEffect } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation } from "@tanstack/react-query";
import * as Sentry from "@sentry/react";
import { X, CreditCard, Users, TrendingUp, AlertCircle } from "lucide-react";
import * as tenantPortalSeatsAPI from "../../utils/api/tenantPortalSeats";

interface SeatSubscriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  requiredSeats?: number; // If provided, shows recommended quantity
}

const SEAT_PRICE = 3.0; // $3/seat/month

const SeatSubscriptionModal: React.FC<SeatSubscriptionModalProps> = ({
  isOpen,
  onClose,
  requiredSeats = 1,
}) => {
  const [quantity, setQuantity] = useState(requiredSeats);

  // Reset quantity when modal opens with new requiredSeats
  useEffect(() => {
    if (isOpen) {
      setQuantity(requiredSeats);
    }
  }, [isOpen, requiredSeats]);

  // Fetch current seat availability
  const {
    data: availability,
    isLoading: isLoadingAvailability,
    error: availabilityError,
  } = useQuery({
    queryKey: ["tenantPortalSeats", "availability"],
    queryFn: tenantPortalSeatsAPI.getSeatAvailability,
    enabled: isOpen,
    refetchOnWindowFocus: false,
  });

  // Subscribe mutation
  const subscribeMutation = useMutation({
    mutationFn: (qty: number) =>
      Sentry.startSpan(
        { op: "http.client", name: "Subscribe to Tenant Portal Seats" },
        () =>
          tenantPortalSeatsAPI.subscribeToSeats({
            quantity: qty,
            success_url: `${window.location.origin}/tenants?seat_subscription=success`,
            cancel_url: `${window.location.origin}/tenants?seat_subscription=cancelled`,
          })
      ),
    onSuccess: (data) => {
      Sentry.logger.info("Redirecting to seat subscription checkout", {
        quantity,
        checkoutSessionId: data.session_id,
      });

      // Redirect to Stripe Checkout
      window.location.href = data.checkout_url;
    },
    onError: (error) => {
      Sentry.captureException(error, {
        tags: {
          component: "SeatSubscriptionModal",
          action: "seat_subscription",
        },
      });
    },
  });

  const handleSubscribe = () => {
    if (quantity < 1 || quantity > 100) {
      Sentry.logger.warn("Invalid seat quantity", { quantity });
      return;
    }
    subscribeMutation.mutate(quantity);
  };

  const handleQuantityChange = (value: string) => {
    const parsed = parseInt(value) || 1;
    setQuantity(Math.max(1, Math.min(100, parsed)));
  };

  const monthlyTotal = quantity * SEAT_PRICE;
  const isLoading = isLoadingAvailability || subscribeMutation.isPending;

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <AnimatePresence>
        {isOpen && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              />
            </Dialog.Overlay>

            <Dialog.Content asChild>
              <motion.div
                className="fixed inset-0 flex items-center justify-center p-4 z-[60]"
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                transition={{ type: "spring", duration: 0.5 }}
              >
                <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[85vh] flex flex-col">
                {/* Header */}
                <div className="bg-gradient-to-br from-blue-600 to-blue-700 px-4 py-3 flex-shrink-0 rounded-t-2xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="bg-white/20 p-1.5 rounded-lg">
                        <Users className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <Dialog.Title className="text-lg font-bold text-white">
                          Add Tenant Portal Seats
                        </Dialog.Title>
                        <p className="text-blue-100 text-xs">
                          Expand your tenant portal capacity
                        </p>
                      </div>
                    </div>
                    <Dialog.Close asChild>
                      <button
                        className="text-white/80 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/10"
                        disabled={subscribeMutation.isPending}
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </Dialog.Close>
                  </div>
                </div>

                {/* Content */}
                <div className="p-4 space-y-4 flex-1 overflow-y-auto">
                  {/* Error Alert */}
                  {availabilityError && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-red-800">
                          Failed to load seat availability
                        </p>
                        <p className="text-xs text-red-600 mt-1">
                          Please try again or contact support if the problem persists.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Current Seat Status */}
                  {availability && (
                    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-700 rounded-xl p-4">
                      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                        <TrendingUp className="w-4 h-4" />
                        Current Usage
                      </h3>
                      <div className="grid grid-cols-3 gap-3">
                        <div className="text-center">
                          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                            {availability.limit}
                          </div>
                          <div className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 font-medium">
                            Current Limit
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-gray-700 dark:text-gray-300">
                            {availability.used}
                          </div>
                          <div className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 font-medium">
                            In Use
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                            {availability.available}
                          </div>
                          <div className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 font-medium">
                            Available
                          </div>
                        </div>
                      </div>
                      <div className="mt-3 pt-3 border-t border-blue-200 dark:border-blue-700">
                        <p className="text-xs text-gray-600 dark:text-gray-400 text-center">
                          Includes{" "}
                          <span className="font-semibold text-blue-600 dark:text-blue-400">
                            {availability.free_seats} free seats
                          </span>{" "}
                          with your Brikli Premium subscription
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Quantity Selector */}
                  <div>
                    <label
                      htmlFor="seat-quantity"
                      className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2"
                    >
                      Number of seats to add
                    </label>
                    <input
                      id="seat-quantity"
                      type="number"
                      min="1"
                      max="100"
                      value={quantity}
                      onChange={(e) => handleQuantityChange(e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all text-lg font-semibold text-center"
                      disabled={isLoading}
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
                      ${SEAT_PRICE.toFixed(2)} per seat per month • Maximum 100
                      seats
                    </p>
                  </div>

                  {/* Pricing Summary */}
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 border border-gray-200 dark:border-gray-600">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                        Monthly Cost:
                      </span>
                      <div className="text-right">
                        <span className="text-xl font-bold text-gray-900 dark:text-white">
                          ${monthlyTotal.toFixed(2)}
                        </span>
                        <span className="text-gray-500 dark:text-gray-400 text-sm ml-1">/mo</span>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                      {quantity} seat{quantity !== 1 ? "s" : ""} ×{" "}
                      ${SEAT_PRICE.toFixed(2)}/month
                    </div>
                    <div className="pt-2 border-t border-gray-200 dark:border-gray-600">
                      <p className="text-xs text-blue-600 dark:text-blue-400 font-medium flex items-center gap-2">
                        <CreditCard className="w-4 h-4" />
                        Cancel anytime. No long-term commitment.
                      </p>
                    </div>
                  </div>

                  {/* Info Box */}
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-lg p-4">
                    <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                      <strong className="text-blue-700 dark:text-blue-400">How it works:</strong>{" "}
                      Each seat allows one tenant to access the Tenant Portal.
                      You can invite multiple tenants, and they'll be assigned
                      seats when they accept your invitation. Unused seats
                      remain available for future invitations.
                    </p>
                  </div>
                </div>

                {/* Footer */}
                <div className="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 flex justify-end gap-3 border-t border-gray-200 dark:border-gray-600 flex-shrink-0 rounded-b-2xl">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-white dark:hover:bg-gray-700 transition-colors font-medium text-gray-700 dark:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    disabled={subscribeMutation.isPending}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSubscribe}
                    disabled={
                      isLoading ||
                      quantity < 1 ||
                      quantity > 100 ||
                      !!availabilityError
                    }
                    className="px-5 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all font-semibold shadow-lg shadow-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none flex items-center gap-2 text-sm"
                  >
                    {subscribeMutation.isPending ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <CreditCard className="w-4 h-4" />
                        Subscribe Now
                      </>
                    )}
                  </button>
                </div>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
};

export default SeatSubscriptionModal;
