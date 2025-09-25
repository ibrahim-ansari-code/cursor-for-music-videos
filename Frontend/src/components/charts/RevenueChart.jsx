import React, { useId, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { ChartSkeleton } from "../ui/skeletons";

const RevenueChart = ({ data, emptyStateMessage = "Revenue and expense data will appear here once available", isLoading = false }) => {
  // ALL HOOKS MUST BE CALLED FIRST - BEFORE ANY CONDITIONAL LOGIC
  
  // Generate unique IDs for this chart instance
  const chartId = useId();
  const incomeGradientId = `incomeGradient-${chartId}`;
  const expenseGradientId = `expenseGradient-${chartId}`;
  
  // Dynamic colors based on dark mode with reactive updates
  const [isDarkMode, setIsDarkMode] = React.useState(() => {
    return document.documentElement.classList.contains('dark');
  });
  
  // Watch for dark mode changes
  React.useEffect(() => {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
          setIsDarkMode(document.documentElement.classList.contains('dark'));
        }
      });
    });
    
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });
    
    return () => observer.disconnect();
  }, []);
  
  const chartColors = useMemo(() => ({
    tickColor: isDarkMode ? '#F9FAFB' : '#6B7280', // gray-50 in dark, gray-500 in light
    gridColor: isDarkMode ? '#374151' : '#E5E7EB', // gray-700 in dark, gray-200 in light  
    axisColor: isDarkMode ? '#4B5563' : '#E5E7EB', // gray-600 in dark, gray-200 in light
    referenceColor: isDarkMode ? '#6B7280' : '#9CA3AF', // gray-500 in dark, gray-400 in light
    legendColor: isDarkMode ? '#F9FAFB' : '#374151', // gray-50 in dark, gray-700 in light
  }), [isDarkMode]);
  
  // Improved data validation and trimming function
  const trimFinancialData = useMemo(() => {
    if (!data || !data.months || !data.revenue || !data.expenses) {
      return null;
    }
    
    // Validate array lengths match
    const minLength = Math.min(
      data.months.length,
      data.revenue.length,
      data.expenses.length
    );
    
    if (minLength === 0) return null;
    
    // Make safe copies with validated lengths
    const months = data.months.slice(0, minLength);
    const revenue = data.revenue.slice(0, minLength).map(v => Number(v) || 0);
    const expenses = data.expenses.slice(0, minLength).map((v, index) => {
      const value = Number(v) || 0;
      // Log warning for negative expense values
      if (value < 0) {
        console.warn(`Negative expense value detected at index ${index} (${months[index]}): ${value}`);
      }
      // Still convert to positive for display, but we've logged the issue
      return Math.abs(value);
    });
    
    // Find first month with significant activity (threshold: $10)
    const ACTIVITY_THRESHOLD = 10;
    let firstActivityIndex = revenue.findIndex((rev, i) => 
      rev >= ACTIVITY_THRESHOLD || expenses[i] >= ACTIVITY_THRESHOLD
    );
    
    // If no significant activity found, show all data
    if (firstActivityIndex === -1) {
      firstActivityIndex = 0;
    }
    
    // Return trimmed data
    return {
      months: months.slice(firstActivityIndex),
      revenue: revenue.slice(firstActivityIndex),
      expenses: expenses.slice(firstActivityIndex),
    };
  }, [data]);

  // Transform and enhance data for chart
  const chartData = useMemo(() => {
    if (!trimFinancialData) return [];
    
    return trimFinancialData.months.map((month, index) => {
      const income = trimFinancialData.revenue[index] || 0;
      const expenses = trimFinancialData.expenses[index] || 0;
      const netIncome = income - expenses;
      
      // Extract month and year from the full month string (e.g., "Jun 25" or "June 2025")
      let displayMonth;
      let yearPart = '';
      
      // Check if month contains year info
      if (month.includes(' ')) {
        const parts = month.split(' ');
        const monthPart = parts[0].length > 3 ? parts[0].substring(0, 3) : parts[0];
        yearPart = parts[1];
        // Format year - if it's 2 digits, add '20' prefix; if 4 digits, take last 2
        if (yearPart.length === 2) {
          displayMonth = `${monthPart} '${yearPart}`;
        } else if (yearPart.length === 4) {
          displayMonth = `${monthPart} '${yearPart.substring(2)}`;
        } else {
          displayMonth = `${monthPart} ${yearPart}`;
        }
      } else {
        // If no year info, just use abbreviated month
        displayMonth = month.length > 3 ? month.substring(0, 3) : month;
      }
      
      return {
        month: displayMonth,
        fullMonth: month,
        Income: income,
        Expenses: expenses,
        NetIncome: netIncome,
        // Pre-formatted values for tooltips
        formattedIncome: income.toLocaleString('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }),
        formattedExpenses: expenses.toLocaleString('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }),
        formattedNetIncome: netIncome.toLocaleString('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
          signDisplay: 'always',
        }),
      };
    });
  }, [trimFinancialData]);
  
  // Calculate dynamic height based on data points
  const chartHeight = useMemo(() => {
    if (chartData.length <= 3) return 280;
    if (chartData.length <= 6) return 320;
    return Math.min(400, 320 + (chartData.length - 6) * 10);
  }, [chartData.length]);

  // NOW SAFE TO DO CONDITIONAL RENDERING AFTER ALL HOOKS
  
  // Show loading skeleton
  if (isLoading) {
    return <ChartSkeleton height="300px" />;
  }

  // Show improved empty state
  if (!trimFinancialData) {
    return (
      <div className="flex items-center justify-center h-[300px]">
        <div className="text-center">
          <div className="w-16 h-16 mb-4 mx-auto rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-gray-400 dark:text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
              />
            </svg>
          </div>
          <h3 className="text-base font-medium text-gray-800 dark:text-gray-200 mb-1">
            No Revenue Data
          </h3>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            {emptyStateMessage}
          </p>
        </div>
      </div>
    );
  }
  
  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-900 bg-opacity-90 text-white px-3 py-2 rounded-lg shadow-lg">
          <p className="font-medium text-sm mb-2">{data.fullMonth}</p>
          <div className="space-y-1">
            <div className="flex justify-between items-center gap-4">
              <span className="text-xs text-gray-300">Revenue:</span>
              <span className="text-xs font-medium">{data.formattedIncome}</span>
            </div>
            <div className="flex justify-between items-center gap-4">
              <span className="text-xs text-gray-300">Expenses:</span>
              <span className="text-xs font-medium">{data.formattedExpenses}</span>
            </div>
            <div className="border-t border-gray-700 pt-1 mt-1">
              <div className="flex justify-between items-center gap-4">
                <span className="text-xs text-gray-300">Net Income:</span>
                <span className={`text-xs font-bold ${data.NetIncome >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {data.formattedNetIncome}
                </span>
              </div>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  // Custom bar label renderer
  const renderBarLabel = (props) => {
    const { x, y, width, value, dataKey } = props;
    // Only show labels when we have few data points for clarity
    if (chartData.length > 6) return null;
    
    const formattedValue = value >= 1000 
      ? `$${(value / 1000).toFixed(0)}k` 
      : `$${value}`;
    
     // FORCE: Income labels GREEN, expenses RED - logical color coding  
     const labelColor = dataKey === 'Income' ? '#10B981' : '#EF4444';
    
    return (
      <text 
        x={x + width / 2} 
        y={y - 5} 
        fill={labelColor} 
        textAnchor="middle" 
        fontSize="11"
        fontWeight="600"
      >
        {formattedValue}
      </text>
    );
  };

  // Custom NetIncome bar label renderer with better positioning and visibility
  const renderNetIncomeLabel = (props) => {
    const { x, y, width, value } = props;
    // Only show labels when we have few data points for clarity
    if (chartData.length > 6) return null;
    
    const formattedValue = Math.abs(value) >= 1000 
      ? `${value < 0 ? '-' : ''}$${(Math.abs(value) / 1000).toFixed(0)}k` 
      : `${value < 0 ? '-' : ''}$${Math.abs(value)}`;
    
    // For negative values, position label above the zero line for visibility
    // For positive values, position above the bar
    const labelY = value < 0 ? y - 20 : y - 5;
    const labelColor = value >= 0 ? '#10B981' : '#EF4444'; // Green for positive, red for negative
    
    return (
      <text 
        x={x + width / 2} 
        y={labelY} 
        fill={labelColor}
        textAnchor="middle" 
        fontSize="11"
        fontWeight="600"
      >
        {formattedValue}
      </text>
    );
  };

  return (
    <div className="flex-1 flex flex-col justify-center">
      <div 
        style={{ height: `${chartHeight}px` }}
        role="img"
        aria-label={`Revenue chart showing ${chartData.length} months of financial data`}
        className="transition-all duration-500 ease-out"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            key={`revenue-chart-${isDarkMode ? 'dark' : 'light'}-${chartData.length}`}
            data={chartData}
            margin={{
              top: 20,
              right: 30,
              left: 25,
              bottom: chartData.length > 6 ? 50 : 30,
            }}
            barCategoryGap="20%"
          >
            <defs>
              <linearGradient id={incomeGradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3B82F6" stopOpacity={1} />
                <stop offset="100%" stopColor="#3B82F6" stopOpacity={0.8} />
              </linearGradient>
              <linearGradient id={expenseGradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#EF4444" stopOpacity={1} />
                <stop offset="100%" stopColor="#EF4444" stopOpacity={0.8} />
              </linearGradient>
              <filter id={`barShadow-${chartId}`} x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="1" stdDeviation="2" floodOpacity="0.1"/>
              </filter>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={chartColors.gridColor}
              vertical={false}
              horizontalOpacity={0.5}
            />
            <XAxis
              dataKey="month"
              axisLine={{ stroke: chartColors.axisColor }}
              tickLine={false}
              tick={{ fontSize: 12, fill: chartColors.tickColor }}
              angle={chartData.length > 6 ? -45 : 0}
              textAnchor={chartData.length > 6 ? "end" : "middle"}
              height={chartData.length > 6 ? 65 : 35}
              interval={chartData.length > 12 ? 1 : 0}
              tickMargin={15}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: chartColors.tickColor }}
              tickMargin={8}
              tickFormatter={(value) => {
                const absValue = Math.abs(value);
                const sign = value < 0 ? "-" : "";
                if (absValue >= 1000) {
                  return `${sign}$${(absValue / 1000).toFixed(0)}k`;
                }
                return `${sign}$${absValue}`;
              }}
              domain={[dataMin => (dataMin < 0 ? dataMin * 1.1 : 0), 'dataMax + 10%']}
            />
            {/* Reference line at zero for net income clarity */}
            {chartData.some(d => d.NetIncome < 0) && (
              <ReferenceLine 
                y={0} 
                stroke={chartColors.referenceColor} 
                strokeDasharray="3 3" 
                strokeWidth={1}
              />
            )}
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ fill: "rgba(59, 130, 246, 0.05)" }}
              animationDuration={150}
            />
            <Legend
              align="right"
              verticalAlign="top"
              iconType="rect"
              wrapperStyle={{
                fontSize: "13px",
                paddingBottom: "20px",
                paddingRight: "0px",
              }}
              formatter={(value) => {
                const displayValue = value === 'NetIncome' ? 'Net Income' : value;
                return <span style={{ color: chartColors.legendColor, paddingLeft: '8px' }}>{displayValue}</span>
              }}
            />
            <Bar
              dataKey="Income"
              fill={`url(#${incomeGradientId})`}
              radius={[6, 6, 0, 0]}
              maxBarSize={chartData.length <= 3 ? 100 : chartData.length <= 6 ? 80 : 60}
              style={{ filter: `url(#barShadow-${chartId})` }}
              animationDuration={800}
              animationBegin={0}
              label={renderBarLabel}
            />
            <Bar
              dataKey="Expenses"
              fill={`url(#${expenseGradientId})`}
              radius={[6, 6, 0, 0]}
              maxBarSize={chartData.length <= 3 ? 100 : chartData.length <= 6 ? 80 : 60}
              style={{ filter: `url(#barShadow-${chartId})` }}
              animationDuration={800}
              animationBegin={100}
              label={renderBarLabel}
            />
            <Bar
              dataKey="NetIncome"
              name="Net Income"
              radius={[6, 6, 0, 0]}
              maxBarSize={chartData.length <= 3 ? 100 : chartData.length <= 6 ? 80 : 60}
              animationDuration={800}
              animationBegin={200}
              label={renderNetIncomeLabel}
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.NetIncome >= 0 ? '#10B981' : '#EF4444'}
                  fillOpacity={0.9}
                  style={{ filter: `url(#barShadow-${chartId})` }}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default RevenueChart;
