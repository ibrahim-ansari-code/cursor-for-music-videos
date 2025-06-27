import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const OccupancyChart = ({ occupied, vacant }) => {
  const data = [
    { 
      name: 'Occupied', 
      value: occupied, 
      color: '#10B981' // green-500
    },
    { 
      name: 'Vacant', 
      value: vacant, 
      color: '#3B82F6' // blue-500
    }
  ];
  
  const total = occupied + vacant;

  // Custom tooltip component
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      const value = data.value;
      const percentage = total === 0 ? 0 : Math.round((value / total) * 100);
      return (
        <div className="bg-black bg-opacity-70 text-white text-xs p-2 rounded">
          <p>{`${data.name}: ${value} (${percentage}%)`}</p>
        </div>
      );
    }
    return null;
  };

  // Custom label function for center text
  const renderCustomizedLabel = ({ cx, cy }) => (
    <text x={cx} y={cy} fill="#1F2937" textAnchor="middle" dominantBaseline="central">
      <tspan x={cx} dy="-0.3em" fontSize="24" fontWeight="700" fontFamily="Inter">
        {total}
      </tspan>
      <tspan x={cx} dy="1.2em" fontSize="14" fontWeight="500" fill="#6B7280" fontFamily="Inter">
        Units
      </tspan>
    </text>
  );

  return (
    <div className="h-60 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={70}
            outerRadius={100}
            paddingAngle={0}
            dataKey="value"
            label={renderCustomizedLabel}
            labelLine={false}
          >
            {data.map((entry, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={entry.color} 
                stroke="#FFFFFF" 
                strokeWidth={2}
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default OccupancyChart;