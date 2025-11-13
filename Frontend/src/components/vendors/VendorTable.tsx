import React from "react";
import { Star } from "lucide-react";
import type { VendorContact } from "../../types/vendor";
import { formatPhoneNumber } from "../../utils/validation";

interface VendorTableProps {
  vendors: VendorContact[];
  isLoading: boolean;
  selectedVendors: Set<number>;
  onToggleSelect: (vendorId: number) => void;
  onToggleSelectAll: () => void;
  onToggleFavorite: (vendorId: number, currentFavoriteStatus: boolean) => void;
  onEdit: (vendor: VendorContact) => void;
  onDelete: (vendorId: number) => void;
  onView: (vendor: VendorContact) => void;
}

const VendorTable: React.FC<VendorTableProps> = ({
  vendors,
  isLoading,
  selectedVendors,
  onToggleSelect,
  onToggleSelectAll,
  onToggleFavorite,
  onEdit,
  onDelete,
  onView,
}) => {
  const allSelected = vendors.length > 0 && vendors.every((v) => selectedVendors.has(v.id));
  const someSelected = vendors.some((v) => selectedVendors.has(v.id));

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (vendors.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-gray-400">
        No vendors found. Create your first vendor!
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="data-table min-w-full">
        <thead>
          <tr>
            <th scope="col" className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">
              <input
                type="checkbox"
                checked={allSelected}
                ref={(el) => {
                  if (el) el.indeterminate = someSelected && !allSelected;
                }}
                onChange={onToggleSelectAll}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 rounded cursor-pointer"
              />
            </th>
            <th scope="col" className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Company</th>
            <th scope="col" className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Trade</th>
            <th scope="col" className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Contact</th>
            <th scope="col" className="px-6 py-4 text-left font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Rating</th>
            <th scope="col" className="px-6 py-4 text-center font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Status</th>
            <th scope="col" className="px-6 py-4 text-center font-semibold text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800">Actions</th>
          </tr>
        </thead>
        <tbody>
          {vendors.map((vendor) => (
            <tr key={vendor.id} onClick={() => onView(vendor)} className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
              <td className="px-6 py-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center space-x-2.5">
                <input
                  type="checkbox"
                  checked={selectedVendors.has(vendor.id)}
                  onChange={() => onToggleSelect(vendor.id)}
                  onClick={(e) => e.stopPropagation()}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 rounded cursor-pointer"
                />
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleFavorite(vendor.id, vendor.is_favorite);
                    }}
                    className={`transition-all duration-200 hover:scale-110 transform ${
                      vendor.is_favorite
                        ? "text-yellow-500 hover:text-yellow-600"
                        : "text-gray-300 dark:text-gray-600 hover:text-yellow-400 dark:hover:text-yellow-500"
                    }`}
                    title={vendor.is_favorite ? "Remove from favorites" : "Add to favorites"}
                    aria-label={vendor.is_favorite ? "Remove from favorites" : "Add to favorites"}
                  >
                    <Star 
                      className="h-4 w-4" 
                      fill={vendor.is_favorite ? "currentColor" : "none"}
                      aria-hidden="true"
                    />
                  </button>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center">
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {vendor.company_name}
                    </div>
                    {vendor.notes && (
                      <div className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                        {vendor.notes}
                      </div>
                    )}
                  </div>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200">
                  {vendor.trade_category}
                </span>
              </td>
              <td className="px-6 py-4">
                <div className="flex flex-col justify-center space-y-1">
                  {(() => {
                    const numericPhone = (vendor.phone || '').replace(/[^\d+]/g, '');
                    return (
                      <a
                        href={`tel:${numericPhone}`}
                        className="phone-link text-sm font-medium"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {formatPhoneNumber(vendor.phone)}
                      </a>
                    );
                  })()}
                  {vendor.email && (
                    <a
                      href={`mailto:${vendor.email}`}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {vendor.email}
                    </a>
                  )}
                  {vendor.contact_person && (
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {vendor.contact_person}
                    </span>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                {vendor.personal_rating ? (
                  <div className="flex items-center text-gray-500 dark:text-gray-400">
                    <span className="text-yellow-500">{"★".repeat(vendor.personal_rating)}</span>
                    <span className="text-gray-300 dark:text-gray-600">
                      {"★".repeat(5 - vendor.personal_rating)}
                    </span>
                    <span className="ml-1">
                      ({vendor.personal_rating})
                    </span>
                  </div>
                ) : (
                  <span className="text-gray-400 dark:text-gray-500">No rating</span>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center">
                <span
                  className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    vendor.is_active
                      ? "bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-400"
                  }`}
                >
                  {vendor.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                <div className="inline-flex space-x-3">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onView(vendor);
                    }}
                    className="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300"
                    title="View"
                  >
                    <i className="fas fa-eye"></i>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit(vendor);
                    }}
                    className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300"
                    title="Edit"
                  >
                    <i className="fas fa-edit"></i>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(vendor.id);
                    }}
                    className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300"
                    title="Delete"
                  >
                    <i className="fas fa-trash"></i>
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

export default VendorTable;
