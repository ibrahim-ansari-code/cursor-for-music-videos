import "./sentry-init";
import React from "react";
import ReactDOM from "react-dom/client";
import { reportFatalError } from './utils/error-reporting';
import App from "./App.jsx";
import { GoogleReCaptchaProvider } from 'react-google-recaptcha-v3';
import ProductionErrorBoundary from "./components/ProductionErrorBoundary";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  const error = new Error("Root DOM element not found - React cannot mount");
  console.error("Root element not found!");
  
  // Report critical DOM mounting errors 
  reportFatalError(error, {
    component: 'index',
    action: 'dom_mount',
    tags: {
      critical: true,
    },
    extra: {
      dom: {
        querySelector: 'root',
        documentReady: document.readyState,
      }
    },
  });
} else {
  const root = ReactDOM.createRoot(rootElement);
  const siteKey = import.meta.env.VITE_RECAPTCHA_SITE_KEY;
  if (!siteKey && import.meta.env.MODE === 'production') {
    console.error('VITE_RECAPTCHA_SITE_KEY is missing in production build. reCAPTCHA headers will be omitted.');
  }
  root.render(
    <React.StrictMode>
      <ProductionErrorBoundary>
        {siteKey ? (
          <GoogleReCaptchaProvider
            reCaptchaKey={siteKey}
            scriptProps={{ async: true, defer: true }}
          >
            <App />
          </GoogleReCaptchaProvider>
        ) : (
          <App />
        )}
      </ProductionErrorBoundary>
    </React.StrictMode>
  );
}
