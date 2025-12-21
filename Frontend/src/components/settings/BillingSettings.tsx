/**
 * Billing Settings Component
 * Manages subscription status, plan upgrades, and payment method updates
 */

import React, { useState, useEffect } from 'react';
import * as Sentry from '@sentry/react';
import { useQuery } from '@tanstack/react-query';
import { Users, TrendingUp, CreditCard } from 'lucide-react';
import {
  getSubscriptionStatus,
  getSubscriptionPlans,
  createCheckoutSession,
  createCustomerPortalSession,
} from '../../utils/api/billing';
import * as tenantPortalSeatsAPI from '../../utils/api/tenantPortalSeats';
import SeatSubscriptionModal from '../tenants/SeatSubscriptionModal';
import type {
  SubscriptionStatus,
  SubscriptionPlan,
} from '../../types/billing';

const BillingSettings: React.FC = () => {
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [seatModalOpen, setSeatModalOpen] = useState(false);

  // Fetch seat availability
  const {
    data: seatAvailability,
    isLoading: seatsLoading,
    error: seatsError,
  } = useQuery({
    queryKey: ['tenantPortalSeats', 'availability'],
    queryFn: tenantPortalSeatsAPI.getSeatAvailability,
    refetchOnWindowFocus: false,
  });

  // Fetch subscription status and available plans
  useEffect(() => {
    const fetchBillingData = async () => {
      try {
        setLoading(true);
        
        const [statusData, plansData] = await Promise.all([
          getSubscriptionStatus(),
          getSubscriptionPlans(),
        ]);
        
        setSubscriptionStatus(statusData);
        setPlans(plansData);
        setError(null);
        
        Sentry.startSpan(
          {
            op: 'billing.load',
            name: 'Load Billing Settings',
          },
          () => {
            Sentry.logger.info('Billing settings loaded', {
              hasSubscription: statusData.has_active_subscription,
              status: statusData.subscription_status,
            });
          }
        );
      } catch (err) {
        console.error('Failed to load billing data:', err);
        setError('Failed to load billing information. Please try again.');
        
        Sentry.captureException(err, {
          tags: {
            component: 'BillingSettings',
            action: 'fetch_billing_data',
          },
        });
      } finally {
        setLoading(false);
      }
    };

    fetchBillingData();
  }, []);

  // Handle subscription upgrade/purchase
  const handleSubscribe = async (priceId: string) => {
    try {
      setActionLoading(true);
      setError(null);

      const { checkout_url } = await createCheckoutSession({
        price_id: priceId,
        success_url: `${window.location.origin}/settings?tab=billing&success=true`,
        cancel_url: `${window.location.origin}/settings?tab=billing&canceled=true`,
      });

      // Redirect to Stripe Checkout
      window.location.href = checkout_url;
    } catch (err: any) {
      console.error('Failed to create checkout session:', err);
      
      // Handle duplicate subscription error
      const errorMessage = err?.message || 'Failed to start checkout. Please try again.';
      if (errorMessage.includes('already have an active subscription')) {
        setError('You already have an active subscription. Refresh the page to see your current plan.');
      } else {
        setError(errorMessage);
      }
      
      setActionLoading(false);
      
      Sentry.captureException(err, {
        tags: {
          component: 'BillingSettings',
          action: 'create_checkout_session',
          duplicate_subscription: errorMessage.includes('already have an active subscription'),
        },
      });
    }
  };

  // Handle manage subscription (payment methods, invoices, cancel)
  const handleManageSubscription = async () => {
    try {
      setActionLoading(true);
      setError(null);

      const { portal_url } = await createCustomerPortalSession();

      // Redirect to Stripe Customer Portal
      window.location.href = portal_url;
    } catch (err) {
      console.error('Failed to create customer portal session:', err);
      setError('Failed to open billing portal. Please try again.');
      setActionLoading(false);
      
      Sentry.captureException(err, {
        tags: {
          component: 'BillingSettings',
          action: 'create_portal_session',
        },
      });
    }
  };


  // Format currency
  const formatCurrency = (amount: number, currency: string): string => {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: currency.toUpperCase(),
    }).format(amount);
  };

  // Format date
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-CA', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Get status badge color
  const getStatusBadgeColor = (status: string): string => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'trialing':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'past_due':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'canceled':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
      default:
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
          <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded mb-4"></div>
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Billing & Subscription
        </h2>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Manage your subscription, payment methods, and billing history
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <i className="fas fa-exclamation-circle text-red-400"></i>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
            </div>
            <div className="ml-auto pl-3">
              <button
                onClick={() => setError(null)}
                className="inline-flex text-red-400 hover:text-red-500"
              >
                <i className="fas fa-times"></i>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Current Subscription Status */}
      {subscriptionStatus && (
        <div className="dark-panel dark-shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Current Subscription
            </h3>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusBadgeColor(subscriptionStatus.subscription_status)}`}>
              {subscriptionStatus.subscription_status.charAt(0).toUpperCase() + subscriptionStatus.subscription_status.slice(1)}
            </span>
          </div>

          <div className="space-y-4">
            {/* Subscription Details */}
            {subscriptionStatus.has_active_subscription ? (
              <>
                {subscriptionStatus.subscription_details && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">Plan</p>
                      <p className="text-lg font-medium text-gray-900 dark:text-white">
                        {subscriptionStatus.subscription_details.name}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">Price</p>
                      <p className="text-lg font-medium text-gray-900 dark:text-white">
                        {subscriptionStatus.subscription_details.amount && subscriptionStatus.subscription_details.currency
                          ? `${formatCurrency(subscriptionStatus.subscription_details.amount, subscriptionStatus.subscription_details.currency)}/${subscriptionStatus.subscription_details.interval}`
                          : 'N/A'}
                      </p>
                    </div>
                  </div>
                )}

                {subscriptionStatus.current_period_end && (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {subscriptionStatus.cancel_at_period_end ? 'Cancels on' : 'Renews on'}
                    </p>
                    <p className="text-base font-medium text-gray-900 dark:text-white">
                      {formatDate(subscriptionStatus.current_period_end)}
                    </p>
                  </div>
                )}

                {/* Trial Information */}
                {subscriptionStatus.trial_active && subscriptionStatus.trial_days_remaining !== undefined && (
                  <div className="rounded-md bg-blue-50 dark:bg-blue-900/20 p-4">
                    <div className="flex">
                      <div className="flex-shrink-0">
                        <i className="fas fa-clock text-blue-400"></i>
                      </div>
                      <div className="ml-3">
                        <p className="text-sm text-blue-800 dark:text-blue-300">
                          Trial period: {subscriptionStatus.trial_days_remaining} days remaining
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex flex-wrap gap-3 pt-4">
                  <button
                    onClick={handleManageSubscription}
                    disabled={actionLoading}
                    className="px-6 py-2.5 bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 rounded-full font-medium transition-all duration-200 shadow-sm hover:shadow-md flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <i className="fas fa-cog mr-2"></i>
                    Manage Subscription
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center py-6">
                <i className="fas fa-shopping-cart text-4xl text-gray-400 mb-4"></i>
                <p className="text-gray-600 dark:text-gray-400 mb-2">
                  You don't have an active subscription
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-500 mb-4">
                  Subscribe to unlock full access to Brikli
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Available Plans */}
      {!subscriptionStatus?.has_active_subscription && plans.length > 0 && (
        <div className="dark-panel dark-shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Available Plans
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className="border border-gray-200 dark:border-gray-700 rounded-lg p-6 hover:border-green-500 dark:hover:border-green-500 transition-colors"
              >
                <div className="mb-4">
                  <h4 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                    {plan.name}
                  </h4>
                  {plan.description && (
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {plan.description}
                    </p>
                  )}
                </div>

                <div className="mb-4">
                  <span className="text-3xl font-bold text-gray-900 dark:text-white">
                    {formatCurrency(plan.amount, plan.currency)}
                  </span>
                  <span className="text-gray-600 dark:text-gray-400">
                    /{plan.interval}
                  </span>
                </div>

                {plan.trial_period_days > 0 && (
                  <div className="mb-4 flex items-center text-sm text-green-600 dark:text-green-400">
                    <i className="fas fa-gift mr-2"></i>
                    <span>{plan.trial_period_days}-day free trial</span>
                  </div>
                )}

                {plan.features.length > 0 && (
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((feature, index) => (
                      <li key={index} className="flex items-start text-sm text-gray-600 dark:text-gray-400">
                        <i className="fas fa-check text-green-500 mr-2 mt-0.5"></i>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                )}

                <button
                  onClick={() => handleSubscribe(plan.stripe_price_id)}
                  disabled={actionLoading}
                  className="w-full px-6 py-3 bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 rounded-full font-medium transition-all duration-200 shadow-sm hover:shadow-md flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {actionLoading ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i>
                      Processing...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-arrow-right mr-2"></i>
                      Subscribe Now
                    </>
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tenant Portal Seats Section */}
      {subscriptionStatus?.has_active_subscription && (
        <div className="dark-panel dark-shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Users className="w-5 h-5" />
                Tenant Portal Seats
              </h3>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Manage your tenant portal seat capacity
              </p>
            </div>
          </div>

          {seatsLoading ? (
            <div className="animate-pulse space-y-3">
              <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
              <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
            </div>
          ) : seatsError ? (
            <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
              <p className="text-sm text-red-800 dark:text-red-300">
                Failed to load seat information. Please try again later.
              </p>
            </div>
          ) : seatAvailability ? (
            <>
              {/* Seat Usage Overview */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-700 rounded-xl p-4 mb-4">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Current Usage
                  </h4>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                      {seatAvailability.limit}
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 mt-1 font-medium">
                      Total Seats
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-gray-700 dark:text-gray-300">
                      {seatAvailability.used}
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 mt-1 font-medium">
                      In Use
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {seatAvailability.available}
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 mt-1 font-medium">
                      Available
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-blue-200 dark:border-blue-700">
                  <p className="text-xs text-gray-600 dark:text-gray-400 text-center">
                    Includes{' '}
                    <span className="font-semibold text-blue-600 dark:text-blue-400">
                      {seatAvailability.free_seats} free seats
                    </span>{' '}
                    with your Brikli Premium subscription
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => setSeatModalOpen(true)}
                  className="px-6 py-2.5 bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 rounded-full font-medium transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2"
                >
                  <CreditCard className="w-4 h-4" />
                  Add More Seats
                </button>

                {seatAvailability.purchased_seats > 0 && (
                  <button
                    onClick={handleManageSubscription}
                    disabled={actionLoading}
                    className="px-6 py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-full font-medium transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <i className="fas fa-cog"></i>
                    Manage Seat Subscription
                  </button>
                )}
              </div>

              {/* Info Box */}
              <div className="mt-4 rounded-md bg-blue-50 dark:bg-blue-900/20 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <i className="fas fa-info-circle text-blue-400"></i>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-blue-800 dark:text-blue-300">
                      <strong>How seats work:</strong> Each tenant portal seat allows one tenant to access their portal.
                      Additional seats cost $3/month each and can be canceled anytime.
                    </p>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* Billing Information Footer */}
      <div className="dark-panel dark-shadow rounded-lg p-6">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <i className="fas fa-info-circle text-blue-500 text-xl"></i>
          </div>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
              Billing Information
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              All payments are processed securely through Stripe. Your subscription will automatically renew unless canceled.
              You can cancel anytime and retain access until the end of your billing period.
            </p>
          </div>
        </div>
      </div>

      {/* Seat Subscription Modal */}
      <SeatSubscriptionModal
        isOpen={seatModalOpen}
        onClose={() => setSeatModalOpen(false)}
        requiredSeats={1}
      />
    </div>
  );
};

export default BillingSettings;

