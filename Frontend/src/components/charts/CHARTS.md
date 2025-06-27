# 📊 Charts Documentation

> **Recharts implementation for Brikli V2 Property Management Dashboard**

## 🎯 Overview

This document describes the chart components used in Brikli V2, built with Recharts. The migration from Chart.js was completed successfully, achieving improved maintainability, performance, and developer experience.

---

## 📊 Chart Components

### Available Charts

| Component | Type | Usage | Location |
|-----------|------|-------|----------|
| **RevenueChart** | Bar Chart | Revenue vs Expenses over time | Dashboard + Accounting Overview |
| **ExpenseBreakdownChart** | Pie Chart | Expense category breakdown | Accounting Overview |
| **IncomeByPropertyChart** | Composed Chart | Income bars + Occupancy line | Accounting Overview |
| **OccupancyChart** | Donut Chart | Property occupancy rates | ⚠️ Ready for future use |

### Dependencies

**Current:**
```json
{
  "recharts": "^2.15.4"
}
```

### Tech Stack Benefits

| Feature | Recharts Advantage |
|---------|-------------------|
| **Performance** | Native React rendering |
| **Code Style** | Declarative components |
| **Lifecycle** | Auto-managed |
| **Responsiveness** | Built-in ResponsiveContainer |
| **Maintainability** | Standard React patterns |

---

## 🚀 Recent Improvements

### Production-Ready Enhancements
- **Data Validation**: Robust array length matching and type safety
- **Performance**: Memoized calculations and optimized re-renders
- **Visual Design**: Professional gradients, shadows, and animations
- **Accessibility**: ARIA labels and semantic HTML
- **Error Handling**: Graceful degradation and informative empty states
- **Unique IDs**: Prevents gradient/filter conflicts with multiple charts
- **Dynamic Sizing**: Responsive height calculations based on data density

### Key Features Added
- **RevenueChart**: NetIncome calculation, reference line for negatives, date formatting
- **IncomeByPropertyChart**: Label collision prevention, dynamic height, animations
- **ExpenseBreakdownChart**: Category sorting, currency formatting in legend
- **All Charts**: Unique gradient IDs, improved empty states, better tooltips

## 🛠️ Implementation Examples

### RevenueChart (Bar Chart with NetIncome)

```jsx
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';

const RevenueChart = ({ data }) => {
  const trimmedData = trimFinancialData(data);
  const chartData = trimmedData.months.map((month, index) => ({
    month,
    income: trimmedData.revenue[index],
    expenses: trimmedData.expenses[index]
  }));

  return (
    <div className="flex-1 flex flex-col justify-center">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" fontSize={11} fill="#999" />
            <YAxis 
              fontSize={11} 
              fill="#999"
              tickFormatter={(value) => value >= 1000 ? `$${value/1000}k` : `$${value}`}
            />
            <Tooltip 
              formatter={(value) => [`$${value.toLocaleString()}`, '']}
              contentStyle={{
                backgroundColor: 'rgba(0,0,0,0.8)',
                border: 'none',
                borderRadius: '4px',
                color: 'white'
              }}
            />
            <Legend />
            <Bar dataKey="income" fill="#1a73e8" radius={[4, 4, 0, 0]} />
            <Bar dataKey="expenses" fill="#e94235" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
```

---

## 📍 Chart Usage

### Current Implementation

| Component | Current Lines | Description | Status |
|-----------|---------------|-------------|--------|
| **RevenueChart** | 133 lines | Revenue vs Expenses bar chart | ✅ Active |
| **ExpenseBreakdownChart** | 146 lines | Expense category pie chart | ✅ Active |
| **IncomeByPropertyChart** | 133 lines | Income bars + Occupancy line chart | ✅ Active |
| **OccupancyChart** | 77 lines | Occupancy donut chart | ⚠️ Ready for use |
| **Total** | **489 lines** | - | ✅ Complete |

### Application Locations

1. **RevenueChart**: 
   - `/dashboard` (main dashboard page)
   - `/accounting/overview` (accounting section)
2. **ExpenseBreakdownChart**: 
   - `/accounting/overview` (accounting section)
3. **IncomeByPropertyChart**: 
   - `/accounting/overview` (accounting section)
4. **OccupancyChart**: 
   - ⚠️ Available for future integration

### File Structure

**Chart Components**: `Frontend/src/components/charts/`
- `RevenueChart.jsx` - Revenue vs Expenses bar chart
- `ExpenseBreakdownChart.jsx` - Expense category pie chart  
- `IncomeByPropertyChart.jsx` - Income bars + Occupancy line chart
- `OccupancyChart.jsx` - Property occupancy donut chart

**Import Usage**:
- `Frontend/src/components/Dashboard.jsx:2`
- `Frontend/src/components/accounting/OverviewTab.jsx:14-16`

## 🚀 Development

### Running Charts

```bash
cd Frontend
npm run dev
```

**Test at**:
- [Dashboard](http://localhost:5173/dashboard)
- [Accounting Overview](http://localhost:5173/accounting/overview)

### Adding New Charts

1. Create component in `Frontend/src/components/charts/`
2. Use Recharts components with ResponsiveContainer
3. Follow existing patterns for styling and data formatting
4. Import and use in relevant pages
5. **Critical**: Use `useId()` for unique gradient/filter IDs
6. Implement proper data validation and memoization
7. Add ARIA labels for accessibility

### Production Checklist
- [ ] Data validation with graceful error handling
- [ ] Unique IDs for SVG elements (gradients, filters)
- [ ] Memoized calculations with `useMemo`
- [ ] Dynamic sizing based on data
- [ ] Professional empty states
- [ ] Accessibility attributes
- [ ] Consistent Tailwind colors
- [ ] Smooth animations

---

> **All chart components use Recharts for consistent, maintainable visualization.**
> 
> **Production Ready**: All charts have been enhanced with robust error handling, performance optimizations, and professional visual design.