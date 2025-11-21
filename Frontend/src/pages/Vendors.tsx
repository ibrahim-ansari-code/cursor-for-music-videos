import React, { useState, useMemo } from "react";
import { toast } from "react-toastify";
import * as Sentry from "@sentry/react";
import * as Select from "@radix-ui/react-select";
import { ChevronDown, Check } from "lucide-react";
import type { VendorContact } from "../types/vendor";
import {
  useVendors,
  useCreateVendor,
  useUpdateVendor,
  useToggleVendorFavorite,
  useDeleteVendor,
  useBulkDeleteVendors,
} from "../hooks/useVendorQueries";
import VendorTable from "../components/vendors/VendorTable";
import VendorModal from "../components/vendors/VendorModal";
import { useSubscriptionGuard } from "../hooks/useSubscriptionGuard";

const Vendors: React.FC = () => {
  // Subscription guard for premium features
  const guardAction = useSubscriptionGuard({ featureName: 'creating vendors' });

  // Local UI state
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [tradeFilter, setTradeFilter] = useState<string>("");
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(20);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingVendor, setEditingVendor] = useState<VendorContact | null>(null);
  const [viewingVendor, setViewingVendor] = useState<VendorContact | null>(null);
  const [selectedVendors, setSelectedVendors] = useState<Set<number>>(new Set());

  // Build query parameters
  const queryParams = useMemo(() => {
    const params: Record<string, any> = {
      limit: pageSize,
      offset: (currentPage - 1) * pageSize,
    };

    if (searchTerm) params.search = searchTerm;
    if (tradeFilter) params.trade_category = tradeFilter;
    if (activeFilter !== undefined) params.is_active = activeFilter;

    return params;
  }, [searchTerm, tradeFilter, activeFilter, currentPage, pageSize]);

  // TanStack Query hooks
  const { data: vendorsData, isLoading, error } = useVendors(queryParams);
  const createVendorMutation = useCreateVendor();
  const updateVendorMutation = useUpdateVendor();
  const toggleFavoriteMutation = useToggleVendorFavorite();
  const deleteVendorMutation = useDeleteVendor();
  const bulkDeleteVendorMutation = useBulkDeleteVendors();

  // Extract data from query response and sort favorites first
  const vendors = useMemo(() => {
    const vendorList = vendorsData?.vendors || [];
    return [...vendorList].sort((a, b) => {
      if (a.is_favorite === b.is_favorite) return 0;
      return a.is_favorite ? -1 : 1;
    });
  }, [vendorsData]);
  const totalCount = vendorsData?.total ?? 0;
  const hasMore = useMemo(() => currentPage * pageSize < totalCount, [currentPage, pageSize, totalCount]);

  // Reset to first page when filters change
  React.useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, tradeFilter, activeFilter]);

  // Clear selection when vendors change
  React.useEffect(() => {
    const currentVendorIds = new Set(vendors.map((v) => v.id));
    setSelectedVendors((prev) => {
      const filtered = Array.from(prev).filter((id) => currentVendorIds.has(id));
      return filtered.length !== prev.size ? new Set(filtered) : prev;
    });
  }, [vendors]);

  const handleModalSubmit = async (formData: any) => {
    try {
      if (editingVendor) {
        await updateVendorMutation.mutateAsync({
          vendorId: editingVendor.id,
          data: formData,
        });
        toast.success("Vendor updated successfully!");
      } else {
        await createVendorMutation.mutateAsync(formData);
        toast.success("Vendor created successfully!");
      }
      closeModal();
      setCurrentPage(1);
    } catch (error: any) {
      console.error("Failed to save vendor:", error);
      toast.error(error?.message || "Failed to save vendor");
      throw error;
    }
  };

  const handleEdit = (vendor: VendorContact) => {
    setEditingVendor(vendor);
    setViewingVendor(null);
    setIsModalOpen(true);
  };

  const handleView = (vendor: VendorContact) => {
    setViewingVendor(vendor);
    setEditingVendor(null);
    setIsModalOpen(true);
  };

  const handleToggleFavorite = async (vendorId: number, currentFavoriteStatus: boolean) => {
    try {
      // Optimistic update happens instantly in useToggleVendorFavorite hook
      await toggleFavoriteMutation.mutateAsync({
        vendorId,
        isFavorite: !currentFavoriteStatus,
      });
      // Optional: Lighter toast for better UX (or remove entirely since change is instant)
      toast.success(
        currentFavoriteStatus ? "Removed from favorites" : "Added to favorites",
        { autoClose: 2000 }
      );
    } catch (error: any) {
      console.error("Failed to update favorite status:", error);
      toast.error(error?.message || "Failed to update favorite status");
    }
  };

  const handleDelete = async (vendorId: number) => {
    if (window.confirm("Are you sure you want to delete this vendor?")) {
      try {
        await deleteVendorMutation.mutateAsync(vendorId);
        toast.success("Vendor deleted successfully!");
      } catch (error: any) {
        console.error("Failed to delete vendor:", error);
        toast.error(error?.message || "Failed to delete vendor");
      }
    }
  };

  const handleBulkDelete = async () => {
    if (selectedVendors.size === 0) return;

    const vendorIdsArray = Array.from(selectedVendors);

    if (
      window.confirm(
        `Are you sure you want to delete ${vendorIdsArray.length} selected vendor${vendorIdsArray.length !== 1 ? "s" : ""}?`
      )
    ) {
      await Sentry.startSpan(
        {
          op: "ui.click",
          name: "Bulk Delete Vendors",
        },
        async (span) => {
          span.setAttribute("vendorCount", vendorIdsArray.length);

          try {
            Sentry.logger.info("Bulk deleting vendors after confirmation", {
              vendorCount: vendorIdsArray.length,
            });

            await bulkDeleteVendorMutation.mutateAsync(vendorIdsArray);

            toast.success(
              `${vendorIdsArray.length} vendor${vendorIdsArray.length !== 1 ? "s" : ""} deleted successfully!`
            );

            setSelectedVendors(new Set());
          } catch (error: any) {
            const errorMessage =
              error?.response?.data?.detail ||
              error?.message ||
              "Failed to delete selected vendors";

            toast.error(errorMessage);

            Sentry.captureException(error, {
              tags: {
                component: "Vendors",
                action: "bulk_delete_vendors",
                feature: "vendors",
                operation: "bulk_delete",
              },
              contexts: {
                bulkDelete: {
                  vendorCount: vendorIdsArray.length,
                },
              },
            });
          }
        }
      );
    }
  };

  const openModalForNew = guardAction(() => {
    setEditingVendor(null);
    setViewingVendor(null);
    setIsModalOpen(true);
  });

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingVendor(null);
    setViewingVendor(null);
  };

  if (error) {
    return (
      <div className="p-6 min-h-screen dark-bg transition-colors duration-300">
        <div className="p-4 text-center bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-700">
          Error: {error instanceof Error ? error.message : String(error)}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[1600px] mx-auto bg-gray-50 dark:bg-gray-900 min-h-screen transition-colors duration-200">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Vendor Contacts</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Manage your preferred vendors and contractors for maintenance work
        </p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm overflow-hidden border border-gray-200 dark:border-gray-700">
        {/* Filters and Search Toolbar */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-600 transition-colors duration-300">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
            {/* Search Input */}
            <div className="relative flex-1 max-w-md w-full">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <i className="fas fa-search text-gray-400 dark:text-gray-500"></i>
              </div>
              <input
                type="text"
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg leading-5 bg-white dark:bg-gray-700 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:placeholder-gray-400 dark:focus:placeholder-gray-500 focus:ring-1 focus:ring-blue-600 dark:focus:ring-blue-500 focus:border-blue-600 dark:focus:border-blue-500 sm:text-sm text-gray-900 dark:text-gray-100"
                placeholder="Search vendors..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            {/* Filter Controls */}
            <div className="flex items-center gap-3 w-full sm:w-auto">
              {/* Trade Category Filter */}
              <Select.Root 
                value={tradeFilter || "ALL"} 
                onValueChange={(value) => setTradeFilter(value === "ALL" ? "" : value)}
              >
                <Select.Trigger className="w-48 px-3 py-2 pr-9 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 flex items-center text-sm hover:border-gray-400 dark:hover:border-gray-500 transition-colors relative">
                  <Select.Value asChild>
                    <span className="truncate block flex-1 text-left">
                      {tradeFilter || "All Trades"}
                    </span>
                  </Select.Value>
                  <Select.Icon className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                    <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                  </Select.Icon>
                </Select.Trigger>
                <Select.Portal>
                  <Select.Content className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
                    <Select.Viewport className="p-1">
                      <Select.Item value="ALL" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>All Trades</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                      <Select.Item value="Plumber" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>Plumber</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                      <Select.Item value="Electrician" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>Electrician</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                      <Select.Item value="HVAC" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>HVAC</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                      <Select.Item value="Carpenter" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>Carpenter</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                      <Select.Item value="General Contractor" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>General Contractor</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                      <Select.Item value="Painter" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>Painter</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                      <Select.Item value="Roofer" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>Roofer</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                      <Select.Item value="Locksmith" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>Locksmith</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                      <Select.Item value="Other" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>Other</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                    </Select.Viewport>
                  </Select.Content>
                </Select.Portal>
              </Select.Root>

              {/* Active Status Filter */}
              <Select.Root
                value={activeFilter === undefined ? "ALL" : String(activeFilter)}
                onValueChange={(value) =>
                  setActiveFilter(value === "ALL" ? undefined : value === "true")
                }
              >
                <Select.Trigger className="w-40 px-3 py-2 pr-9 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 flex items-center text-sm hover:border-gray-400 dark:hover:border-gray-500 transition-colors relative">
                  <Select.Value asChild>
                    <span className="truncate block flex-1 text-left">
                      {activeFilter === undefined
                        ? "All Status"
                        : activeFilter
                        ? "Active Only"
                        : "Inactive Only"}
                    </span>
                  </Select.Value>
                  <Select.Icon className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                    <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                  </Select.Icon>
                </Select.Trigger>
                <Select.Portal>
                  <Select.Content className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
                    <Select.Viewport className="p-1">
                      <Select.Item value="ALL" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>All Status</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                      <Select.Item value="true" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>Active Only</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                      <Select.Item value="false" className="relative flex items-center px-8 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 outline-none">
                        <Select.ItemText>Inactive Only</Select.ItemText>
                        <Select.ItemIndicator className="absolute left-2 inline-flex items-center">
                          <Check className="h-4 w-4" />
                        </Select.ItemIndicator>
                      </Select.Item>
                    </Select.Viewport>
                  </Select.Content>
                </Select.Portal>
              </Select.Root>

              <button
                className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors duration-300"
                onClick={openModalForNew}
              >
                <i className="fas fa-plus"></i>
                New Vendor
              </button>
            </div>
          </div>
        </div>

        {/* Bulk Actions */}
        {selectedVendors.size > 0 && (
          <div className="px-4 py-3 bg-blue-50 dark:bg-blue-900/20 border-b border-gray-200 dark:border-gray-600">
            <button
              type="button"
              onClick={handleBulkDelete}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-lg text-sm font-medium text-white bg-red-600 hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600 transition-colors duration-150"
            >
              <i className="fas fa-trash mr-2"></i>
              Delete Selected ({selectedVendors.size})
            </button>
          </div>
        )}

        {/* Vendor Table */}
        <VendorTable
          vendors={vendors}
          isLoading={isLoading}
          selectedVendors={selectedVendors}
          onToggleSelect={(vendorId) => {
            setSelectedVendors((prev) => {
              const next = new Set(prev);
              if (next.has(vendorId)) {
                next.delete(vendorId);
              } else {
                next.add(vendorId);
              }
              return next;
            });
          }}
          onToggleSelectAll={() => {
            if (vendors.every((v) => selectedVendors.has(v.id))) {
              setSelectedVendors(new Set());
            } else {
              setSelectedVendors(new Set(vendors.map((v) => v.id)));
            }
          }}
          onToggleFavorite={handleToggleFavorite}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onView={handleView}
        />
      </div>

        {/* Pagination */}
        {totalCount > pageSize && (
          <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-600 flex items-center justify-between">
            <div className="text-sm text-gray-700 dark:text-gray-300">
              Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalCount)} of {totalCount} vendors
            </div>
            <div className="flex space-x-2">
              <button
                type="button"
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <span className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100">
                Page {currentPage} of {Math.ceil(totalCount / pageSize)}
              </span>
              <button
                type="button"
                onClick={() => setCurrentPage((prev) => prev + 1)}
                disabled={!hasMore}
                className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
        </div>
      )}

      {/* Vendor Modal */}
      <VendorModal
        isOpen={isModalOpen}
        onClose={closeModal}
        onSubmit={handleModalSubmit}
        vendor={editingVendor || viewingVendor}
        isViewing={!!viewingVendor}
      />
    </div>
  );
};

export default Vendors;

