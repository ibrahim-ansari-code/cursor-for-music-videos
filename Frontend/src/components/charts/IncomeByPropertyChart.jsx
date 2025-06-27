import React, { useId } from "react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const IncomeByPropertyChart = ({ properties = [] }) => {
  // Generate unique IDs for this chart instance
  const chartId = useId();
  const gradientId = `incomeGradient-${chartId}`;
  const shadowId = `barShadow-${chartId}`;
  
  // Show a placeholder while data is loading or empty
  if (!Array.isArray(properties) || properties.length === 0) {
    return (
      <div className="flex items-center justify-center h-[320px]">
        <div className="text-center">
          <div className="w-16 h-16 mb-4 mx-auto rounded-full bg-gray-100 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3.75h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008z"
              />
            </svg>
          </div>
          <h3 className="text-base font-medium text-gray-800 mb-1">
            No Property Data
          </h3>
          <p className="text-xs text-gray-600">
            Add properties to see income and occupancy breakdown
          </p>
        </div>
      </div>
    );
  }

  // Transform and validate data for Recharts
  const chartData = properties
    .map((property) => {
      const income = Number(property.monthlyIncome) || 0;
      const occupancyRate = Number(property.occupancyRate) || 0;

      // Validate data
      if (income < 0 || occupancyRate < 0 || occupancyRate > 100) {
        console.warn(`Invalid data for property ${property.name}:`, { income, occupancyRate });
        return null;
      }

      return {
        name: property.name || 'Unknown Property',
        income: income,
        occupancyRate: occupancyRate,
        // Add formatted values for tooltips
        formattedIncome: income.toLocaleString('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }),
      };
    })
    .filter(Boolean) // Remove invalid entries
    .sort((a, b) => b.income - a.income); // Sort by income descending

  // Custom tooltip component for better styling
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-900 bg-opacity-90 text-white px-3 py-2 rounded-lg shadow-lg">
          <p className="font-medium text-sm mb-1">{label}</p>
          <div className="space-y-1">
            <p className="text-xs">
              <span className="text-gray-300">Income:</span>{' '}
              <span className="font-medium">{data.formattedIncome}</span>
            </p>
            <p className="text-xs">
              <span className="text-gray-300">Occupancy:</span>{' '}
              <span className="font-medium">{data.occupancyRate}%</span>
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  // Custom label for bar values with collision detection
  const renderCustomBarLabel = (props) => {
    const { x, y, width, height, value } = props;
    
    // Don't render label if bar is too short (less than 25px)
    if (height < 25) {
      return null;
    }
    
    const formattedValue = value >= 1000 
      ? `$${(value / 1000).toFixed(1)}k` 
      : `$${value}`;
    
    // Calculate text width approximation (11px font × character count)
    const textWidth = formattedValue.length * 7;
    
    // Don't render if text is wider than bar
    if (textWidth > width - 4) {
      return null;
    }
    
    return (
      <text 
        x={x + width / 2} 
        y={y - 5} 
        fill="#374151" 
        textAnchor="middle" 
        fontSize="11"
        fontWeight="500"
      >
        {formattedValue}
      </text>
    );
  };

  // Custom label for occupancy rate with enhanced collision detection
  const renderOccupancyLabel = (props) => {
    const { x, y, value, index, width } = props;
    
    // Don't render label if value is 0 to avoid overlap with axis
    if (value === 0) return null;
    
    // Dynamic label spacing based on chart width and data points
    const calculateSkipInterval = () => {
      // Estimate available width per data point
      const chartWidth = width || 800; // Default fallback width
      const availableWidth = chartWidth - 80; // Account for margins
      const widthPerPoint = availableWidth / chartData.length;
      
      // Estimate label width (approximately 30px for "XX%" format)
      const estimatedLabelWidth = 30;
      
      // Calculate how many labels can fit without overlap
      if (widthPerPoint >= estimatedLabelWidth + 10) {
        return 1; // Show all labels if there's enough space
      } else if (widthPerPoint >= (estimatedLabelWidth + 10) / 2) {
        return 2; // Show every other label
      } else if (widthPerPoint >= (estimatedLabelWidth + 10) / 3) {
        return 3; // Show every third label
      } else {
        return 4; // Show every fourth label for very dense charts
      }
    };
    
    const skipInterval = calculateSkipInterval();
    
    // Always show first, last, and highest/lowest values
    const isImportant = index === 0 || 
                       index === chartData.length - 1 ||
                       value === Math.max(...chartData.map(d => d.occupancyRate)) ||
                       value === Math.min(...chartData.map(d => d.occupancyRate));
    
    // Skip labels based on calculated interval, but always show important ones
    if (!isImportant && index % skipInterval !== 0) {
      return null;
    }
    
    // Position label above or below based on neighboring values to minimize overlap
    const neighbors = chartData.slice(Math.max(0, index - 1), index + 2);
    const hasHighNeighbors = neighbors.some(n => n.occupancyRate > value + 10);
    const yOffset = hasHighNeighbors ? 15 : -10;
    
    return (
      <text 
        x={x} 
        y={y + yOffset} 
        fill="#10B981" 
        textAnchor="middle" 
        fontSize="12"
        fontWeight="600"
      >
        {value}%
      </text>
    );
  };

  // Dynamic height calculation with better scaling
  const calculateChartHeight = () => {
    const baseHeight = 200; // Base height for chart elements (legend, axes, padding)
    const barHeight = 40; // Height per bar
    const minHeight = 300; // Minimum chart height
    const maxHeight = 600; // Maximum chart height
    
    // For 1-3 properties: use minimum height for better proportions
    if (chartData.length <= 3) {
      return minHeight;
    }
    
    // For 4+ properties: scale dynamically
    const calculatedHeight = baseHeight + (chartData.length * barHeight);
    
    // Clamp between min and max
    return Math.max(minHeight, Math.min(maxHeight, calculatedHeight));
  };
  
  const chartHeight = calculateChartHeight();

  return (
    <div className="flex-1 flex flex-col justify-center animate-fadeIn">
      <div 
        style={{ 
          height: `${chartHeight}px`
        }}
        role="img"
        aria-label={`Income by property chart showing ${chartData.length} properties with monthly income and occupancy rates`}
        className="transition-all duration-500 ease-out"
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{
              top: 10,
              right: 10,
              left: 10,
              bottom: 25,
            }}
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3B82F6" stopOpacity={1} />
                <stop offset="100%" stopColor="#3B82F6" stopOpacity={0.8} />
              </linearGradient>
              <filter id={shadowId} x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="1" stdDeviation="2" floodOpacity="0.1"/>
              </filter>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#E5E7EB"
              vertical={false}
              horizontalOpacity={0.5}
            />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 12, fill: '#374151' }}
              angle={0}
              textAnchor="middle"
              height={10}
              axisLine={{ stroke: '#E5E7EB' }}
              tickLine={false}
              interval={0}
              tickFormatter={(value) => {
                // Truncate long property names
                return value.length > 12 ? value.substring(0, 12) + '...' : value;
              }}
            />
            <YAxis
              yAxisId="left"
              tick={{ fontSize: 12, fill: "#6B7280" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(value) =>
                value >= 1000 ? `$${(value / 1000).toFixed(0)}k` : `$${value}`
              }
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 12, fill: "#6B7280" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(value) => `${value}%`}
              domain={[0, 'dataMax + 5']}
            />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ fill: "rgba(59, 130, 246, 0.05)" }}
            />
            <Legend
              align="right"
              verticalAlign="top"
              wrapperStyle={{
                paddingBottom: "20px",
                fontSize: "13px"
              }}
            />
            <Bar
              yAxisId="left"
              dataKey="income"
              fill={`url(#${gradientId})`}
              name="Monthly Income"
              radius={[8, 8, 0, 0]}
              maxBarSize={80}
              style={{ filter: `url(#${shadowId})` }}
              label={renderCustomBarLabel}
              animationDuration={800}
              animationBegin={0}
              animationEasing="ease-out"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="occupancyRate"
              stroke="#10B981"
              strokeWidth={3}
              name="Occupancy Rate"
              dot={{ fill: "#10B981", strokeWidth: 2, r: 6 }}
              activeDot={{ r: 8, strokeWidth: 0 }}
              label={renderOccupancyLabel}
              animationDuration={1000}
              animationBegin={200}
              animationEasing="ease-out"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default IncomeByPropertyChart;
