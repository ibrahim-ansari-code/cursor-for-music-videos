import React, { useState, useEffect } from 'react';
import OccupancyChart from './OccupancyChart';
import RevenueChart from './RevenueChart';
import { fetchDashboardData } from '../utils/api';

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [selectedProperty, setSelectedProperty] = useState('all');
  const [timePeriod, setTimePeriod] = useState('month');
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        const data = await fetchDashboardData({ 
          property_id: selectedProperty !== 'all' ? selectedProperty : undefined,
          time_period: timePeriod
        });
        setDashboardData(data);
        setError(null);
      } catch (err) {
        console.error('Error loading dashboard data:', err);
        setError(err.message || 'Failed to load dashboard data. Please try again.');
        if (err.response) {
          console.error('Response:', await err.response.text());
        }
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, [selectedProperty, timePeriod]);

  if (loading && !dashboardData) {
    return (
      <div className="p-4 flex justify-center items-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-3 text-gray-600">Loading dashboard data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
          <button 
            onClick={() => window.location.reload()}
            className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        
        <div className="mt-3 md:mt-0 flex space-x-3">
          <select
            className="border border-gray-300 rounded-md py-1.5 pl-3 pr-10 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            value={selectedProperty}
            onChange={(e) => setSelectedProperty(e.target.value)}
          >
            <option value="all">All Properties</option>
            {/* In a real app, these would be populated from API data */}
            <option value="1">Property 1</option>
            <option value="2">Property 2</option>
            <option value="3">Property 3</option>
          </select>
          
          <select
            className="border border-gray-300 rounded-md py-1.5 pl-3 pr-10 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            value={timePeriod}
            onChange={(e) => setTimePeriod(e.target.value)}
          >
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
            <option value="year">This Year</option>
          </select>
          
          <button className="flex items-center px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50">
            <i className="fas fa-cog mr-1.5"></i>
            Customize
          </button>
        </div>
      </div>
      
      {/* Financial Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="dashboard-card">
          <h2 className="text-sm font-medium text-gray-500 mb-1">Revenue</h2>
          <div className="flex items-baseline">
            <p className="text-2xl font-semibold">${dashboardData?.summary?.monthly_revenue?.toLocaleString() || '0'}</p>
            <span className="ml-2 text-xs font-medium text-green-600">
              <i className="fas fa-arrow-up mr-0.5"></i>
              8.3%
            </span>
          </div>
          <div className="h-16 mt-3">
            <svg className="w-full h-full" viewBox="0 0 150 50">
              <path d="M0,40 L10,35 L20,38 L30,32 L40,36 L50,30 L60,35 L70,28 L80,32 L90,25 L100,30 L110,20 L120,25 L130,15 L140,20 L150,10" fill="none" stroke="#E5E7EB" strokeWidth="2" />
              <path d="M0,40 L10,35 L20,38 L30,32 L40,36 L50,30 L60,35 L70,28 L80,32 L90,25 L100,30 L110,20 L120,25 L130,15 L140,20 L150,10" fill="none" stroke="#059669" strokeWidth="2" />
            </svg>
          </div>
        </div>
        
        <div className="dashboard-card">
          <h2 className="text-sm font-medium text-gray-500 mb-1">Earned from Rent</h2>
          <div className="flex items-baseline">
            <p className="text-2xl font-semibold">${dashboardData?.summary?.monthly_revenue?.toLocaleString() || '0'}</p>
            <span className="ml-2 text-xs font-medium text-green-600">
              <i className="fas fa-arrow-up mr-0.5"></i>
              6.2%
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-1">Monthly recurring revenue</div>
        </div>
        
        <div className="dashboard-card">
          <h2 className="text-sm font-medium text-gray-500 mb-1">Spent on maintenance</h2>
          <div className="flex items-baseline">
            <p className="text-2xl font-semibold">${dashboardData?.summary?.maintenance_expenses?.toLocaleString() || '0'}</p>
            <span className="ml-2 text-xs font-medium text-orange-600">
              <i className="fas fa-arrow-up mr-0.5"></i>
              3.0%
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-1">From 5 properties</div>
        </div>
      </div>
      
      {/* Info Banner */}
      <div className="bg-gradient-to-r from-purple-500 to-indigo-600 rounded-lg overflow-hidden shadow-md">
        <div className="p-6 md:flex md:items-center md:justify-between">
          <div className="text-white mb-4 md:mb-0 md:pr-4">
            <h2 className="text-xl font-semibold">Take control of your finances and manage your properties like a pro</h2>
            <p className="mt-1 opacity-90">Stay on top of your revenue, expenses, and occupancy all in one place.</p>
          </div>
          <div className="flex items-center">
            <button className="bg-white text-indigo-600 px-4 py-2 rounded-md font-medium shadow-sm hover:bg-gray-50">
              Get Started
            </button>
            <img src="https://source.unsplash.com/random/120x80/?building" alt="Properties" className="h-20 ml-6 rounded-md hidden md:block" />
          </div>
        </div>
      </div>
      
      {/* Stats & Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Payments Due */}
        <div className="dashboard-card">
          <h2 className="text-lg font-medium text-gray-900 mb-3">Due</h2>
          
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-6">
              <button className="py-2 px-1 border-b-2 border-blue-500 font-medium text-sm text-blue-600">
                Rent
              </button>
              <button className="py-2 px-1 border-b-2 border-transparent font-medium text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300">
                Invoices
              </button>
            </nav>
          </div>
          
          <div className="mt-3 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tenant</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reminder</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {dashboardData?.payments_due?.map((payment) => (
                  <tr key={payment.id}>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-700">
                          {payment.tenant_name.split(' ').map(n => n[0]).join('')}
                        </div>
                        <div className="ml-3">
                          <p className="text-sm font-medium text-gray-900">{payment.tenant_name}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap text-sm text-gray-900">${payment.amount}</td>
                    <td className="px-3 py-3 whitespace-nowrap text-sm text-gray-500">
                      {payment.days_overdue 
                        ? <span className="text-red-600">Yesterday</span> 
                        : new Date(payment.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                      }
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap text-sm text-gray-500">
                      <button className="text-gray-400 hover:text-gray-500">
                        <i className="far fa-bell"></i>
                      </button>
                    </td>
                  </tr>
                ))}
                {(!dashboardData?.payments_due || dashboardData.payments_due.length === 0) && (
                  <tr>
                    <td colSpan="4" className="px-3 py-4 text-center text-sm text-gray-500">
                      No pending payments
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        
        {/* Occupancy Rate */}
        <div className="dashboard-card">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Occupancy rate</h2>
          
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <OccupancyChart 
                occupied={dashboardData?.occupancy?.occupied_units || 0} 
                vacant={dashboardData?.occupancy?.vacant_units || 0} 
              />
            </div>
            
            <div className="space-y-4">
              <div>
                <div className="flex items-center">
                  <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
                  <span className="text-sm font-medium text-gray-500">Occupied</span>
                </div>
                <p className="text-xl font-semibold mt-1">{dashboardData?.occupancy?.occupied_units || 0}</p>
              </div>
              
              <div>
                <div className="flex items-center">
                  <div className="w-3 h-3 rounded-full bg-blue-500 mr-2"></div>
                  <span className="text-sm font-medium text-gray-500">Vacant</span>
                </div>
                <p className="text-xl font-semibold mt-1">{dashboardData?.occupancy?.vacant_units || 0}</p>
              </div>
              
              <div>
                <div className="flex items-center">
                  <div className="w-3 h-3 rounded-full bg-gray-300 mr-2"></div>
                  <span className="text-sm font-medium text-gray-500">Total Units</span>
                </div>
                <p className="text-xl font-semibold mt-1">{dashboardData?.occupancy?.total_units || 0}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Leads & Revenue Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Leads */}
        <div className="dashboard-card">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Leads</h2>
          
          <div className="space-y-3">
            {dashboardData?.leads?.map((lead) => (
              <div key={lead.id} className="flex justify-between items-start p-3 bg-gray-50 rounded-lg">
                <div className="flex items-start">
                  <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gray-300 flex items-center justify-center text-gray-600">
                    {lead.name.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-900">{lead.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{lead.property_interest}</p>
                  </div>
                </div>
                <div className="flex items-center">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    lead.status === 'new' ? 'bg-green-100 text-green-800' : 
                    lead.status === 'contacted' ? 'bg-blue-100 text-blue-800' : 
                    'bg-purple-100 text-purple-800'
                  }`}>{lead.status === 'new' ? 'Via email' : 'Via mail'}</span>
                  <span className="text-xs text-gray-500 ml-3">
                    {new Date(lead.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {/* Revenue Trends */}
        <div className="dashboard-card">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Latest Contracts/Tenants</h2>
          
          <div className="space-y-3">
            {dashboardData?.leads?.map((lead) => (
              <div key={`contract-${lead.id}`} className="flex justify-between items-start p-3 bg-gray-50 rounded-lg">
                <div className="flex items-start">
                  <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gray-300 flex items-center justify-center text-gray-600">
                    {lead.name.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-900">{lead.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      <span className="text-gray-900">Suit 509</span><br />
                      100 Ocean Street, KPL 5R2, San Francisco
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="h-12 w-16 rounded bg-gray-200 mb-1">
                    <img 
                      src={`https://source.unsplash.com/random/64x48/?building,${lead.id}`} 
                      alt="Property" 
                      className="h-full w-full object-cover rounded"
                    />
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(lead.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      {/* Revenue Chart */}
      <div className="dashboard-card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-medium text-gray-900">Revenue Trends</h2>
          <div className="flex space-x-2">
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-blue-500 mr-1"></div>
              <span className="text-xs text-gray-600">Revenue</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-green-500 mr-1"></div>
              <span className="text-xs text-gray-600">Expenses</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-purple-500 mr-1"></div>
              <span className="text-xs text-gray-600">Net Income</span>
            </div>
          </div>
        </div>
        
        <RevenueChart data={dashboardData?.revenue} />
      </div>
    </div>
  );
};

export default Dashboard;
