# Analysis and Improvement Plan for Unit Management

## 1. Current State Analysis

The unit management flow is centered on the `PropertyDetail.jsx` page, which displays a property's units within a `UnitTable.jsx`. Users can add, edit, and delete units through modals. The core logic presents several opportunities for enhancement:

*   **Unified Create/Edit Modal**: `NewUnitModal.jsx` is used for both creating a new unit and editing an existing one. This dual-purpose implementation is the source of the primary issues identified.
*   **Client-Side Logic**: The `PropertyDetail.jsx` component is responsible for fetching raw unit data and then performing calculations on the client-side to derive key stats like total units, vacant units, and monthly revenue.
*   **Data Refresh on Change**: Any state change (create, update, delete) triggers a full refetch of all property data to update the UI, which is reliable but not always performant.
*   **UI Inconsistencies**: The Properties page uses a custom notification banner while PropertyDetail uses react-toastify, creating an inconsistent user experience across the application.

## 2. Key Issues Identified

### User Experience (UX)

1.  **Confusing "Edit" Workflow**: The current "Edit" functionality is misleading. It allows a user to modify a unit's descriptive details (like its floor number) in the same form as its rental status (`is_rented`). This can lead to unintentional and significant changes, such as marking a rented unit as vacant.
2.  **Inconsistent Notifications**: Properties.jsx uses a custom notification banner while PropertyDetail.jsx uses react-toastify, creating an inconsistent experience across the application.
3.  **Missing Validation**: The NewUnitModal allows marking a unit as rented without any tenant assignment or lease validation, potentially creating invalid data states.
4.  **Sluggish UI Feedback**: Relying on a full server refetch after every action makes the UI feel less responsive than it could be.

### Business Logic

1.  **Fragile Occupancy State**: A unit's occupancy is managed by a simple `is_rented` boolean that can be directly toggled in the UI. This is a fragile system. A unit's rental status should be a derived property based on whether it has an active lease agreement, not a directly editable field. The current design allows a user to break the data integrity between a unit and its lease with a single click.
2.  **Mixing Business Concerns**: The `NewUnitModal` incorrectly combines two distinct business processes: managing a unit's physical attributes (name, floor) and managing its rental lifecycle (status, rent). According to the principle of **Separation of Concerns**, these should be handled in separate, dedicated workflows.
3.  **Client-Side Calculations**: The frontend calculates key business metrics. As advocated in architectural patterns like **Backend for Frontend (BFF)**, this logic is better placed in the API. This ensures data consistency across all potential clients (e.g., web and mobile) and simplifies the frontend code.

## 3. Proposed Improvement Plan

A phased approach to refactor the unit management feature, starting with foundational fixes and moving toward more advanced enhancements.

### Phase 1: Foundational Refactoring & UX Cleanup

This phase addresses the most critical UX and bug-related issues.

1.  **Create a Dedicated `EditUnitModal.jsx`**:
    *   **What**: Introduce a new `Frontend/src/components/units/EditUnitModal.jsx` component.
    *   **Why**: To separate the "edit unit" workflow from the "create unit" workflow. This new modal will be for editing a unit's *physical characteristics only* (e.g., Unit Number, Floor). It will **not** contain form fields for `monthly_rent` or `is_rented`. For occupied units, it can display tenant and rent details as read-only information for context.
    *   **Files to modify**: `Frontend/src/pages/PropertyDetail.jsx`, create `Frontend/src/components/units/EditUnitModal.jsx`.

2.  **Standardize Notifications Across the App**:
    *   **What**: Convert `Properties.jsx` to use `react-toastify` instead of custom notification banner for consistency with PropertyDetail.
    *   **Why**: To create a consistent notification experience across all pages.
    *   **Files to modify**: `Frontend/src/pages/Properties.jsx`.

3.  **Add Validation to NewUnitModal**:
    *   **What**: Prevent marking a unit as rented without tenant assignment. Add validation logic that shows an error toast if `is_rented` is true but no tenant is assigned.
    *   **Why**: To prevent invalid data states and maintain data integrity.
    *   **Files to modify**: `Frontend/src/components/units/NewUnitModal.jsx`.

4.  **Create UnitStatusBadge Component**:
    *   **What**: Create a new `Frontend/src/components/units/UnitStatusBadge.jsx` component for consistent visual representation of unit status.
    *   **Why**: To ensure consistent UI patterns and make status more visually clear across the app.
    *   **Files to create**: `Frontend/src/components/units/UnitStatusBadge.jsx`.

### Phase 2: Strengthening Business Logic

This phase focuses on making the underlying application logic more robust and aligned with real-world processes.

1.  **Decouple Occupancy Status from Direct Edit**:
    *   **What (Frontend)**: In `NewUnitModal.jsx`, remove the "Unit is currently rented" checkbox. New units should always be created as "Vacant," becoming "Rented" only through the "Assign Tenant" workflow, which correctly manages lease creation.
    *   **What (Backend)**: The `UnitUpdate` API endpoint should not allow direct modification of the `is_rented` field. This status should be a derived property managed by the backend's lease management logic.
    *   **Why**: To ensure data integrity and align the application's behavior with real-world business rules.
    *   **Files to modify**: `Frontend/src/components/units/NewUnitModal.jsx`, `Backend/api/units/service.py`.

2.  **Move Stat Calculations to the Backend (BFF Pattern)**:
    *   **What (Backend)**: Enhance the `/api/properties/{id}` endpoint to calculate and return the `stats` object directly in the response:
        ```python
        class PropertyStats(BaseModel):
            total_units: int
            vacant_units: int
            occupied_units: int
            monthly_revenue: Decimal
            occupancy_rate: float
        ```
    *   **What (Frontend)**: Refactor `PropertyDetail.jsx` to consume these pre-calculated stats, removing the client-side logic.
    *   **Why**: To simplify the frontend, improve performance, and establish the API as the single source of truth.
    *   **Files to modify**: `Backend/api/properties/service.py`, `Backend/api/properties/schemas.py`, `Frontend/src/pages/PropertyDetail.jsx`.

3.  **Implement Lease-Unit Integration**:
    *   **What**: Create proper integration between units and leases:
        - Add `GET /api/units/{id}/lease` endpoint to fetch active lease for a unit
        - Create `useUnitStatus` hook that derives rental status from lease data
        - Update UnitTable to show lease information for rented units
    *   **Why**: To properly model the relationship between units and leases, ensuring data consistency.
    *   **Files to create**: `Frontend/src/hooks/useUnitStatus.js`, update `Backend/api/units/router.py`.

### Phase 3: Performance & Future Enhancements

These are forward-looking improvements to build upon the new, stable foundation.

1.  **Implement Optimistic UI Updates**:
    *   **What**: Refactor the data-handling functions in `PropertyDetail.jsx` to update the local UI state immediately upon user action, without waiting for the API response:
        ```javascript
        const handleUnitUpdate = async (unitId, updates) => {
          // Optimistically update UI
          setUnits(prev => prev.map(u => 
            u.id === unitId ? { ...u, ...updates } : u
          ));
          
          try {
            await api.updateUnit(unitId, updates);
            toast.success("Unit updated successfully");
          } catch (error) {
            // Revert on failure
            loadProperty();
            toast.error("Update failed");
          }
        };
        ```
    *   **Why**: To make the application feel significantly faster and more responsive.
    *   **Files to modify**: `Frontend/src/pages/PropertyDetail.jsx`.

2.  **Expand Lease Management Workflows**:
    *   **What**: For rented units, introduce new actions like "View Lease" and "End Lease" to the `UnitTable`. These would launch dedicated modals or pages for managing the full lease lifecycle.
    *   **Why**: To build out a more complete and powerful feature set that correctly models the complexities of property management.
    *   **Files to modify**: `Frontend/src/components/units/UnitTable.jsx`.

3.  **Add State Management for Units**:
    *   **What**: Implement proper state management using Context API or Zustand:
        ```javascript
        const useUnitsStore = create((set) => ({
          units: [],
          stats: null,
          updateUnit: (id, changes) => set(state => ({
            units: state.units.map(u => u.id === id ? { ...u, ...changes } : u)
          })),
          deleteUnit: (id) => set(state => ({
            units: state.units.filter(u => u.id !== id)
          }))
        }));
        ```
    *   **Why**: To centralize unit state management and make it easier to implement optimistic updates.
    *   **Files to create**: `Frontend/src/stores/unitsStore.js`.

4.  **Add Type Safety with JSDoc**:
    *   **What**: Add JSDoc type definitions for better IDE support and code documentation:
        ```javascript
        /**
         * @typedef {Object} Unit
         * @property {number} id
         * @property {string} name
         * @property {boolean} is_rented
         * @property {number|null} tenant_id
         * @property {string|null} monthly_rent
         * @property {Object|null} tenant
         */
        ```
    *   **Why**: To improve code maintainability and reduce runtime errors.
    *   **Files to modify**: All unit-related components.

## Implementation Order

1. **File Organization** (Immediate): Move all unit-related components to `Frontend/src/components/units/`
2. **Phase 1**: Focus on UX cleanup and fixing critical issues
3. **Phase 2**: Implement backend improvements and proper data modeling
4. **Phase 3**: Add performance optimizations and advanced features

## Success Metrics

- Unit updates feel instant (< 50ms perceived latency)
- Zero data integrity issues (no units marked as rented without leases)
- Consistent UI/UX patterns across the application
- Reduced code complexity and improved maintainability 