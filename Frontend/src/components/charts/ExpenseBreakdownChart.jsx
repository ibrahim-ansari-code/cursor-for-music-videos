import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

const ExpenseBreakdownChart = ({ expenses = [] }) => {
  // Generate unique ID for this chart instance
  const chartId = React.useId();
  const shadowId = `shadow-${chartId}`;
  
  const backgroundColors = [
    "#3B82F6", // blue-500
    "#10B981", // emerald-500
    "#F59E0B", // amber-500
    "#8B5CF6", // violet-500
    "#EC4899", // pink-500
    "#06B6D4", // cyan-500
    "#F97316", // orange-500
    "#14B8A6", // teal-500
    "#6366F1", // indigo-500
    "#84CC16", // lime-500
  ];

  if (!expenses || expenses.length === 0) {
    return (
      <div className="flex items-center justify-center h-[260px]">
        <div className="text-center">
          <div className="w-16 h-16 mb-4 mx-auto rounded-full bg-gray-100 flex items-center justify-center">
            <svg
              aria-hidden="true"
              className="w-8 h-8 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 14.25l6-6m4.5-3.493V21.75l-3.75-1.5-3.75 1.5-3.75-1.5-3.75 1.5V4.757c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0c1.1.128 1.907 1.077 1.907 2.185zM9.75 9h.008v.008H9.75V9zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm4.125 4.5h.008v.008h-.008V13.5zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
              />
            </svg>
          </div>
          <h3 className="text-base font-medium text-gray-800 mb-1">No Expense Data</h3>
          <p className="text-xs text-gray-600">
            Add expenses to see a breakdown by category
          </p>
        </div>
      </div>
    );
  }

  // Calculate total for percentages
  const total = expenses.reduce((sum, exp) => sum + (Number(exp.total_amount) || 0), 0);

  // Group expenses by category and sum amounts
  const categoryTotals = expenses.reduce((acc, exp) => {
    const category = exp.category || 'Other';
    const amount = Number(exp.total_amount) || 0;
    
    // Skip negative amounts or invalid values
    if (amount < 0 || isNaN(amount)) {
      console.warn(`Invalid expense amount for category ${category}: ${exp.total_amount}`);
      return acc;
    }
    
    if (acc[category]) {
      acc[category] += amount;
    } else {
      acc[category] = amount;
    }
    return acc;
  }, {});

  // Transform data for Recharts - sort categories alphabetically for consistent colors
  const chartData = Object.entries(categoryTotals)
    .sort(([a], [b]) => a.localeCompare(b)) // Sort by category name
    .map(([category, amount], index) => {
      const percentage = total > 0 ? ((amount / total) * 100).toFixed(1) : "0.0";
      
      return {
        name: category.charAt(0).toUpperCase() + category.slice(1),
        value: amount,
        percentage: percentage,
        color: backgroundColors[index % backgroundColors.length],
        formattedValue: amount.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      };
    })
    .filter(item => item.value > 0); // Only show categories with positive values

  // Custom tooltip component
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-900 bg-opacity-90 text-white px-3 py-2 rounded-lg shadow-lg" 
             style={{ fontSize: '13px' }}>
          <p className="font-medium">{data.name}</p>
          <p className="text-gray-300">${data.formattedValue} ({data.percentage}%)</p>
        </div>
      );
    }
    return null;
  };

  // Custom label function for legend with percentages
  const renderLegend = (props) => {
    const { payload } = props;
    return (
      <ul className="recharts-legend-wrapper" style={{ 
        listStyle: 'none', 
        margin: 0, 
        padding: '0 0 0 24px',
        fontSize: '13px',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        color: '#374151'
      }}>
        {payload.map((entry, index) => {
          const data = chartData.find(item => item.color === entry.color);
          return (
            <li key={`item-${index}`} style={{ 
              display: 'flex', 
              alignItems: 'center', 
              marginBottom: '12px' 
            }}>
              <span style={{
                display: 'inline-block',
                width: '12px',
                height: '12px',
                backgroundColor: entry.color,
                borderRadius: '3px',
                marginRight: '10px',
                flexShrink: 0
              }}></span>
              <span style={{ 
                display: 'flex', 
                flexDirection: 'column',
                lineHeight: '1.3'
              }}>
                <span style={{ fontWeight: '500', color: '#111827' }}>
                  {entry.value}
                </span>
                <span style={{ fontSize: '12px', color: '#6B7280' }}>
                  ${data?.formattedValue || '0.00'} ({data?.percentage || '0.0'}%)
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <div className="flex-1 flex flex-col justify-center p-2">
      <div className="relative w-full h-[260px]" aria-label={`Expense breakdown pie chart showing ${chartData.length} categories`}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <defs>
              <filter id={shadowId} x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.15"/>
              </filter>
            </defs>
            <Pie
              data={chartData}
              cx="45%"
              cy="50%"
              innerRadius={50}
              outerRadius={100}
              paddingAngle={2}
              dataKey="value"
              animationBegin={0}
              animationDuration={800}
              animationEasing="ease-out"
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.color} 
                  stroke="none"
                  style={{ filter: `url(#${shadowId})` }}
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              verticalAlign="middle" 
              align="right" 
              layout="vertical"
              content={renderLegend}
              wrapperStyle={{
                paddingLeft: '14px',
                maxHeight: '240px',
                overflowY: 'auto'
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ExpenseBreakdownChart;