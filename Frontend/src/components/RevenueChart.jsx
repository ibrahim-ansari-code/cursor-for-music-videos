import React, { useRef, useEffect } from "react";
import Chart from "chart.js/auto";

const RevenueChart = ({ data }) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    // If no data or chart already exists, return
    if (!data || !data.months || !chartRef.current) return;

    // Destroy previous chart if it exists
    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = chartRef.current.getContext("2d");

    // Trim data arrays to include only months since first financial activity
    const trimmedData = trimFinancialData(data);

    // Prepare data
    const labels = trimmedData.months;
    const revenueData = trimmedData.revenue;
    const expensesData = trimmedData.expenses;
    const netIncomeData = trimmedData.net_income;

    // Create chart
    chartInstance.current = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Income",
            data: revenueData,
            backgroundColor: "#1a73e8", // blue
            borderColor: "#1a73e8",
            borderWidth: 0,
            borderRadius: 4,
            order: 2,
          },
          {
            label: "Expenses",
            data: expensesData,
            backgroundColor: "#e94235", // red
            borderColor: "#e94235",
            borderWidth: 0,
            borderRadius: 4,
            order: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              drawBorder: false,
              borderDash: [5, 5],
              color: "#f0f0f0",
            },
            ticks: {
              callback: function (value) {
                if (value >= 1000) {
                  return "$" + value / 1000 + "k";
                }
                return "$" + value;
              },
              font: {
                size: 11,
              },
              color: "#999",
            },
          },
          x: {
            grid: {
              display: false,
              drawBorder: false,
            },
            ticks: {
              font: {
                size: 11,
              },
              color: "#999",
            },
          },
        },
        plugins: {
          legend: {
            display: true,
            position: "top",
            align: "end",
            labels: {
              usePointStyle: true,
              boxWidth: 8,
              pointStyle: "circle",
              padding: 20,
              font: {
                size: 12,
              },
            },
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                let label = context.dataset.label || "";
                if (label) {
                  label += ": ";
                }
                if (context.parsed.y !== null) {
                  label += "$" + context.parsed.y.toLocaleString();
                }
                return label;
              },
            },
          },
          title: {
            display: false,
          },
        },
        interaction: {
          mode: "index",
          intersect: false,
        },
        barPercentage: 0.6,
        categoryPercentage: 0.7,
        layout: {
          padding: {
            top: 0,
            right: 0,
            bottom: 16,
            left: 0,
          },
        },
      },
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [data]);

  // Function to trim data arrays to include only months since first financial activity
  const trimFinancialData = (data) => {
    // Make copies of the arrays
    const months = [...data.months];
    const revenue = [...data.revenue];
    const expenses = [...data.expenses];
    const netIncome = [...data.net_income];

    // Find the first month with any financial activity
    let firstActivityIndex = -1;
    for (let i = 0; i < revenue.length; i++) {
      if (revenue[i] > 0 || expenses[i] > 0) {
        firstActivityIndex = i;
        break;
      }
    }

    // If no activity found, or already starts with activity, return original data
    if (firstActivityIndex <= 0) {
      return data;
    }

    // Trim arrays to start from the first activity month
    return {
      months: months.slice(firstActivityIndex),
      revenue: revenue.slice(firstActivityIndex),
      expenses: expenses.slice(firstActivityIndex),
      net_income: netIncome.slice(firstActivityIndex),
    };
  };

  return (
    <div className="flex-1 flex flex-col justify-center">
      <div className="h-64">
        <canvas ref={chartRef}></canvas>
      </div>
    </div>
  );
};

export default RevenueChart;
