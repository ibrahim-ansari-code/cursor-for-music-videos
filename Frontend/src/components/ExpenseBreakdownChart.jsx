import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const ExpenseBreakdownChart = ({ expenses = [] }) => {
  // Format expenses data for chart
  const labels = expenses.map(exp => {
    // Capitalize first letter of category
    return exp.category.charAt(0).toUpperCase() + exp.category.slice(1);
  });
  const data = expenses.map(exp => exp.amount);
  const backgroundColors = [
    '#4F46E5', // indigo
    '#10B981', // emerald
    '#F59E0B', // amber
    '#EF4444', // red
    '#6366F1', // violet
    '#0EA5E9', // sky
    '#8B5CF6', // purple
    '#EC4899', // pink
  ];

  // Calculate percentages
  const total = data.reduce((sum, amount) => sum + amount, 0);
  const percentages = data.map(amount => ((amount / total) * 100).toFixed(1));

  // Create labels with percentages
  const labelsWithPercentages = labels.map((label, i) => `${label} ${percentages[i]}%`);

  const chartData = {
    labels: labelsWithPercentages,
    datasets: [
      {
        data,
        backgroundColor: backgroundColors,
        borderColor: backgroundColors,
        borderWidth: 1,
        hoverOffset: 5,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '60%',
    plugins: {
      legend: {
        position: 'right',
        align: 'center',
        labels: {
          usePointStyle: true,
          padding: 15,
          boxWidth: 8,
          font: {
            size: 11,
          },
        },
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            // Just show the category name and dollar amount
            const category = context.label.split(' ')[0]; // Get just the category name without percentage
            const value = context.raw;
            return `${category}: $${value.toLocaleString()}`;
          }
        }
      },
      // Explicitly disable any center text plugin
      doughnutlabel: false,
      centerText: false
    },
  };

  return (
    <div className="flex-1 flex flex-col justify-center">
      <div className="relative w-full" style={{ height: '240px' }}>
        <Doughnut data={chartData} options={options} />
      </div>
    </div>
  );
};

export default ExpenseBreakdownChart;