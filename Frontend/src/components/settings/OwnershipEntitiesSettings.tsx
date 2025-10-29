import React, { useState, useEffect, useMemo } from 'react';
import { toast } from 'react-toastify';
import * as Sentry from '@sentry/react';
import { Briefcase, Plus, Trash2, AlertCircle, Edit2, Mail, Phone, MapPin, Search, Filter, X } from 'lucide-react';
import {
  fetchOwnershipEntities,
  deleteOwnershipEntity,
  type OwnershipEntity,
  ENTITY_TYPES,
  type EntityType
} from '../../utils/api/ownershipEntities';
import NewOwnershipEntityModal from '../ownership/NewOwnershipEntityModal';
import EditOwnershipEntityModal from '../ownership/EditOwnershipEntityModal';

const OwnershipEntitiesSettings: React.FC = () => {
  const [entities, setEntities] = useState<OwnershipEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingEntity, setEditingEntity] = useState<OwnershipEntity | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<EntityType | 'all'>('all');

  // Load entities on mount
  useEffect(() => {
    loadEntities();
  }, []);

  const loadEntities = async () => {
    try {
      setLoading(true);
      Sentry.logger.debug('Loading ownership entities for settings');
      const response = await fetchOwnershipEntities({ pageSize: 100 });
      setEntities(response.entities || []);
      Sentry.logger.debug('Ownership entities loaded', { count: response.entities?.length || 0 });
    } catch (error) {
      console.error('Failed to load ownership entities:', error);
      Sentry.captureException(error, {
        tags: {
          component: 'OwnershipEntitiesSettings',
          action: 'load_entities',
          feature: 'settings',
        },
      });
      toast.error('Failed to load ownership entities');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = (newEntity: OwnershipEntity) => {
    Sentry.logger.info('Ownership entity created from settings', {
      entityId: newEntity.id,
      entityType: newEntity.entity_type,
    });
    setEntities(prev => [...prev, newEntity]);
    setIsCreateModalOpen(false);
  };

  const handleEdit = (entity: OwnershipEntity) => {
    setEditingEntity(entity);
    setIsEditModalOpen(true);
  };

  const handleUpdate = (updatedEntity: OwnershipEntity) => {
    Sentry.logger.info('Ownership entity updated from settings', {
      entityId: updatedEntity.id,
      entityType: updatedEntity.entity_type,
    });
    setEntities(prev => prev.map(e => e.id === updatedEntity.id ? updatedEntity : e));
    setIsEditModalOpen(false);
    setEditingEntity(null);
  };

  const handleDelete = async (entity: OwnershipEntity) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${entity.name}"?\n\nNote: This will not affect existing properties that use this entity.`
    );

    if (!confirmed) return;

    setDeletingId(entity.id);
    try {
      await Sentry.startSpan(
        {
          op: 'ownership.entity.delete',
          name: 'Delete Ownership Entity',
        },
        async (span) => {
          span.setAttribute('entityId', entity.id);
          span.setAttribute('entityName', entity.name);

          Sentry.logger.info('Deleting ownership entity', {
            entityId: entity.id,
            entityName: entity.name,
          });

          await deleteOwnershipEntity(entity.id);

          setEntities(prev => prev.filter(e => e.id !== entity.id));
          toast.success(`Ownership entity "${entity.name}" deleted successfully`);

          Sentry.logger.info('Ownership entity deleted successfully', {
            entityId: entity.id,
          });
        }
      );
    } catch (error) {
      console.error('Failed to delete ownership entity:', error);
      Sentry.captureException(error, {
        tags: {
          component: 'OwnershipEntitiesSettings',
          action: 'delete_entity',
          feature: 'settings',
        },
        contexts: {
          business: {
            entityId: entity.id,
            entityName: entity.name,
          },
        },
      });
      toast.error('Failed to delete ownership entity');
    } finally {
      setDeletingId(null);
    }
  };

  const getEntityTypeLabel = (entityType: string) => {
    return ENTITY_TYPES.find(type => type.value === entityType)?.label || entityType;
  };

  // Filter and search entities
  const filteredEntities = useMemo(() => {
    let filtered = entities;

    // Filter by type
    if (filterType !== 'all') {
      filtered = filtered.filter(entity => entity.entity_type === filterType);
    }

    // Search by name, legal name, or tax ID
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(entity =>
        entity.name.toLowerCase().includes(query) ||
        entity.legal_name?.toLowerCase().includes(query) ||
        entity.tax_id?.toLowerCase().includes(query) ||
        entity.contact_email?.toLowerCase().includes(query)
      );
    }

    return filtered;
  }, [entities, filterType, searchQuery]);

  const clearFilters = () => {
    setSearchQuery('');
    setFilterType('all');
  };

  // Render loading skeleton cards instead of full-page spinner
  const renderLoadingSkeleton = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden animate-pulse"
        >
          {/* Header skeleton */}
          <div className="p-5 pb-4 bg-gradient-to-br from-gray-50 to-white dark:from-gray-800 dark:to-gray-800 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-gray-200 dark:bg-gray-700"></div>
              <div className="flex-1 space-y-2">
                <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
              </div>
            </div>
          </div>

          {/* Content skeleton */}
          <div className="p-5 space-y-3">
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-4/5"></div>
          </div>

          {/* Footer skeleton */}
          <div className="px-5 py-3 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end gap-2">
            <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
            <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <Briefcase className="h-6 w-6 text-green-600 dark:text-green-400" />
            Ownership Entities
            {entities.length > 0 && (
              <span className="text-base font-normal text-gray-500 dark:text-gray-400">
                ({filteredEntities.length} of {entities.length})
              </span>
            )}
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Manage the entities that own your properties
          </p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium text-sm whitespace-nowrap"
        >
          <Plus className="h-4 w-4" />
          Create Entity
        </button>
      </div>

      {/* Search and Filter Bar - Only show when there are entities */}
      {entities.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search Input */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by name, legal name, tax ID, or email..."
                className="w-full pl-10 pr-10 py-2.5 text-sm border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  aria-label="Clear search"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Filter Dropdown */}
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-gray-500" />
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value as EntityType | 'all')}
                className="pl-10 pr-10 py-2.5 text-sm border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 appearance-none cursor-pointer min-w-[160px]"
              >
                <option value="all">All Types</option>
                {ENTITY_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
              <svg 
                className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>

            {/* Clear Filters Button */}
            {(searchQuery || filterType !== 'all') && (
              <button
                onClick={clearFilters}
                className="px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors whitespace-nowrap"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        renderLoadingSkeleton()
      ) : filteredEntities.length === 0 && entities.length > 0 ? (
        /* No Results State */
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12">
          <div className="text-center max-w-md mx-auto">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-700 mb-4">
              <Search className="h-8 w-8 text-gray-400 dark:text-gray-500" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              No entities found
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
              No ownership entities match your search criteria. Try adjusting your filters or search terms.
            </p>
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              Clear Filters
            </button>
          </div>
        </div>
      ) : entities.length === 0 ? (
        /* Empty State */
        <div className="bg-white dark:bg-gray-800 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 p-12">
          <div className="text-center max-w-md mx-auto">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 mb-4">
              <Briefcase className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              No ownership entities yet
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
              Create your first ownership entity to start organizing your property portfolio. Ownership entities can be companies, individuals, trusts, or other legal structures.
            </p>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              <Plus className="h-5 w-5" />
              Create Your First Entity
            </button>
          </div>
        </div>
      ) : (
        // Entities Grid
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredEntities.map((entity) => {
            const hasDetails = !!(entity.legal_name || entity.tax_id || entity.contact_email || entity.contact_phone || (entity.city && entity.province));
            
            return (
              <div
                key={entity.id}
                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-lg hover:border-green-300 dark:hover:border-green-700 transition-all duration-200"
              >
                {/* Entity Header */}
                <div className="p-5 pb-4 bg-gradient-to-br from-gray-50 to-white dark:from-gray-800 dark:to-gray-800 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-green-600 dark:from-green-600 dark:to-green-700 flex items-center justify-center shadow-sm">
                      <Briefcase className="h-6 w-6 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 truncate mb-1">
                        {entity.name}
                      </h3>
                      <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800">
                        {getEntityTypeLabel(entity.entity_type)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Entity Details */}
                <div className="p-5">
                  {hasDetails ? (
                    <div className="space-y-3 text-sm">
                      {entity.legal_name && (
                        <div className="flex flex-col">
                          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                            Legal Name
                          </span>
                          <span className="text-gray-900 dark:text-gray-100 font-medium">
                            {entity.legal_name}
                          </span>
                        </div>
                      )}
                      {entity.tax_id && (
                        <div className="flex flex-col">
                          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                            Tax ID
                          </span>
                          <span className="text-gray-900 dark:text-gray-100 font-mono font-medium">
                            {entity.tax_id}
                          </span>
                        </div>
                      )}
                      {entity.contact_email && (
                        <div className="flex items-start gap-2">
                          <Mail className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                          <span className="text-gray-900 dark:text-gray-100 text-sm break-all">
                            {entity.contact_email}
                          </span>
                        </div>
                      )}
                      {entity.contact_phone && (
                        <div className="flex items-center gap-2">
                          <Phone className="h-4 w-4 text-green-600 dark:text-green-400 flex-shrink-0" />
                          <span className="text-gray-900 dark:text-gray-100 text-sm">
                            {entity.contact_phone}
                          </span>
                        </div>
                      )}
                      {entity.city && entity.province && (
                        <div className="flex items-start gap-2">
                          <MapPin className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                          <span className="text-gray-900 dark:text-gray-100 text-sm">
                            {entity.city}, {entity.province}
                          </span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-6">
                      <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                        No additional details provided
                      </p>
                    </div>
                  )}
                </div>

                {/* Actions Footer */}
                <div className="px-5 py-3 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end gap-2">
                  <button
                    onClick={() => handleEdit(entity)}
                    className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors"
                  >
                    <Edit2 className="h-3.5 w-3.5" />
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(entity)}
                    disabled={deletingId === entity.id}
                    className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {deletingId === entity.id ? (
                      <>
                        <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-red-600"></div>
                        Deleting...
                      </>
                    ) : (
                      <>
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Info Banner */}
      {entities.length > 0 && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex gap-3">
            <AlertCircle className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-green-900 dark:text-green-100">
              <p className="font-medium mb-1">About Ownership Entities</p>
              <p className="text-green-700 dark:text-green-300">
                Ownership entities help organize your properties by legal ownership structure. You can assign properties to entities when creating or editing them. Deleting an entity will not affect existing properties that use it.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Create Modal */}
      <NewOwnershipEntityModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleCreate}
      />

      {/* Edit Modal */}
      <EditOwnershipEntityModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingEntity(null);
        }}
        onSuccess={handleUpdate}
        entity={editingEntity}
      />
    </div>
  );
};

export default OwnershipEntitiesSettings;
