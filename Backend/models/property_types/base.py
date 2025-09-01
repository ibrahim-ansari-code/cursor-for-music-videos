"""
Base class and utilities for property type models.
Provides common functionality and validation for all property types.
"""
from typing import Optional, Dict, Any, List
from decimal import Decimal
from sqlmodel import SQLModel


class PropertyTypeBase(SQLModel):
    """Base class for all property type-specific models"""
    
    @classmethod
    def validate_percentage(cls, v: Optional[Decimal], field_name: str) -> Optional[Decimal]:
        """Validate percentage fields are between 0 and 100"""
        if v is not None and (v < 0 or v > 100):
            raise ValueError(f"{field_name} must be between 0 and 100")
        return v
    
    @classmethod
    def validate_positive_number(cls, v: Optional[int], field_name: str) -> Optional[int]:
        """Validate that numeric fields are positive"""
        if v is not None and v < 0:
            raise ValueError(f"{field_name} must be a positive number")
        return v
    
    @classmethod
    def validate_json_structure(cls, v: Dict[str, Any], expected_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Validate JSON field structure"""
        if expected_keys:
            for key in expected_keys:
                if key not in v:
                    v[key] = None  # Set default for missing keys
        return v
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """Override in subclasses to calculate type-specific metrics"""
        return {}
    
    def validate_business_rules(self) -> list[str]:
        """Override in subclasses to validate business rules. Returns list of validation errors."""
        return []


class LeaseExpiryHelper:
    """Helper class for lease expiry distribution calculations"""
    
    @staticmethod
    def calculate_quarterly_distribution(leases: List) -> Dict[str, int]:
        """Calculate lease expiry distribution by quarter"""
        from collections import defaultdict
        distribution: Dict[str, int] = defaultdict(int)
        
        for lease in leases:
            if hasattr(lease, 'end_date') and lease.end_date:
                year = lease.end_date.year
                quarter = (lease.end_date.month - 1) // 3 + 1
                key = f"{year}-Q{quarter}"
                distribution[key] += 1
        
        return dict(distribution)
    
    @staticmethod
    def get_upcoming_expiries(leases: List, months_ahead: int = 6) -> List:
        """Get leases expiring in the next N months"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now().date() + timedelta(days=months_ahead * 30)
        
        return [
            lease for lease in leases 
            if hasattr(lease, 'end_date') and lease.end_date 
            and lease.end_date <= cutoff_date
        ]


class UnitMixHelper:
    """Helper class for unit mix calculations"""
    
    @staticmethod
    def standardize_unit_type(unit_type: str) -> str:
        """Standardize unit type naming"""
        mappings = {
            'studio': 'studio',
            '0br': 'studio',
            '1br': '1br',
            '1bedroom': '1br',
            '1 bedroom': '1br',
            '2br': '2br',
            '2bedroom': '2br',
            '2 bedroom': '2br',
            '3br': '3br',
            '3bedroom': '3br',
            '3 bedroom': '3br',
            '4br': '4br',
            '4bedroom': '4br',
            '4 bedroom': '4br',
            'penthouse': 'penthouse',
            'loft': 'loft'
        }
        return mappings.get(unit_type.lower().strip(), unit_type.lower())
    
    @staticmethod
    def validate_unit_mix(unit_mix: Dict[str, int], total_units: int) -> bool:
        """Validate that unit mix adds up to total units"""
        return sum(unit_mix.values()) == total_units
    
    @staticmethod
    def calculate_average_rent_by_type(units: List) -> Dict[str, Decimal]:
        """Calculate average rent by unit type"""
        from collections import defaultdict
        from decimal import Decimal
        
        rent_by_type = defaultdict(list)
        
        for unit in units:
            if hasattr(unit, 'unit_type') and hasattr(unit, 'monthly_rent'):
                if unit.monthly_rent:
                    unit_type = UnitMixHelper.standardize_unit_type(unit.unit_type)
                    rent_by_type[unit_type].append(Decimal(str(unit.monthly_rent)))
        
        avg_rent: Dict[str, Decimal] = {}
        for unit_type, rents in rent_by_type.items():
            if rents:
                avg_rent[unit_type] = Decimal(sum(rents) / len(rents))
        
        return avg_rent


class FinancialMetricsHelper:
    """Helper for financial calculations across property types"""
    
    @staticmethod
    def calculate_cap_rate(net_operating_income: Decimal, property_value: Decimal) -> Optional[Decimal]:
        """Calculate capitalization rate"""
        if property_value and property_value > 0:
            return (net_operating_income / property_value) * 100
        return None
    
    @staticmethod
    def calculate_gross_rent_multiplier(property_value: Decimal, annual_rental_income: Decimal) -> Optional[Decimal]:
        """Calculate GRM"""
        if annual_rental_income and annual_rental_income > 0:
            return property_value / annual_rental_income
        return None
    
    @staticmethod
    def calculate_expense_ratio(operating_expenses: Decimal, gross_income: Decimal) -> Optional[Decimal]:
        """Calculate expense ratio"""
        if gross_income and gross_income > 0:
            return (operating_expenses / gross_income) * 100
        return None
