import React from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

const ExpenseBreakdownChart = ({ expenses = [] }) => {
  // Format expenses data for chart
  const labels = expenses.map((exp) => {
    // Capitalize first letter of category
    return exp.category.charAt(0).toUpperCase() + exp.category.slice(1);
  });
  // Use total_amount for the chart data, as this represents the full expense value
  const data = expenses.map((exp) => exp.total_amount);
  const backgroundColors = [
    "#4F46E5", // indigo
    "#10B981", // emerald
    "#F59E0B", // amber
    "#EF4444", // red
    "#6366F1", // violet
    "#0EA5E9", // sky
    "#8B5CF6", // purple
    "#EC4899", // pink
  ];

  // Calculate percentages
  const total = data.reduce(
    (sum, amount) => sum + (Number(amount) || 0),
    0
  );
  const percentages = data.map((amount) =>
    total > 0 ? (((Number(amount) || 0) / total) * 100).toFixed(1) : "0.0"
  );

  // Create labels with percentages
  const labelsWithPercentages = labels.map(
    (label, i) => `${label} ${percentages[i]}%`
  );

  const chartData = {
    labels: labelsWithPercentages,
    datasets: [
      {
        data,
        backgroundColor: backgroundColors,
        borderColor: backgroundColors, // Or a slightly darker version for borders
        borderWidth: 1,
        hoverOffset: 8, // Increased for better visual feedback
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "60%",
    plugins: {
      legend: {
        position: "right",
        align: "center", // 'center' is often better for vertical legends
        labels: {
          usePointStyle: true,
          padding: 20, // Increased padding
          boxWidth: 10, // Slightly larger box
          font: {
            size: 12, // Slightly larger font
            family: "'Inter', sans-serif", // Consistent font
          },
          color: "#4B5563", // Tailwind gray-600 for text
        },
      },
      tooltip: {
        enabled: true,
        backgroundColor: "rgba(0,0,0,0.7)",
        titleFont: { size: 14, family: "'Inter', sans-serif" },
        bodyFont: { size: 12, family: "'Inter', sans-serif" },
        padding: 10,
        cornerRadius: 4,
        displayColors: false, // Hide color box in tooltip if legend is clear
        callbacks: {
          label: (context) => {
            const categoryLabel =
              context.chart.data.labels[context.dataIndex].split(" ")[0];
            const value = context.raw;
            return `${categoryLabel}: $${Number(value).toLocaleString(
              undefined,
              { minimumFractionDigits: 2, maximumFractionDigits: 2 }
            )}`;
          },
        },
      },
      // Explicitly disable any center text plugin if not used intentionally
      doughnutlabel: false,
      centerText: false,
    },
    animation: {
      animateScale: true,
      animateRotate: true,
    },
  };

  if (!expenses || expenses.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center h-full min-h-[240px]">
        <svg
          aria-hidden="true"
          className="w-12 h-12 text-gray-400 mb-3"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth="1"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
          />
        </svg>
        <h3 className="text-md font-semibold text-gray-700">No Expense Data</h3>
        <p className="text-sm text-gray-500 mt-1">
          Add some expenses to see a breakdown here.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col justify-center p-2">
      <div className="relative w-full" style={{ height: "260px" }}>
        {" "}
        {/* Adjusted height */}
        <Doughnut data={chartData} options={options} />
      </div>
    </div>
  );
};

export default ExpenseBreakdownChart;
