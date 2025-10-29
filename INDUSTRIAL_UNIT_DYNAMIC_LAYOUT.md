# Industrial Unit Dynamic Layout Jira Ticket

## Description

When a landlord adds a unit under an industrial property, the current form still shows residential fields (e.g., bedrooms, bathrooms) and lacks proper ownership and rent separation. We need to implement a dynamic layout for industrial units that automatically displays the correct structure, connects ownership to a company, and separates rent fields clearly.

## Context (from user feedback)

- For industrial units, “bedrooms” and “bathrooms” don’t apply.
- Required fields should include:
  - Unit Number
  - Monthly Rent
  - Additional Rent
  - Security Deposit
  - Ownership (linked to company or property owner)
- The “ownership” field should pull from a predefined list of companies or property owners, or let them enter manual text input.
- Rent fields need to be stored separately in the backend for reporting and accounting consistency.
- “Industrial area” display formatting should differ from residential.

## Acceptance Criteria

- ✅ **Dynamic Layout:**
  - When Property Type = Industrial → hide Bedrooms/Bathrooms fields.
  - Show: Unit Number, Monthly Rent, Additional Rent, Security Deposit, Ownership.
- ✅ **Ownership Field:**
  - Ownership should be a dropdown linked to a property owner/company table.
  - Selected ownership should persist and reflect in reports and exports.
  - Allow multiple ownership entities (optional enhancement).
- ✅ **Rent Field Separation:**
  - Separate and label fields clearly: `rent_monthly`, `rent_additional`, `deposit_security`.
  - Ensure backend schema supports these distinctions.
- ✅ **Industrial Layout:**
  - Industrial unit cards/tables in landlord portal should remove irrelevant residential fields.
  - Layout and alignment should follow same design system as residential units.
- ✅ **Validation:**
  - Required: Unit Number, Monthly Rent, Ownership.
  - Optional: Additional Rent, Security Deposit.

## Developer Notes

- Update Add Unit modal to conditionally render based on property type.
- Integrate ownership data source or create owners table if not yet present.
- Verify data consistency between unit creation, edit, and summary view.
- Coordinate with UI/UX to ensure clean industrial formatting.
- Confirm compatibility with CSV import/export.

---

## Analysis and Implementation Plan

This feature requires coordinated changes across the backend and frontend to support a dynamic unit management experience based on property type. The core of the task is to introduce new fields for industrial units while hiding residential-specific fields.

### Backend Implementation

1. **Update Database Model (`Backend/models/units.py`):**
    - Add the following fields to the `PropertyUnit` model:
        - `additional_rent`: `Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(12, 2)))`
        - `security_deposit`: `Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(12, 2)))`
        - `ownership`: `Optional[str] = None` (A simple string field is a good first step, can be evolved to a foreign key later).

2. **Create Database Migration:**
    - Run `poetry run alembic revision --autogenerate -m "add_industrial_fields_to_units"` to create a new migration file.
    - Verify the migration script and apply it using `poetry run alembic upgrade head`.

3. **Update API Schemas (`Backend/api/units/schemas.py`):**
    - Add `additional_rent`, `security_deposit`, and `ownership` to `UnitBase`, `UnitCreate`, and `UnitUpdate` schemas.
    - Add validation for the new fields as needed (e.g., must be non-negative).

4. **Update API Endpoints:**
    - The existing `create_unit_for_property` and `update_unit` functions in `Backend/api/units/router.py` should automatically handle the new fields thanks to the schema updates. No significant logic changes are expected in the service layer initially.

### Frontend Implementation

1. **Update Modals (`Frontend/src/components/units/NewUnitModal.jsx` & `EditUnitModal.jsx`):**
    - Both modals must accept a `propertyType` prop.
    - Use conditional rendering:
        - If `propertyType === 'Industrial'`:
            - Show fields for `Monthly Rent`, `Additional Rent`, `Security Deposit`, and `Ownership`.
            - Hide `Bedrooms` and `Bathrooms` fields.
        - Otherwise, show the existing residential fields.
    - Update the local form state (`formData`) to include `additional_rent`, `security_deposit`, and `ownership`.
    - Modify the `handleSubmit` function to pass the new fields in the API request.

2. **Update Unit Table (`Frontend/src/components/units/UnitTable.jsx`):**
    - The component needs to receive the `propertyType`.
    - Conditionally render the table columns. For industrial properties, display columns for the new rent fields and ownership, and hide residential-specific columns.

3. **Update API Client (`Frontend/src/utils/api/units.js`):**
    - The `createUnit` and `updateUnit` functions should be updated to include the new fields in the JSON body sent to the backend. The formatting logic in `updateUnit` should be extended for the new decimal fields.
