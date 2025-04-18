import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchPropertyById } from '../utils/api';
import StatCard from '../components/StatCard'; // Import StatCard
import UnitTable from '../components/UnitTable'; // Import UnitTable

// Icons for StatCards
const UnitIcon = () => <i className="fas fa-door-closed text-blue-600"></i>;
const VacantIcon = () => <i className="fas fa-door-open text-yellow-600"></i>;
const RevenueIcon = () => <i className="fas fa-dollar-sign text-green-600"></i>;

const PropertyDetail = () => {
  const { id } = useParams();
  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [stats, setStats] = useState({
    totalUnits: 0,
    vacantUnits: 0,
    monthlyRevenue: 0,
  });

  useEffect(() => {
    const loadProperty = async () => {
      try {
        setLoading(true);
        setError(null);
        console.log(`Fetching property details for ID: ${id}`);
        const data = await fetchPropertyById(id);
        console.log('Property data received:', data);
        setProperty(data);

        // Calculate stats based on the fetched units
        if (data && data.units) {
          const totalUnits = data.units.length;
          const vacantUnits = data.units.filter(unit => !unit.is_rented).length;
          const monthlyRevenue = data.units
            .filter(unit => unit.is_rented && unit.monthly_rent)
            .reduce((sum, unit) => sum + unit.monthly_rent, 0);
          
          setStats({ totalUnits, vacantUnits, monthlyRevenue });
        }

      } catch (err) {
        console.error('Error fetching property details:', err);
        setError(err.message || 'Failed to load property details.');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      loadProperty();
    }
  }, [id]);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount || 0);
  };

  // Functions for unit actions
  const handleEditUnit = (unitId) => {
    console.log(`Edit unit clicked: ${unitId}`);
    // Open edit modal logic here
  };

  const handleDeleteUnit = (unitId) => {
    console.log(`Delete unit clicked: ${unitId}`);
    // Confirm and call delete API logic here
  };

  const handleAddNewUnit = () => {
    console.log('Add new unit clicked');
    // Open add unit modal logic here
  };

  if (loading) return (
    <div className="p-6 text-center">
      <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
      <p className="text-gray-600">Loading property details...</p>
    </div>
  );
  
  if (error) return (
    <div className="p-6 text-center">
      <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4 max-w-md mx-auto">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm leading-5 text-red-700">{error}</p>
          </div>
        </div>
      </div>
      <button 
        onClick={() => window.location.reload()}
        className="mt-2 px-4 py-2 border border-transparent text-sm leading-5 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-500 focus:outline-none focus:border-blue-700 focus:shadow-outline-blue active:bg-blue-700 transition ease-in-out duration-150"
      >
        Try Again
      </button>
    </div>
  );
  
  if (!property) return <div className="p-6 text-center">Property not found.</div>;

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      {/* Breadcrumbs */}
      <div className="mb-6">
        <nav className="text-sm" aria-label="Breadcrumb">
          <ol className="list-none p-0 inline-flex space-x-2">
            <li className="flex items-center">
              <Link to="/" className="text-gray-500 hover:text-gray-700">
                <i className="fas fa-home"></i>
              </Link>
            </li>
            <li>
              <span className="text-gray-400">/</span>
            </li>
            <li className="flex items-center">
              <Link to="/properties" className="text-gray-500 hover:text-gray-700">Properties</Link>
            </li>
            <li>
              <span className="text-gray-400">/</span>
            </li>
            <li className="text-gray-700 font-medium" aria-current="page">
              {property.name}
            </li>
          </ol>
        </nav>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard 
          title="Total units" 
          value={stats.totalUnits} 
          icon={<UnitIcon />} 
          bgColor="bg-blue-50"
          textColor="text-blue-600"
        />
        <StatCard 
          title="Vacant units" 
          value={stats.vacantUnits} 
          icon={<VacantIcon />} 
          bgColor="bg-yellow-50"
          textColor="text-yellow-600"
        />
        <StatCard 
          title="Monthly Revenue" 
          value={formatCurrency(stats.monthlyRevenue)} 
          icon={<RevenueIcon />} 
          bgColor="bg-green-50"
          textColor="text-green-600"
        />
      </div>

      {/* Units Section */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
          <div className="w-1/3">
            {/* Left spacer */}
          </div>
          <h2 className="text-lg font-medium text-center text-gray-800 w-1/3">Units</h2>
          <div className="w-1/3 flex justify-end">
            <button
              onClick={handleAddNewUnit}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
            >
              <i className="fas fa-plus text-xs"></i>
              Add a new unit
            </button>
          </div>
        </div>

        {/* Unit Table */}
        <UnitTable 
          units={property.units || []} 
          loading={false} // We're already handling main page loading state
          error={null}
          onEdit={handleEditUnit} 
          onDelete={handleDeleteUnit} 
        />
      </div>
    </div>
  );
};

export default PropertyDetail; 