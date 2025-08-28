import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import ProductionErrorBoundary from "./components/ProductionErrorBoundary";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  console.error("Root element not found!");
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
