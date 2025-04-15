import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { fetchPropertyById } from '../utils/api';

// Tabs component for property details
const Tabs = ({ activeTab, setActiveTab }) => {
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'units', label: 'Units' },
    { id: 'leases', label: 'Leases' },
    { id: 'maintenance', label: 'Maintenance' },
    { id: 'documents', label: 'Documents' },
    { id: 'history', label: 'History' },
  ];

  return (
    <div className="border-b border-gray-200 mb-6">
      <nav className="-mb-px flex space-x-8">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  );
};

// Status badge component
const StatusBadge = ({ status }) => {
  const statusStyles = {
    vacant: 'bg-yellow-50 text-yellow-700',
    rented: 'bg-green-50 text-green-700',
    'partially_rented': 'bg-blue-50 text-blue-700',
    maintenance: 'bg-orange-50 text-orange-700',
  };

  const statusLabels = {
    vacant: 'Vacant',
    rented: 'Rented',
    'partially_rented': 'Partially Rented',
    maintenance: 'In Maintenance',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyles[status] || 'bg-gray-100 text-gray-800'}`}>
      {statusLabels[status] || status}
    </span>
  );
};

// Photo gallery component
const PhotoGallery = ({ mainImage = null }) => {
  // Mock images for gallery
  const images = [
    'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?ixlib=rb-4.0.3',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?ixlib=rb-4.0.3',
    'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?ixlib=rb-4.0.3',
    'https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?ixlib=rb-4.0.3',
  ];

  // Use first image as main if not provided
  const displayMainImage = mainImage || images[0];

  return (
    <div className="grid grid-cols-3 gap-2 h-96">
      <div className="col-span-2 row-span-2 overflow-hidden rounded-lg">
        <img 
          src={displayMainImage} 
          alt="Main property view" 
          className="w-full h-full object-cover"
        />
      </div>
      <div className="grid grid-rows-2 gap-2">
        {images.slice(1, 3).map((img, index) => (
          <div key={index} className="overflow-hidden rounded-lg">
            <img 
              src={img} 
              alt={`Property view ${index + 2}`} 
              className="w-full h-full object-cover"
            />
          </div>
        ))}
      </div>
      <div className="relative overflow-hidden rounded-lg">
        <img 
          src={images[3]} 
          alt="Property view 4" 
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-black bg-opacity-40 flex items-center justify-center">
          <button className="text-white text-sm font-medium px-3 py-1 bg-black bg-opacity-50 rounded">
            See all photos
          </button>
        </div>
      </div>
    </div>
  );
};

// PropertyInfo component that shows address, property details, etc.
const PropertyInfo = ({ property }) => {
  return (
    <div className="mt-6 space-y-8">
      <div className="flex justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{property.name}</h2>
          <p className="text-gray-600">{property.address}, {property.city}, {property.state} {property.zip_code}</p>
          <div className="mt-2 flex items-center space-x-2">
            <StatusBadge status={property.status || 'vacant'} />
            <span className="text-gray-500 text-sm">
              {property.property_type}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="border rounded-lg p-4">
          <div className="text-sm text-gray-500">RENT/MONTH ($)</div>
          <div className="text-xl font-semibold mt-1">$500</div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="text-sm text-gray-500">BEDROOMS</div>
          <div className="text-xl font-semibold mt-1">8</div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="text-sm text-gray-500">BATHROOMS</div>
          <div className="text-xl font-semibold mt-1">5</div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="text-sm text-gray-500">MIN CONTRACT</div>
          <div className="text-xl font-semibold mt-1">1yr</div>
        </div>
      </div>
    </div>
  );
};

// LandlordInfo component
const LandlordInfo = ({ owner }) => {
  if (!owner) return null;

  return (
    <div className="border rounded-lg p-6 mt-8">
      <h3 className="text-lg font-semibold mb-4">Landlord</h3>
      <div className="flex items-center space-x-4">
        <div className="h-12 w-12 rounded-full overflow-hidden bg-gray-200">
          {owner.profile_image_url ? (
            <img src={owner.profile_image_url} alt={`${owner.first_name} ${owner.last_name}`} className="h-full w-full object-cover" />
          ) : (
            <div className="h-full w-full flex items-center justify-center bg-blue-100 text-blue-800 font-bold text-xl">
              {owner.first_name.charAt(0)}{owner.last_name.charAt(0)}
            </div>
          )}
        </div>
        <div>
          <h4 className="font-medium text-gray-900">{owner.first_name} {owner.last_name}</h4>
          <p className="text-sm text-gray-500">Joined: {new Date().toLocaleDateString()}</p>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex items-center space-x-2">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M2 5a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V5zm2-2a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4z" clipRule="evenodd" />
            <path d="M10 9a2 2 0 100-4 2 2 0 000 4zm0 2a4 4 0 100-8 4 4 0 000 8z" />
          </svg>
          <span className="text-gray-700">Phone:</span>
          <a href={`tel:${owner.phone}`} className="text-blue-600 hover:underline">{owner.phone || 'N/A'}</a>
        </div>

        <div className="flex items-center space-x-2">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
            <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
            <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
          </svg>
          <span className="text-gray-700">Email:</span>
          <a href={`mailto:${owner.email}`} className="text-blue-600 hover:underline">{owner.email}</a>
        </div>

        <div className="flex items-center space-x-2">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
          </svg>
          <span className="text-gray-700">Location:</span>
          <span className="text-gray-900">Apartment 20, 543 KPS, Quebec, Canada</span>
        </div>
      </div>

      <div className="mt-4">
        <button className="text-blue-600 hover:text-blue-800 font-medium">
          View landlord profile
        </button>
      </div>
    </div>
  );
};

// Property amenities component
const PropertyAmenities = () => {
  const amenities = [
    { name: 'Kitchen', available: true },
    { name: 'WiFi', available: true },
    { name: 'Pool', available: false },
    { name: 'TV', available: true },
    { name: 'Air Conditioner', available: true },
    { name: 'Water Heater', available: true },
  ];

  return (
    <div className="mt-8">
      <h3 className="text-lg font-semibold mb-4">Amenities</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {amenities.map((amenity, index) => (
          <div key={index} className="flex items-center space-x-2">
            <div className={`rounded-full h-6 w-6 flex items-center justify-center ${amenity.available ? 'bg-green-100' : 'bg-gray-100'}`}>
              {amenity.available ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-green-600" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            <span className={amenity.available ? 'text-gray-900' : 'text-gray-400'}>
              {amenity.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Property overview component
const PropertyOverview = ({ property }) => {
  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold mb-4">Overview</h3>
        <p className="text-gray-700">
          {property?.description || 
            "This room has a view of about 30 square meters and the upper bathroom can be used alone. The garden is also available to guests. Utensils very easy to reach for express train ISO, which is about 10 min away. Mainaustrasse is a quiet neighborhood and as soon as you turn 2 very nice streets you are in the center of Konstanz. The new Kreuzlingen is a central point for many destinations."}
        </p>
        <p className="text-gray-700 mt-4">
          The living space is just right for a short stay. The bathroom, which is completely newly renovated, can be used completely alone. Of course, so is the room. If several people arrive, the air mattress will also be cheap, which is located in the room.
        </p>
        <button className="text-blue-600 hover:text-blue-800 font-medium mt-2">
          Show more
        </button>
      </div>

      <PropertyAmenities />
    </div>
  );
};

const PropertyDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch property data
  useEffect(() => {
    const loadProperty = async () => {
      try {
        setLoading(true);
        const data = await fetchPropertyById(id);
        setProperty(data);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching property:', err);
        setError(err.message || 'Failed to load property details');
        setLoading(false);
      }
    };

    loadProperty();
  }, [id]);

  // Loading state
  if (loading) {
    return (
      <div className="p-6 flex justify-center items-center min-h-screen-navbar">
        <div className="text-center">
          <div className="spinner-border animate-spin inline-block w-8 h-8 border-4 rounded-full text-blue-600 border-t-transparent" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2 text-gray-600">Loading property details...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
        <button 
          onClick={() => navigate('/properties')}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Back to Properties
        </button>
      </div>
    );
  }

  if (!property) {
    return (
      <div className="p-6 max-w-6xl mx-auto text-center">
        <h2 className="text-2xl font-bold mb-4">Property Not Found</h2>
        <p className="mb-6">The property you're looking for doesn't exist or you don't have permission to view it.</p>
        <button 
          onClick={() => navigate('/properties')}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Back to Properties
        </button>
      </div>
    );
  }

  // Main render with property data
  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Breadcrumbs */}
      <nav className="mb-4 flex" aria-label="Breadcrumb">
        <ol className="inline-flex items-center space-x-1 md:space-x-3">
          <li className="inline-flex items-center">
            <Link to="/properties" className="text-gray-500 hover:text-gray-700">
              Properties
            </Link>
          </li>
          <li>
            <div className="flex items-center">
              <svg className="w-6 h-6 text-gray-400" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd"></path>
              </svg>
              <span className="text-gray-800 font-medium ml-1">Property #{property.id}</span>
            </div>
          </li>
        </ol>
      </nav>

      {/* Main content */}
      <PhotoGallery />
      <PropertyInfo property={property} />
      
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2">
          <Tabs activeTab={activeTab} setActiveTab={setActiveTab} />
          
          {activeTab === 'overview' && <PropertyOverview property={property} />}
          {activeTab === 'units' && <div>Units content coming soon...</div>}
          {activeTab === 'leases' && <div>Leases content coming soon...</div>}
          {activeTab === 'maintenance' && <div>Maintenance content coming soon...</div>}
          {activeTab === 'documents' && <div>Documents content coming soon...</div>}
          {activeTab === 'history' && <div>History content coming soon...</div>}
        </div>
        
        <div>
          <LandlordInfo owner={property.owner} />
        </div>
      </div>
    </div>
  );
};

export default PropertyDetail; 