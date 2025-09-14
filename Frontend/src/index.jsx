import "./sentry-init";
import React from "react";
import ReactDOM from "react-dom/client";
import { reportFatalError } from './utils/error-reporting';
import App from "./App.jsx";
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
  root.render(
    <React.StrictMode>
      <ProductionErrorBoundary>
        <App />
      </ProductionErrorBoundary>
    </React.StrictMode>
  );
}
