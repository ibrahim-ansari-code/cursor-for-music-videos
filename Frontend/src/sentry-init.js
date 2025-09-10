import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration({
      // Keep text visible for better debugging in financial workflows
      maskAllText: false,
      blockAllMedia: false,
    }),
  ],
  
  // Performance Monitoring - balanced for SaaS production use
  tracesSampleRate: import.meta.env.MODE === 'development' ? 1.0 : 0.1, // 100% dev, 10% production
  
  // Session Replay - cost-effective for financial SaaS
  replaysSessionSampleRate: import.meta.env.MODE === 'development' ? 0.1 : 0.05, // 10% dev, 5% production
  replaysOnErrorSampleRate: 1.0, // Always capture error sessions (critical for financial app)
  
  // Environment detection
  environment: import.meta.env.MODE,
  
  // Release tracking (automatically set by @sentry/vite-plugin)
  
  // Enhanced error filtering for production SaaS
  beforeSend(event) {
    // Filter out noise from browser extensions and non-application errors
    if (event.exception) {
      const error = event.exception.values?.[0];
      if (error?.stacktrace?.frames) {
        const frames = error.stacktrace.frames;
        
        // Skip errors from browser extensions
        if (frames.some(frame => 
          frame.filename?.includes('chrome-extension://') ||
          frame.filename?.includes('moz-extension://') ||
          frame.filename?.includes('safari-extension://') ||
          frame.filename?.includes('extension://')
        )) {
          return null;
        }
        
        // Skip common non-actionable browser errors
        const message = error.value?.toLowerCase() || '';
        if (
          message.includes('non-error promise rejection') ||
          message.includes('script error') ||
          message.includes('network error') ||
          message.includes('loading css chunk')
        ) {
          return null;
        }
      }
    }
    
    return event;
  },
  
  // Send default PII for better context in financial workflows
  sendDefaultPii: false,
});
