import React from "react";
import { TrendingUp } from "lucide-react";

// Move translations to module level to prevent recreation on each render
const translations = {
  "reports.title": "Coming Soon",
  "reports.description":
    "We're working on building a comprehensive reporting system to help you gain insights into your property portfolio performance.",
  "reports.availability":
    "This feature will be available in the near future. Stay tuned!",
};

// Placeholder for future i18n implementation
const t = (key) => {
  return translations[key] || key;
};

const Reports = () => {
  return (
    <main className="text-center py-16 px-4">
      <div className="bg-white rounded-lg shadow-sm p-10 max-w-lg mx-auto">
        <div className="text-blue-600 text-6xl mb-6">
          <TrendingUp size={64} className="mx-auto" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-semibold text-gray-800 mb-4">
          {t("reports.title")}
        </h1>
        <div className="text-gray-600">
          <p>{t("reports.description")}</p>
          <p className="mt-4">{t("reports.availability")}</p>
        </div>
      </div>
    </main>
  );
};

export default Reports;

/* FUTURE IMPLEMENTATION - UNCOMMENT WHEN READY

import React, { useState, useEffect } from "react";
import {
  ChevronDown,
  FileSpreadsheet,
  FileText,
  Mail,
  Loader2,
  TrendingUp,
  Download,
  X,
} from "lucide-react";
import { fetchReportSummary, fetchProperties } from "../utils/api";
import { toast } from "react-toastify";

// Placeholder components for charts (replace with actual chart components later if needed)
const MonthlyRevenueChart = ({ data }) => {
  // Basic rendering, replace with Recharts later
  return (
    <div className="monthly-revenue-chart h-72 w-full relative border border-gray-200 rounded p-4">
      <div className="absolute top-2 right-2 flex items-center gap-4">
        <div className="flex items-center">
          <div className="w-3 h-3 bg-blue-500 rounded-sm mr-1.5"></div>
          <span className="text-xs text-gray-600">Rental Income</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 bg-green-400 rounded-sm mr-1.5"></div>
          <span className="text-xs text-gray-600">Other Income</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 bg-red-500 rounded-sm mr-1.5"></div>
          <span className="text-xs text-gray-600">Expenses</span>
        </div>
      </div>
      {data ? (
        <div className="mt-8">
          <p className="text-sm text-gray-500">Chart data available:</p>
          <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-48">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      ) : (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-500">Generate report to view chart.</p>
        </div>
      )}
    </div>
  );
};

const ReportsImplementation = () => {
  // State for form controls
  const [reportType, setReportType] = useState("Financial Summary");
  const [dateRange, setDateRange] = useState("Current Month");
  const [selectedProperties, setSelectedProperties] = useState([]);
  const [availableProperties, setAvailableProperties] = useState([]);
  const [activeTab, setActiveTab] = useState("Monthly");
  const [isGenerating, setIsGenerating] = useState(false);
  const [showPropertyDropdown, setShowPropertyDropdown] = useState(false);

  // State for report data
  const [reportData, setReportData] = useState(null);
  const [error, setError] = useState(null);

  // Fetch available properties on component mount
  useEffect(() => {
    const loadProperties = async () => {
      try {
        const properties = await fetchProperties();
        setAvailableProperties(properties);
      } catch (err) {
        console.error("Error fetching properties:", err);
        toast.error("Failed to load properties for filtering.");
      }
    };
    loadProperties();
  }, []);

  // Handler for generating reports
  const handleGenerateReport = async () => {
    setIsGenerating(true);
    setError(null);
    setReportData(null); // Clear previous data

    try {
      const propertyIds = selectedProperties.map((p) => p.id);
      const params = {
        report_type: reportType,
        date_range: dateRange,
        property_ids: propertyIds,
      };

      const data = await fetchReportSummary(params);
      setReportData(data);
      toast.success("Report generated successfully!");
    } catch (err) {
      console.error("Error generating report:", err);
      setError(err.message || "Failed to generate report. Please try again.");
      toast.error(err.message || "Failed to generate report.");
    } finally {
      setIsGenerating(false);
    }
  };

  // Toggle property selection
  const togglePropertySelection = (property) => {
    setSelectedProperties((prev) =>
      prev.some((p) => p.id === property.id)
        ? prev.filter((p) => p.id !== property.id)
        : [...prev, property]
    );
  };

  // Check if a property is selected
  const isPropertySelected = (propertyId) => {
    return selectedProperties.some((p) => p.id === propertyId);
  };

  return (
    <div className="flex flex-col space-y-6">
      <div className="flex justify-end">
        <div className="flex gap-2">
          <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-teal">
            <FileSpreadsheet className="mr-2 h-4 w-4" />
            Export to Excel
          </button>
          <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-teal">
            <FileText className="mr-2 h-4 w-4" />
            Export to PDF
          </button>
          <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-teal">
            <Mail className="mr-2 h-4 w-4" />
            Email Report
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
        <div className="col-span-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Report Type
          </label>
          <div className="relative">
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="bg-white border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-brand-teal focus:border-brand-teal block w-full p-2.5 pr-8 appearance-none"
            >
              <option value="Financial Summary">Financial Summary</option> 
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
              <ChevronDown className="h-4 w-4" />
            </div>
          </div>
        </div>

        <div className="col-span-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Date Range
          </label>
          <div className="relative">
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="bg-white border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-brand-teal focus:border-brand-teal block w-full p-2.5 pr-8 appearance-none"
            >
              <option value="Current Month">Current Month</option>
              <option value="Last Month">Last Month</option>
              <option value="Last Quarter">Last Quarter</option>
              <option value="Year to Date">Year to Date</option>
              <option value="Last Year">Last Year</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
              <ChevronDown className="h-4 w-4" />
            </div>
          </div>
        </div>

        <div className="col-span-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Property
          </label>
          <div className="relative">
            <button
              onClick={() => setShowPropertyDropdown(!showPropertyDropdown)}
              className="bg-white border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-brand-teal focus:border-brand-teal block w-full p-2.5 text-left flex justify-between items-center"
            >
              <span>
                {selectedProperties.length === 0
                  ? "Select properties (optional)"
                  : selectedProperties.length === 1
                  ? selectedProperties[0].name
                  : `${selectedProperties.length} properties selected`}
              </span>
              <ChevronDown
                className={`h-4 w-4 transform transition-transform ${
                  showPropertyDropdown ? "rotate-180" : ""
                }`}
              />
            </button>

            {showPropertyDropdown && (
              <div className="absolute z-10 mt-1 w-full bg-white shadow-lg rounded-lg border border-gray-200 max-h-60 overflow-auto">
                <div className="p-2">
                  <input
                    type="text"
                    placeholder="Search properties..."
                    className="w-full px-2 py-1 border border-gray-300 rounded mb-2"
                    // Add search functionality if needed
                  />
                </div>
                {availableProperties.length > 0 ? (
                  availableProperties.map((property) => (
                    <div
                      key={property.id}
                      onClick={() => togglePropertySelection(property)}
                      className={`px-4 py-2 cursor-pointer hover:bg-gray-100 flex items-center ${
                        isPropertySelected(property.id) ? "bg-teal-50" : ""
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isPropertySelected(property.id)}
                        readOnly
                        className="mr-2 form-checkbox h-4 w-4 text-brand-teal border-gray-300 rounded focus:ring-brand-teal"
                      />
                      {property.name}
                    </div>
                  ))
                ) : (
                  <div className="px-4 py-2 text-gray-500">
                    No properties found.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="col-span-1">
          <button
            onClick={handleGenerateReport}
            disabled={isGenerating}
            className="w-full bg-brand-teal hover:bg-teal-600 text-white px-4 py-2.5 rounded-lg flex items-center justify-center"
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Generating...
              </>
            ) : (
              "Generate Report"
            )}
          </button>
        </div>
      </div>

      {selectedProperties.length > 0 && (
        <div className="flex flex-wrap gap-2 -mt-2">
          {selectedProperties.map((property) => (
            <div
              key={property.id}
              className="inline-flex items-center bg-gray-100 text-sm px-2 py-1 rounded"
            >
              {property.name}
              <button
                onClick={() => togglePropertySelection(property)}
                className="ml-1 text-gray-500 hover:text-gray-700"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6">
            <h2 className="text-lg font-medium mb-4">
              Monthly Revenue Overview
            </h2>

            <div className="inline-flex rounded-md bg-gray-200 p-1 mb-6">
              <button
                className={`px-4 py-1.5 text-sm font-medium rounded-md bg-white text-gray-900 shadow`}
              >
                {dateRange} 
              </button>
            </div>

            <MonthlyRevenueChart data={reportData?.monthly_chart} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <h2 className="text-lg font-medium mb-6">
              Financial Highlights ({dateRange})
            </h2>

            <div className="flex flex-col items-center space-y-6">
              <div className="grid grid-cols-2 gap-6 w-full">
                <div className="flex flex-col items-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500 mb-1">Total Revenue</p>
                  <p className="text-2xl font-bold">
                    {reportData
                      ? `$${reportData.summary.total_monthly_revenue.toFixed(
                          2
                        )}`
                      : "$0.00"}
                  </p>
                </div>

                <div className="flex flex-col items-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500 mb-1">Average Rent</p>
                  <p className="text-2xl font-bold">
                    {reportData
                      ? `$${reportData.summary.avg_rent.toFixed(2)}`
                      : "$0.00"}
                  </p>
                </div>

                <div className="flex flex-col items-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500 mb-1">Occupancy Rate</p>
                  <p className="text-2xl font-bold">
                    {reportData && reportData.summary.occupancy_rate
                      ? `${reportData.summary.occupancy_rate.toFixed(1)}%`
                      : "0.0%"}
                  </p>
                </div>

                <div className="flex flex-col items-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500 mb-1">Revenue/Unit</p>
                  <p className="text-2xl font-bold">
                    {reportData && reportData.summary.revenue_per_unit
                      ? `$${reportData.summary.revenue_per_unit.toFixed(2)}`
                      : "$0.00"}
                  </p>
                </div>
              </div>

              {reportData && reportData.summary.period_comparison && (
                <div className="border-t border-gray-200 pt-4 w-full">
                  <h3 className="text-sm font-medium text-gray-700 mb-3 text-center">
                    Period Comparison
                  </h3>
                  <div className="flex justify-around">
                    <div className="flex flex-col items-center">
                      <p className="text-xs text-gray-500">Revenue Change</p>
                      <div className="flex items-center mt-1">
                        <span
                          className={`text-base font-medium ${
                            (reportData.summary.period_comparison
                              .revenue_change || 0) >= 0
                              ? "text-green-600"
                              : "text-red-600"
                          }`}
                        >
                          {(reportData.summary.period_comparison
                            .revenue_change || 0) >= 0
                            ? "+"
                            : ""}
                          {reportData.summary.period_comparison.revenue_change
                            ? reportData.summary.period_comparison.revenue_change.toFixed(
                                1
                              )
                            : "0.0"}
                          %
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col items-center">
                      <p className="text-xs text-gray-500">Occupancy Change</p>
                      <div className="flex items-center mt-1">
                        <span
                          className={`text-base font-medium ${
                            (reportData.summary.period_comparison
                              .occupancy_change || 0) >= 0
                              ? "text-green-600"
                              : "text-red-600"
                          }`}
                        >
                          {(reportData.summary.period_comparison
                            .occupancy_change || 0) >= 0
                            ? "+"
                            : ""}
                          {reportData.summary.period_comparison.occupancy_change
                            ? reportData.summary.period_comparison.occupancy_change.toFixed(
                                1
                              )
                            : "0.0"}
                          %
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {!reportData && (
                <div className="text-center text-gray-500 text-sm mt-4">
                  <p>Generate a report to see financial highlights</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-6 border-b flex justify-between items-center">
          <h2 className="text-lg font-medium">
            Financial Details ({dateRange})
          </h2>
          <button className="flex items-center text-indigo-600 hover:text-indigo-800 text-sm">
            <Download className="h-4 w-4 mr-1" />
            Export
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-100 text-gray-700">
              <tr>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider"
                >
                  Property
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider"
                >
                  Units
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider"
                >
                  Occupied
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider"
                >
                  Occ. Rate
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider"
                >
                  Revenue
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider"
                >
                  Avg Rent
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider"
                >
                  Expenses
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider"
                >
                  Net Income
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {isGenerating ? (
                <tr>
                  <td colSpan="8" className="px-6 py-8 text-center text-sm">
                    <Loader2 className="h-5 w-5 animate-spin inline mr-2" />{" "}
                    Generating data...
                  </td>
                </tr>
              ) : reportData && reportData.financial_table.length > 0 ? (
                reportData.financial_table.map((row, index) => (
                  <tr
                    key={row.property_id || index}
                    className="hover:bg-gray-50"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 text-left">
                      {row.property}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 text-right">
                      {row.units}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 text-right">
                      {row.occupied_units}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 text-right">
                      {row.occupancy_rate}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 text-right">
                      ${row.monthly_revenue.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 text-right">
                      ${row.avg_rent.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 text-right">
                      ${row.expenses.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-right ${row.net_income >= 0 ? 'text-green-600' : 'text-red-600'}">
                      ${row.net_income.toFixed(2)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan="8"
                    className="px-6 py-8 text-center text-sm text-gray-500"
                  >
                    {error
                      ? `Error: ${error}`
                      : "No data available. Select properties and generate a report."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

*/
