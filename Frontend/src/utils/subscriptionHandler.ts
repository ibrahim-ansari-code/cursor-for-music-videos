/**
 * Global Subscription Error Handler
 * Provides a singleton for handling 402 errors globally
 */

type SubscriptionModalCallback = (featureName?: string) => void;

class SubscriptionHandler {
  private showModalCallback: SubscriptionModalCallback | null = null;

  /**
   * Register the callback to show the subscription modal
   * Called by SubscriptionProvider on mount
   */
  setShowModalCallback(callback: SubscriptionModalCallback) {
    this.showModalCallback = callback;
  }

  /**
   * Trigger the subscription modal
   * Called by API client when 402 error is detected
   */
  showModal(featureName?: string) {
    if (this.showModalCallback) {
      this.showModalCallback(featureName);
    } else {
      console.warn('Subscription modal callback not registered');
      // Fallback: redirect to billing page
      window.location.href = '/settings?tab=billing';
    }
  }
}

// Export singleton instance
export const subscriptionHandler = new SubscriptionHandler();

