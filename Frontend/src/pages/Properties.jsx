import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  fetchProperties,
  createProperty,
  deleteProperty,
  updateProperty,
  fetchPropertyById,
} from "../utils/api";
import NewPropertyModal from "../components/NewPropertyModal";
import LoadingSpinner from "../components/LoadingSpinner";

// Utility functions
// Capitalize first letter of string
const capitalize = (str) => {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
};

const StatusCard = ({
  title,
  count,
  bgColor = "bg-white",
  textColor = "text-gray-900",
  onClick,
  icon,
}) => (
  <div
    className="bg-white overflow-hidden shadow rounded-lg cursor-pointer hover:shadow-md transition-shadow"
    onClick={onClick}
  >
    <div className="px-4 py-5 sm:p-6">
      <div className="flex items-center">
        <div className={`flex-shrink-0 ${bgColor} rounded-md p-3`}>{icon}</div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">
              {title}
            </dt>
            <dd>
              <div className={`text-lg font-medium ${textColor}`}>{count}</div>
            </dd>
          </dl>
        </div>
      </div>
    </div>
  </div>
);

const StatusBadge = ({ status }) => {
  const statusStyles = {
    ACTIVE: "bg-green-50 text-green-700",
    MAINTENANCE: "bg-orange-50 text-orange-700",
    VACANT: "bg-yellow-50 text-yellow-700",
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        statusStyles[status.toUpperCase()] || "bg-gray-100 text-gray-800"
      }`}
    >
      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current"></span>
      {status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()}
    </span>
  );
};

const PropertyTable = ({ properties, loading, error, onDelete, onEdit }) => {
  const navigate = useNavigate();

  if (loading) return <LoadingSpinner message="Loading properties..." />;

  if (error)
    return (
      <div className="p-8 text-center">
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4 max-w-md mx-auto">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
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

  if (!properties || properties.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        No properties found. Create your first property!
      </div>
    );
  }

  // Generate image placeholder based on property name
  const getImageInitial = (name) => {
    if (!name) return "";
    return name.charAt(0).toUpperCase();
  };

  const handleDelete = (e, propertyId) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this property?")) {
      onDelete(propertyId);
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Property
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Type
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Address
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Status
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Added
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {properties.map((property) => (
            <tr
              key={property.id}
              className="hover:bg-gray-50 cursor-pointer transition-colors"
              onClick={() => navigate(`/properties/${property.id}`)}
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center justify-start">
                  <div className="flex-shrink-0 h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 font-bold text-left">
                    {getImageInitial(property.name)}
                  </div>
                  <div className="ml-4">
                    <div className="text-sm font-medium text-gray-900 text-left">
                      {property.name}
                    </div>
                  </div>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-left">
                {capitalize(property.property_type)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-left">
                <div
                  className="max-w-xs truncate"
                  title={`${property.address}, ${property.city}, ${property.state}`}
                >
                  {property.address}, {property.city}, {property.state}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center">
                <div className="flex justify-center">
                  <StatusBadge status={property.status || "ACTIVE"} />
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-left">
                {new Date(property.created_at).toLocaleDateString()}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                <div className="flex justify-center space-x-3">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/properties/${property.id}`);
                    }}
                    className="text-indigo-600 hover:text-indigo-900"
                  >
                    View
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit(property.id);
                    }}
                    className="text-blue-600 hover:text-blue-900"
                  >
                    Edit
                  </button>
                  <button
                    onClick={(e) => handleDelete(e, property.id)}
                    className="text-red-600 hover:text-red-900"
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const Properties = () => {
  const navigate = useNavigate();
  const [properties, setProperties] = useState([]);
  const [filteredProperties, setFilteredProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusFilter, setStatusFilter] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusCounts, setStatusCounts] = useState({
    ACTIVE: 0,
    MAINTENANCE: 0,
    VACANT: 0,
    total: 0,
  });
  const [isDeleting, setIsDeleting] = useState(false);
  const [notification, setNotification] = useState(null);
  const [currentProperty, setCurrentProperty] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [sortOption, setSortOption] = useState(null);
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [filterOptions, setFilterOptions] = useState({
    propertyType: null,
    status: null,
    dateAdded: null,
  });

  // Refs for clicking outside filter/sort menus
  const filterMenuRef = useRef(null);
  const sortMenuRef = useRef(null);

  // Helper function to calculate status counts
  const calculateStatusCounts = (propertiesList) => {
    return propertiesList.reduce(
      (acc, property) => {
        acc.total++;
        const status = (property.status || "ACTIVE").toUpperCase(); // Default to active and ensure uppercase
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      },
      {
        ACTIVE: 0,
        MAINTENANCE: 0,
        VACANT: 0,
        total: 0,
      }
    );
  };

  useEffect(() => {
    fetchPropertiesData();
  }, []);

  useEffect(() => {
    // Close menus when clicking outside
    function handleClickOutside(event) {
      if (
        filterMenuRef.current &&
        !filterMenuRef.current.contains(event.target)
      ) {
        setShowFilterMenu(false);
      }
      if (sortMenuRef.current && !sortMenuRef.current.contains(event.target)) {
        setShowSortMenu(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  useEffect(() => {
    // Filter and sort properties based on search term, status filter and sort option
    if (!properties.length) return;

    let result = [...properties];

    // Apply status filter from cards or dropdown
    if (statusFilter) {
      result = result.filter(
        (p) =>
          (p.status || "ACTIVE").toUpperCase() === statusFilter.toUpperCase()
      );
    }

    // Apply search term filter
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(term) ||
          p.address.toLowerCase().includes(term) ||
          p.city.toLowerCase().includes(term) ||
          p.property_type.toLowerCase().includes(term)
      );
    }

    // Apply property type filter
    if (filterOptions.propertyType) {
      result = result.filter(
        (p) => p.property_type === filterOptions.propertyType
      );
    }

    // Apply status filter from dropdown (overrides card selection)
    if (filterOptions.status) {
      result = result.filter(
        (p) =>
          (p.status || "ACTIVE").toUpperCase() ===
          filterOptions.status.toUpperCase()
      );
    }

    // Apply date filter
    if (filterOptions.dateAdded) {
      const now = new Date();
      const cutoffDate = new Date();

      switch (filterOptions.dateAdded) {
        case "last-week":
          cutoffDate.setDate(now.getDate() - 7);
          break;
        case "last-month":
          cutoffDate.setMonth(now.getMonth() - 1);
          break;
        case "last-year":
          cutoffDate.setFullYear(now.getFullYear() - 1);
          break;
        default:
          break;
      }

      result = result.filter((p) => new Date(p.created_at) >= cutoffDate);
    }

    // Apply sorting
    if (sortOption) {
      result.sort((a, b) => {
        switch (sortOption) {
          case "name-asc":
            return a.name.localeCompare(b.name);
          case "name-desc":
            return b.name.localeCompare(a.name);
          case "type-asc":
            return a.property_type.localeCompare(b.property_type);
          case "type-desc":
            return b.property_type.localeCompare(a.property_type);
          case "status-asc":
            return (a.status || "ACTIVE")
              .toUpperCase()
              .localeCompare((b.status || "ACTIVE").toUpperCase());
          case "status-desc":
            return (b.status || "ACTIVE")
              .toUpperCase()
              .localeCompare((a.status || "ACTIVE").toUpperCase());
          case "date-asc":
            return new Date(a.created_at) - new Date(b.created_at);
          case "date-desc":
            return new Date(b.created_at) - new Date(a.created_at);
          default:
            return 0;
        }
      });
    }

    console.log("[Properties useEffect] Filtered/Sorted Properties:", result);
    setFilteredProperties(result);

    // Also update status counts whenever properties change
    const newCounts = calculateStatusCounts(result);
    console.log(
      "[Properties useEffect] Setting statusCounts state:",
      newCounts
    );
    setStatusCounts(newCounts);
  }, [properties, statusFilter, searchTerm, filterOptions, sortOption]);

  const fetchPropertiesData = async () => {
    try {
      setLoading(true);
      setError(null);

      console.log("Fetching properties...");
      const response = await fetchProperties();
      console.log("Properties response:", response);

      setProperties(response);
      setFilteredProperties(response);

      // Calculate status counts using the helper
      const counts = calculateStatusCounts(response);
      setStatusCounts(counts);
    } catch (err) {
      console.error("Error fetching properties:", err);
      setError(err.message || "Failed to load properties. Please try again.");
      // If fetch fails, set empty arrays to avoid undefined errors
      setProperties([]);
      setFilteredProperties([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProperty = async (propertyData) => {
    setIsSubmitting(true);
    try {
      let result;
      let updatedProperties; // Declare here to be accessible for both branches

      if (isEditing && currentProperty) {
        console.log(
          "[handleCreateProperty - Edit] Updating property:",
          currentProperty.id,
          "with data:",
          propertyData
        );
        // Update existing property
        result = await updateProperty(currentProperty.id, propertyData);
        console.log("[handleCreateProperty - Edit] API Response:", result);

        // Update the properties list
        updatedProperties = properties.map((p) =>
          p.id === currentProperty.id ? result : p
        );
        console.log(
          "[handleCreateProperty - Edit] Setting properties state:",
          updatedProperties
        );
        setProperties(updatedProperties);

        setNotification({
          type: "success",
          message: "Property updated successfully",
        });
      } else {
        console.log(
          "[handleCreateProperty - Create] Creating property with data:",
          propertyData
        );
        // Create new property
        result = await createProperty(propertyData);
        console.log("[handleCreateProperty - Create] API Response:", result);

        // Add new property to the list
        updatedProperties = [result, ...properties];
        console.log(
          "[handleCreateProperty - Create] Setting properties state:",
          updatedProperties
        );
        setProperties(updatedProperties);

        // Ensure filtered list and counts are updated using the final list
        // Apply current filters/sorting to the new list
        let finalFilteredProperties = [...updatedProperties];
        // Re-apply filters (this logic is duplicated from the useEffect hook, consider extracting)
        if (statusFilter) {
          finalFilteredProperties = finalFilteredProperties.filter(
            (p) =>
              (p.status || "ACTIVE").toUpperCase() ===
              statusFilter.toUpperCase()
          );
        }
        if (searchTerm.trim()) {
          const term = searchTerm.toLowerCase();
          finalFilteredProperties = finalFilteredProperties.filter(
            (p) =>
              p.name.toLowerCase().includes(term) ||
              p.address.toLowerCase().includes(term) ||
              p.city.toLowerCase().includes(term) ||
              p.property_type.toLowerCase().includes(term)
          );
        }
        if (filterOptions.propertyType) {
          finalFilteredProperties = finalFilteredProperties.filter(
            (p) => p.property_type === filterOptions.propertyType
          );
        }
        if (filterOptions.status) {
          finalFilteredProperties = finalFilteredProperties.filter(
            (p) =>
              (p.status || "ACTIVE").toUpperCase() ===
              filterOptions.status.toUpperCase()
          );
        }
        if (filterOptions.dateAdded) {
          const now = new Date();
          const cutoffDate = new Date();
          switch (filterOptions.dateAdded) {
            case "last-week":
              cutoffDate.setDate(now.getDate() - 7);
              break;
            case "last-month":
              cutoffDate.setMonth(now.getMonth() - 1);
              break;
            case "last-year":
              cutoffDate.setFullYear(now.getFullYear() - 1);
              break;
          }
          finalFilteredProperties = finalFilteredProperties.filter(
            (p) => new Date(p.created_at) >= cutoffDate
          );
        }
        // Re-apply sorting
        if (sortOption) {
          finalFilteredProperties.sort((a, b) => {
            switch (sortOption) {
              case "name-asc":
                return a.name.localeCompare(b.name);
              case "name-desc":
                return b.name.localeCompare(a.name);
              case "type-asc":
                return a.property_type.localeCompare(b.property_type);
              case "type-desc":
                return b.property_type.localeCompare(a.property_type);
              case "status-asc":
                return (a.status || "ACTIVE")
                  .toUpperCase()
                  .localeCompare((b.status || "ACTIVE").toUpperCase());
              case "status-desc":
                return (b.status || "ACTIVE")
                  .toUpperCase()
                  .localeCompare((a.status || "ACTIVE").toUpperCase());
              case "date-asc":
                return new Date(a.created_at) - new Date(b.created_at);
              case "date-desc":
                return new Date(b.created_at) - new Date(a.created_at);
              default:
                return 0;
            }
          });
        }
        console.log(
          "[handleCreateProperty] Setting filteredProperties state:",
          finalFilteredProperties
        );
        setFilteredProperties(finalFilteredProperties); // Update filtered properties

        // Update counts based on the complete updated list
        const newCounts = calculateStatusCounts(updatedProperties);
        console.log(
          "[handleCreateProperty] Setting statusCounts state:",
          newCounts
        );
        setStatusCounts(newCounts);

        setNotification({
          type: "success",
          message: "Property created successfully",
        });
      }

      // Reset state and close modal
      setIsModalOpen(false);
      setCurrentProperty(null);
      setIsEditing(false);

      // Clear notification after 3 seconds
      setTimeout(() => {
        setNotification(null);
      }, 3000);

      return result;
    } catch (error) {
      console.error("Error saving property:", error);
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditProperty = async (propertyId) => {
    try {
      setLoading(true);
      const property = await fetchPropertyById(propertyId);
      setCurrentProperty(property);
      setIsEditing(true);
      setIsModalOpen(true);
    } catch (error) {
      console.error("Error fetching property details:", error);
      setNotification({
        type: "error",
        message: "Failed to load property details",
      });

      setTimeout(() => {
        setNotification(null);
      }, 3000);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusCardClick = (status) => {
    setStatusFilter(
      status.toUpperCase() === statusFilter ? null : status.toUpperCase()
    );
  };

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
  };

  const clearFilters = () => {
    setFilterOptions({
      propertyType: null,
      status: null,
      dateAdded: null,
    });
    setStatusFilter(null);
    setSearchTerm("");
    setSortOption(null);
  };

  const handleDeleteProperty = async (propertyId) => {
    setIsDeleting(true);
    try {
      console.log(`[handleDeleteProperty] Deleting property ID: ${propertyId}`);
      // The delete endpoint returns 204 No Content which doesn't have a JSON body
      // so we need to handle it differently
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/properties/${propertyId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }
      );

      if (!response.ok && response.status !== 204) {
        let errorData;
        try {
          errorData = await response.json();
        } catch (e) {
          // Ignore if the response is not JSON
          errorData = { detail: `Request failed with status ${response.status}` };
        }
        throw new Error(errorData.detail || "Failed to delete property");
      }

      // Update properties list after successful deletion
      const newPropertiesList = properties.filter((p) => p.id !== propertyId);
      console.log(
        "[handleDeleteProperty] Setting properties state:",
        newPropertiesList
      );
      setProperties(newPropertiesList);

      // Show success notification
      setNotification({
        type: "success",
        message: "Property was successfully deleted",
      });

      // Clear notification after 3 seconds
      setTimeout(() => {
        setNotification(null);
      }, 3000);
    } catch (error) {
      console.error("Error deleting property:", error);

      // Show error notification
      setNotification({
        type: "error",
        message: error.message || "Failed to delete property. Please try again.",
      });

      // Clear notification after 3 seconds
      setTimeout(() => {
        setNotification(null);
      }, 3000);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleFilterToggle = () => {
    setShowFilterMenu(!showFilterMenu);
    setShowSortMenu(false);
  };

  const handleSortToggle = () => {
    setShowSortMenu(!showSortMenu);
    setShowFilterMenu(false);
  };

  const handleFilterSelect = (type, value) => {
    setFilterOptions((prev) => ({
      ...prev,
      [type]: value === prev[type] ? null : value,
    }));
  };

  const handleSortSelect = (option) => {
    setSortOption(option === sortOption ? null : option);
    setShowSortMenu(false);
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatusCard
          title="Active"
          count={statusCounts.ACTIVE}
          bgColor={statusFilter === "ACTIVE" ? "bg-green-100" : "bg-green-50"}
          textColor="text-green-600"
          onClick={() => handleStatusCardClick("ACTIVE")}
          icon={
            <svg
              className="h-6 w-6 text-green-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
        <StatusCard
          title="In-maintenance"
          count={statusCounts.MAINTENANCE}
          bgColor={
            statusFilter === "MAINTENANCE" ? "bg-orange-100" : "bg-orange-50"
          }
          textColor="text-orange-600"
          onClick={() => handleStatusCardClick("MAINTENANCE")}
          icon={
            <svg
              className="h-6 w-6 text-orange-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
        <StatusCard
          title="Vacant"
          count={statusCounts.VACANT}
          bgColor={statusFilter === "VACANT" ? "bg-yellow-100" : "bg-yellow-50"}
          textColor="text-yellow-600"
          onClick={() => handleStatusCardClick("VACANT")}
          icon={
            <svg
              className="h-6 w-6 text-yellow-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
        <StatusCard
          title="Total"
          count={statusCounts.total}
          onClick={clearFilters}
          icon={
            <svg
              className="h-6 w-6 text-indigo-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
          }
        />
      </div>

      {/* Notification */}
      {notification && (
        <div
          className={`mb-6 p-4 rounded-lg ${
            notification.type === "success"
              ? "bg-green-50 border border-green-200 text-green-700"
              : "bg-red-50 border border-red-200 text-red-700"
          }`}
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              {notification.type === "success" ? (
                <svg
                  className="h-5 w-5 text-green-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg
                  className="h-5 w-5 text-red-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium">{notification.message}</p>
            </div>
          </div>
        </div>
      )}

      {/* Properties Table */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <i className="fas fa-search text-gray-400"></i>
              </div>
              <input
                type="text"
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-600 focus:border-blue-600 sm:text-sm"
                placeholder="Search properties..."
                value={searchTerm}
                onChange={handleSearch}
              />
            </div>
            <div className="flex items-center gap-4">
              {(statusFilter ||
                Object.values(filterOptions).some((val) => val !== null)) && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">Filtered by:</span>
                  {statusFilter && <StatusBadge status={statusFilter} />}
                  {filterOptions.propertyType && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                      Type: {capitalize(filterOptions.propertyType)}
                    </span>
                  )}
                  {filterOptions.status && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                      Status: {capitalize(filterOptions.status.toLowerCase())}
                    </span>
                  )}
                  {filterOptions.dateAdded && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                      Date:{" "}
                      {filterOptions.dateAdded === "last-week"
                        ? "Last week"
                        : filterOptions.dateAdded === "last-month"
                        ? "Last month"
                        : "Last year"}
                    </span>
                  )}
                  <button
                    onClick={clearFilters}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    <i className="fas fa-times-circle"></i>
                  </button>
                </div>
              )}

              <button
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
                onClick={() => setIsModalOpen(true)}
              >
                <i className="fas fa-plus"></i>
                Add new property
              </button>

              {/* Filter Dropdown */}
              <div className="relative" ref={filterMenuRef}>
                <button
                  onClick={handleFilterToggle}
                  className={`inline-flex items-center px-4 py-2 border rounded-lg shadow-sm text-sm font-medium ${
                    Object.values(filterOptions).some((val) => val !== null)
                      ? "bg-blue-50 text-blue-700 border-blue-300"
                      : "text-gray-700 bg-white border-gray-300"
                  } hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
                >
                  <i className="fas fa-filter mr-2"></i>
                  Filter
                </button>

                {showFilterMenu && (
                  <div className="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 divide-y divide-gray-100 focus:outline-none z-10">
                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Property Type
                      </h3>
                      <div className="space-y-1">
                        {[
                          "residential",
                          "commercial",
                          "industrial",
                          "mixed-use",
                          "apartment-complex",
                        ].map((type) => (
                          <button
                            key={type}
                            onClick={() =>
                              handleFilterSelect("propertyType", type)
                            }
                            className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                              filterOptions.propertyType === type
                                ? "bg-blue-100 text-blue-800"
                                : "text-gray-700 hover:bg-gray-100"
                            }`}
                          >
                            {filterOptions.propertyType === type && (
                              <svg
                                className="mr-2 h-4 w-4 text-blue-500"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            )}
                            {capitalize(type)}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Status
                      </h3>
                      <div className="space-y-1">
                        {["ACTIVE", "MAINTENANCE", "VACANT"].map((status) => (
                          <button
                            key={status}
                            onClick={() => handleFilterSelect("status", status)}
                            className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                              filterOptions.status === status
                                ? "bg-blue-100 text-blue-800"
                                : "text-gray-700 hover:bg-gray-100"
                            }`}
                          >
                            {filterOptions.status === status && (
                              <svg
                                className="mr-2 h-4 w-4 text-blue-500"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            )}
                            {capitalize(status.toLowerCase())}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Date Added
                      </h3>
                      <div className="space-y-1">
                        {[
                          { id: "last-week", label: "Last Week" },
                          { id: "last-month", label: "Last Month" },
                          { id: "last-year", label: "Last Year" },
                        ].map((option) => (
                          <button
                            key={option.id}
                            onClick={() =>
                              handleFilterSelect("dateAdded", option.id)
                            }
                            className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                              filterOptions.dateAdded === option.id
                                ? "bg-blue-100 text-blue-800"
                                : "text-gray-700 hover:bg-gray-100"
                            }`}
                          >
                            {filterOptions.dateAdded === option.id && (
                              <svg
                                className="mr-2 h-4 w-4 text-blue-500"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            )}
                            {option.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="p-2">
                      <button
                        onClick={clearFilters}
                        className="w-full flex justify-center items-center px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md"
                      >
                        <i className="fas fa-times-circle mr-2"></i>
                        Clear All Filters
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Sort Dropdown */}
              <div className="relative" ref={sortMenuRef}>
                <button
                  onClick={handleSortToggle}
                  className={`inline-flex items-center px-4 py-2 border rounded-lg shadow-sm text-sm font-medium ${
                    sortOption
                      ? "bg-blue-50 text-blue-700 border-blue-300"
                      : "text-gray-700 bg-white border-gray-300"
                  } hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
                >
                  <i className="fas fa-sort mr-2"></i>
                  Sort
                </button>

                {showSortMenu && (
                  <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 divide-y divide-gray-100 focus:outline-none z-10">
                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Name
                      </h3>
                      <div className="space-y-1">
                        <button
                          onClick={() => handleSortSelect("name-asc")}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === "name-asc"
                              ? "bg-blue-100 text-blue-800"
                              : "text-gray-700 hover:bg-gray-100"
                          }`}
                        >
                          <i className="fas fa-sort-alpha-down mr-2"></i>A to Z
                        </button>
                        <button
                          onClick={() => handleSortSelect("name-desc")}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === "name-desc"
                              ? "bg-blue-100 text-blue-800"
                              : "text-gray-700 hover:bg-gray-100"
                          }`}
                        >
                          <i className="fas fa-sort-alpha-down-alt mr-2"></i>Z
                          to A
                        </button>
                      </div>
                    </div>

                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Type
                      </h3>
                      <div className="space-y-1">
                        <button
                          onClick={() => handleSortSelect("type-asc")}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === "type-asc"
                              ? "bg-blue-100 text-blue-800"
                              : "text-gray-700 hover:bg-gray-100"
                          }`}
                        >
                          <i className="fas fa-sort-alpha-down mr-2"></i>A to Z
                        </button>
                        <button
                          onClick={() => handleSortSelect("type-desc")}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === "type-desc"
                              ? "bg-blue-100 text-blue-800"
                              : "text-gray-700 hover:bg-gray-100"
                          }`}
                        >
                          <i className="fas fa-sort-alpha-down-alt mr-2"></i>Z
                          to A
                        </button>
                      </div>
                    </div>

                    <div className="p-2">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-3 pt-1">
                        Date Added
                      </h3>
                      <div className="space-y-1">
                        <button
                          onClick={() => handleSortSelect("date-desc")}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === "date-desc"
                              ? "bg-blue-100 text-blue-800"
                              : "text-gray-700 hover:bg-gray-100"
                          }`}
                        >
                          <i className="fas fa-sort-numeric-down-alt mr-2"></i>
                          Newest First
                        </button>
                        <button
                          onClick={() => handleSortSelect("date-asc")}
                          className={`group flex items-center w-full px-3 py-2 text-sm rounded-md ${
                            sortOption === "date-asc"
                              ? "bg-blue-100 text-blue-800"
                              : "text-gray-700 hover:bg-gray-100"
                          }`}
                        >
                          <i className="fas fa-sort-numeric-down mr-2"></i>
                          Oldest First
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        <PropertyTable
          properties={filteredProperties}
          loading={loading || isDeleting}
          error={error}
          onDelete={handleDeleteProperty}
          onEdit={handleEditProperty}
        />
      </div>

      {/* New/Edit Property Modal */}
      <NewPropertyModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setCurrentProperty(null);
          setIsEditing(false);
        }}
        onSubmit={handleCreateProperty}
        isLoading={isSubmitting}
        propertyData={currentProperty}
        isEditing={isEditing}
      />
    </div>
  );
};

export default Properties;
