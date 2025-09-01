# Property Management System Technical Architecture Plan

## Executive Summary

This document outlines the technical architecture for splitting the monolithic properties table into property type-specific tables, integrating Google Places API, and implementing an enhanced property creation workflow.

## Current State

### Database

- Single `properties` table with 19 records across 5 property types
- Basic fields: id, name, address, city, province, postal_code, property_type, year_built, description, status, user_id, timestamps
- Related tables: property_units, leases, maintenance_requests, expenses, invoices

### API Architecture

- FastAPI endpoints in `Backend/api/properties/`
- Basic CRUD operations with single schema for all property types
- Azure Maps integration for address autocomplete

### Frontend

- Single-step modal for property creation
- Basic form fields regardless of property type
- No map visualization

## Proposed Architecture

### Database Design: Table Inheritance Pattern

```text
properties (base table)
├── properties_residential
├── properties_commercial
├── properties_apartment_complex
├── properties_industrial
├── properties_mixed_use
├── properties_land
├── properties_special_purpose
└── properties_other
```

### Enhanced Base Table

Add to existing `properties` table:

- `latitude` NUMERIC(10, 8)
- `longitude` NUMERIC(11, 8)
- `google_place_id` VARCHAR(255)
- `formatted_address` TEXT
- `neighborhood` VARCHAR(100)
- `country` VARCHAR(2) DEFAULT 'CA'

### Property Type-Specific Tables

#### Apartment Complex Table (`properties_apartment_complex`)

Based on Jira requirements:

##### Core Building Information

- `property_id` (FK to properties)
- `number_of_buildings` INTEGER NOT NULL
- `total_units` INTEGER NOT NULL
- `assigned_property_manager` VARCHAR(200)
- `building_codes_names` JSONB -- {"building_1": "East Tower", "building_2": "West Tower"}

##### Unit Distribution

- `unit_mix` JSONB NOT NULL -- {"studio": 20, "1br": 40, "2br": 30, "3br": 10}
- `studio_units` INTEGER DEFAULT 0
- `one_bed_units` INTEGER DEFAULT 0
- `two_bed_units` INTEGER DEFAULT 0
- `three_bed_units` INTEGER DEFAULT 0
- `penthouse_units` INTEGER DEFAULT 0

##### Amenities & Infrastructure

- `shared_amenities` JSONB -- ["gym", "pool", "parking_garage", "clubhouse", "laundry"]
- `has_security_system` BOOLEAN DEFAULT false
- `security_system_details` VARCHAR(500)
- `elevator_count` INTEGER DEFAULT 0
- `trash_system_type` VARCHAR(50) -- 'chute', 'compactor', 'curbside', 'valet'
- `trash_system_details` TEXT

##### Management & Operations

- `lease_expiry_distribution` JSONB -- {"2024-Q1": 15, "2024-Q2": 20, ...}
- `emergency_contacts` JSONB -- [{"name": "John Doe", "role": "Super", "phone": "xxx", "available": "24/7"}]
- `on_site_management` BOOLEAN DEFAULT false
- `management_office_hours` JSONB
- `property_management_company` VARCHAR(200)

##### Additional Fields

- `parking_spaces_total` INTEGER
- `parking_ratio` NUMERIC(3,2)
- `pet_policy` VARCHAR(500)
- `utilities_included` JSONB
- `average_rent` NUMERIC(12,2)
- `vacancy_rate` NUMERIC(5,2)

#### Commercial Properties Table (`properties_commercial`)

Based on Jira requirements:

##### Space Information

- `property_id` (FK to properties)
- `space_type` VARCHAR(50) NOT NULL -- 'retail', 'office', 'medical', 'restaurant', etc.
- `usable_square_feet` INTEGER NOT NULL
- `rentable_square_feet` INTEGER NOT NULL
- `common_area_factor` NUMERIC(5,2) -- For expense allocation
- `lease_type` VARCHAR(50) NOT NULL -- 'gross', 'triple_net', 'modified_gross'

##### Compliance & Zoning

- `zoning_code` VARCHAR(50) NOT NULL
- `business_licensing_compliance` JSONB -- {"status": "compliant", "licenses": [...], "expiry_dates": {...}}
- `permitted_uses` JSONB

##### Physical Specifications

- `ceiling_height` NUMERIC(5,2)
- `has_loading_area` BOOLEAN DEFAULT false
- `loading_docks_count` INTEGER DEFAULT 0
- `loading_area_details` TEXT
- `signage_rights` BOOLEAN DEFAULT false
- `signage_restrictions` TEXT

##### Infrastructure

- `power_supply_info` JSONB -- {"voltage": ["120V", "240V"], "phase": "3-phase", "capacity": "400A"}
- `hvac_details` JSONB -- {"type": "central", "zones": 4, "age": 5, "last_service": "2023-12"}
- `internet_infrastructure` JSONB -- {"fiber_ready": true, "providers": ["Bell", "Rogers"], "speed": "1Gbps"}

##### Tenant Information

- `number_of_tenants` INTEGER DEFAULT 0
- `tenant_mix` JSONB -- [{"name": "Store A", "sqft": 2000, "type": "retail"}]
- `anchor_tenant` VARCHAR(200)

##### Management

- `property_management_company` VARCHAR(200)
- `on_site_maintenance` BOOLEAN DEFAULT false

#### Residential Properties Table

Standard residential fields:

- Bedrooms, bathrooms, square feet, lot size
- Garage spaces, basement, pool, hot tub
- Heating/cooling types, appliances
- HOA fees, property taxes, insurance

### API Architecture Updates

#### New Service Layer Structure

```text
Backend/api/properties/
├── router.py                 # Enhanced routing with type-specific endpoints
├── schemas/
│   ├── base.py              # Base property schemas
│   ├── residential.py       # Residential-specific schemas
│   ├── commercial.py        # Commercial-specific schemas
│   ├── apartment.py         # Apartment complex schemas
│   └── ...
├── services/
│   ├── property_service.py  # Base property operations
│   ├── google_places.py     # Google Places integration
│   └── type_handlers.py     # Type-specific business logic
└── models.py                # SQLModel definitions
```

#### Key API Changes

1. **Polymorphic Response Handling**: API returns type-specific data based on property_type
2. **Google Places Integration**: New endpoints for autocomplete and place details
3. **Validation Layer**: Type-specific validation using discriminated unions in Pydantic
4. **Transaction Management**: Atomic operations for base + type-specific table inserts

### Frontend Architecture Updates

#### Component Structure

```text
Frontend/src/components/properties/
├── NewPropertyWizard/
│   ├── index.jsx            # Main wizard controller
│   ├── steps/
│   │   ├── BasicInfoStep.jsx
│   │   ├── LocationStep.jsx    # Google Maps integration
│   │   ├── TypeSpecificStep.jsx
│   │   └── ReviewStep.jsx
│   └── forms/
│       ├── ResidentialForm.jsx
│       ├── CommercialForm.jsx
│       ├── ApartmentForm.jsx
│       └── ...
├── PropertyTypeFields.jsx    # Dynamic form field renderer
└── GoogleMapsWrapper.jsx     # Maps component wrapper
```

#### Key Frontend Changes

1. **Multi-step Wizard**: Replace modal with 4-step creation flow
2. **Dynamic Form Generation**: Render fields based on selected property type
3. **Google Maps Integration**: Interactive map for location selection
4. **Session Token Management**: Optimize Google Places API usage
5. **Real-time Validation**: Type-specific field validation

### Migration Strategy

#### Phase 1: Database Schema Evolution

1. Add location fields to base properties table
2. Create type-specific tables with proper foreign keys
3. Create database view `v_properties_full` for unified querying
4. Implement RLS policies on new tables

#### Phase 2: Data Migration

1. Run Alembic migration to create new structure
2. Populate type-specific tables with default values for existing records
3. Maintain backward compatibility during transition

#### Phase 3: API Layer Evolution

1. Deploy new endpoints alongside existing ones
2. Implement feature flags for gradual rollout
3. Update frontend to use new endpoints based on feature flags

#### Phase 4: Frontend Deployment

1. Deploy new property creation wizard
2. Update property listing to display type-specific fields
3. Implement property editing with type-specific forms

### Technical Considerations

#### Performance Optimization

- Index foreign keys and commonly queried fields
- Use database views for complex queries
- Implement pagination for large property lists

#### Data Integrity

- Use database transactions for multi-table operations
- Implement cascade deletes for type-specific data
- Add check constraints for business rules

#### API Design

- RESTful endpoints with type discrimination
- Consistent error handling across property types
- Comprehensive OpenAPI documentation

#### Security

- Maintain RLS policies across all tables
- Validate Google Places API responses
- Sanitize user inputs for JSONB fields

### Integration Points

#### Google Places API

- Autocomplete: `/api/properties/places/autocomplete`
- Place Details: `/api/properties/places/details`
- Session token management for billing optimization

#### Existing Systems

- Maintain compatibility with units, leases, maintenance systems
- Update reporting queries to use new structure
- Ensure QuickBooks sync handles new fields

### Rollback Strategy

1. Feature flags allow instant rollback
2. Database views maintain backward compatibility
3. Old API endpoints remain functional during transition
4. Data migration scripts are reversible
