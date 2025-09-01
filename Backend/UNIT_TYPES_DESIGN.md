# Property Type-Specific Unit Design

## Unit Model Hierarchy

### Base Unit Fields (All Types)

- `name` - Unit identifier
- `property_id` - Link to property
- `is_rented` - Occupancy status
- `monthly_rent` - Rent amount
- `size` - Square footage
- `description` - Unit description

### Apartment Complex Units

```python
class ApartmentUnit(BaseUnit):
    unit_type: str  # "studio", "1br", "2br", "3br", "penthouse"
    floor: int
    bedrooms: int
    bathrooms: float
    has_balcony: bool
    has_in_unit_laundry: bool
    parking_spaces: int
    storage_unit_number: str | None
```

### Commercial Units

```python
class CommercialUnit(BaseUnit):
    unit_type: str  # "office", "retail", "restaurant", "medical"
    floor: int
    zoning_type: str  # "retail", "office", "mixed"
    max_occupancy: int
    has_street_access: bool
    has_loading_dock: bool
    parking_ratio: float  # spaces per 1000 sqft
    hvac_zones: int
    electrical_capacity: str  # "standard", "high", "industrial"
```

### Industrial Units

```python
class IndustrialUnit(BaseUnit):
    unit_type: str  # "warehouse", "manufacturing", "flex", "storage"
    ceiling_height: float  # in feet
    loading_docks: int
    drive_in_doors: int
    electrical_capacity: str  # "standard", "high", "industrial"
    has_crane: bool
    has_rail_access: bool
    clear_span: bool  # no columns
    truck_court_depth: float  # in feet
```

### Mixed-Use Units

```python
class MixedUseUnit(BaseUnit):
    primary_use: str  # "residential", "commercial", "industrial"
    # Then includes fields from the appropriate type above
```

## Unit Generation UI by Property Type

### 1. Apartment Complex

- **Quick Generate**: "Generate 50 units across 5 floors"
- **Pattern Options**:
  - By floor plan (10 units per floor)
  - By unit mix (20% studio, 40% 1BR, 30% 2BR, 10% 3BR)
- **Naming**: "101, 102, 103..." or "1A, 1B, 1C..."

### 2. Commercial Property

- **Quick Generate**: "Create 10 office suites"
- **Pattern Options**:
  - By floor (Suite 100-105, 200-205)
  - By size tiers (Small/Medium/Large)
- **Naming**: "Suite 101", "Office A", "Retail Space 1"

### 3. Industrial Property

- **Quick Generate**: "Create 5 warehouse bays"
- **Pattern Options**:
  - Sequential bays (Bay 1-5)
  - By dock access (Dock A1-A5, B1-B5)
- **Naming**: "Bay 1", "Warehouse A", "Unit WH-01"

### 4. Residential (Single-Family)

- **Options**:
  - No units (property is the single unit)
  - Add ADU (Accessory Dwelling Unit)
  - Add Guest House

### 5. Mixed-Use

- **Hybrid Approach**:
  - First select zones (Ground floor retail, Upper floors residential)
  - Generate units per zone with appropriate types

## Implementation Steps

1. **Backend**:
   - Extend PropertyUnit model with type-specific fields
   - Create unit generation service methods per type
   - Add validation for unit types matching property types

2. **Frontend - New UnitsStep**:
   - Detect property type from previous steps
   - Show appropriate unit generation UI
   - Support both quick generation and manual entry
   - Preview generated units before creation

3. **Smart Defaults**:
   - Apartment: 10 units per floor, numbered by floor
   - Commercial: 5-10 suites, sized 1000-5000 sqft
   - Industrial: 3-5 bays, 5000-20000 sqft each
   - Residential: No units by default
   - Mixed-Use: Guide through zone definition first

## API Endpoints

```python
# Generate units based on pattern
POST /api/properties/{id}/units/generate
{
    "pattern": "by_floor",
    "config": {
        "floors": 5,
        "units_per_floor": 10,
        "unit_mix": {"studio": 0.2, "1br": 0.4, "2br": 0.3, "3br": 0.1}
    }
}

# Bulk create units
POST /api/properties/{id}/units/bulk
{
    "units": [...]
}
```

## Benefits

1. **Better Data Quality**: Captures property-type-specific information
2. **Improved UX**: Tailored generation for each property type  
3. **Scalability**: Easy to add new property types
4. **Flexibility**: Supports both quick generation and detailed entry
5. **Future-Ready**: Sets foundation for type-specific features (industrial equipment tracking, commercial lease terms, etc.)
