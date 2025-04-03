import React, { useRef, useEffect } from 'react';
import Chart from 'chart.js/auto';

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

    const ctx = chartRef.current.getContext('2d');
    
    // Prepare data
    const labels = data.months;
    const revenueData = data.revenue;
    const expensesData = data.expenses;
    const netIncomeData = data.net_income;
    
    // Create chart
    chartInstance.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Revenue',
            data: revenueData,
            backgroundColor: '#3B82F6', // blue-500
            borderColor: '#3B82F6',
            borderWidth: 1,
            borderRadius: 4,
            order: 2
          },
          {
            label: 'Expenses',
            data: expensesData,
            backgroundColor: '#10B981', // green-500
            borderColor: '#10B981',
            borderWidth: 1,
            borderRadius: 4,
            order: 3
          },
          {
            label: 'Net Income',
            data: netIncomeData,
            type: 'line',
            borderColor: '#8B5CF6', // purple-500
            borderWidth: 2,
            pointBackgroundColor: '#8B5CF6',
            pointRadius: 3,
            fill: false,
            tension: 0.1,
            order: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              drawBorder: false,
            },
            ticks: {
              callback: function(value) {
                return '$' + value.toLocaleString();
              }
            }
          },
          x: {
            grid: {
              display: false,
              drawBorder: false
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                let label = context.dataset.label || '';
                if (label) {
                  label += ': ';
                }
                if (context.parsed.y !== null) {
                  label += '$' + context.parsed.y.toLocaleString();
                }
                return label;
              }
            }
          }
        },
        interaction: {
          mode: 'index',
          intersect: false,
        },
        barPercentage: 0.6,
        categoryPercentage: 0.7
      }
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [data]);

  return (
    <div className="h-72 w-full">
      <canvas ref={chartRef}></canvas>
    </div>
  );
};

export default RevenueChart;
