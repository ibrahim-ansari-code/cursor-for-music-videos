/**
 * Skeleton loading component for maintenance requests
 * Provides a loading state while maintenance data is being fetched
 */
const SkeletonMaintenanceLoading = () => {
  return (
    <div className="bg-white rounded-lg shadow border border-gray-200">
      <div className="p-6">
        {/* Page Header skeleton */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <div className="h-6 bg-gray-200 rounded w-48 animate-pulse mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-64 animate-pulse"></div>
          </div>
          <div className="h-10 bg-gray-200 rounded w-32 animate-pulse"></div>
        </div>

        <div className="space-y-6">
          {/* Your Requests header skeleton */}
          <div className="bg-gray-50 flex items-center justify-between p-4 rounded-lg">
            <div className="h-6 bg-gray-200 rounded w-32 animate-pulse"></div>
            <div className="flex gap-2">
              <div className="h-8 bg-gray-200 rounded w-16 animate-pulse"></div>
              <div className="h-8 bg-gray-200 rounded w-20 animate-pulse"></div>
              <div className="h-8 bg-gray-200 rounded w-20 animate-pulse"></div>
            </div>
          </div>

          {/* Table skeleton */}
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            {/* Table header */}
            <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
              <div className="h-5 bg-gray-200 rounded w-32 animate-pulse"></div>
            </div>

            {/* Table rows skeleton */}
            <div className="divide-y divide-gray-200">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="px-6 py-4 flex items-center gap-6">
                  <div className="flex-1 h-12 bg-gray-200 rounded animate-pulse"></div>
                  <div className="w-32 h-4 bg-gray-200 rounded animate-pulse"></div>
                  <div className="w-32 h-4 bg-gray-200 rounded animate-pulse"></div>
                  <div className="w-24 h-6 bg-gray-200 rounded-full animate-pulse"></div>
                  <div className="w-24 h-4 bg-gray-200 rounded animate-pulse"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SkeletonMaintenanceLoading;