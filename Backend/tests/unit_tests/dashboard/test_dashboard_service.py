"""
Unit tests for the DashboardService class and service layer logic.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID as PythonUUID
from datetime import datetime, date, UTC, timedelta
from decimal import Decimal

from fastapi import HTTPException

from Backend.api.dashboard.service import DashboardService
from Backend.api.dashboard.schemas import DashboardSummary, OccupancyData, RevenueData, PaymentDue
from Backend.models.property import Property, PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.lease import Lease
from Backend.models.accounting.payment import Payment
from Backend.models.accounting.expense import Expense
from Backend.models.accounting.invoice import Invoice
from Backend.models.accounting.common import PaymentStatus
from Backend.models.user import User
from Backend.models.enums import UserType


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_mock_user(user_type: str = "ADMIN", user_id: PythonUUID | None = None):
    """Create a mock user for testing."""
    mock_user = MagicMock(spec=User)
    mock_user.user_type = UserType(user_type)
    mock_user.id = user_id or uuid4()
    return mock_user

def create_mock_property(property_id: int = 1, user_id: PythonUUID | None = None):
    """Create a mock property for testing."""
    mock_property = MagicMock(spec=Property)
    mock_property.id = property_id
    mock_property.user_id = user_id or uuid4()
    mock_property.units = []
    mock_property.leases = []
    mock_property.expenses = []
    mock_property.invoices = []
    return mock_property

def create_mock_unit(property_id: int = 1, is_rented: bool = True):
    """Create a mock property unit for testing."""
    mock_unit = MagicMock(spec=PropertyUnit)
    mock_unit.property_id = property_id
    mock_unit.is_rented = is_rented
    mock_unit.monthly_rent = Decimal("1000.00") if is_rented else None
    return mock_unit

def create_mock_payment(amount: Decimal = Decimal("1000.00"), status: PaymentStatus = PaymentStatus.PAID):
    """Create a mock payment for testing."""
    mock_payment = MagicMock(spec=Payment)
    mock_payment.amount = amount
    mock_payment.status = status
    mock_payment.payment_date = datetime(2024, 1, 15, tzinfo=UTC)
    return mock_payment

def create_mock_expense(amount: Decimal = Decimal("500.00"), category: str = "utilities"):
    """Create a mock expense for testing."""
    mock_expense = MagicMock(spec=Expense)
    mock_expense.subtotal_amount = amount
    mock_expense.total_tax_amount = Decimal("50.00")
    mock_expense.category = category
    mock_expense.expense_date = datetime(2024, 1, 10, tzinfo=UTC)
    return mock_expense

def create_mock_invoice(amount: Decimal = Decimal("1200.00"), status: PaymentStatus = PaymentStatus.PENDING):
    """Create a mock invoice for testing."""
    mock_invoice = MagicMock(spec=Invoice)
    mock_invoice.id = 1
    mock_invoice.amount = amount
    mock_invoice.status = status
    mock_invoice.due_date = date(2024, 1, 31)
    
    # Mock tenant
    mock_tenant = MagicMock(spec=Tenant)
    mock_tenant.first_name = "John"
    mock_tenant.last_name = "Doe"
    mock_tenant.company_name = None
    mock_tenant.leases = []
    mock_invoice.tenant = mock_tenant
    
    return mock_invoice


# =============================================================================
# DATE RANGE CALCULATION TESTS
# =============================================================================

class TestDashboardServiceDateRanges:
    """Test date range calculations."""
    
    def test_calculate_date_range_with_overrides(self):
        """Test date range calculation with explicit overrides."""
        start_override = date(2024, 1, 1)
        end_override = date(2024, 1, 31)
        
        start_date, end_date = DashboardService._calculate_date_range(
            "month", start_override, end_override
        )
        
        assert start_date == start_override
        assert end_date == end_override
    
    def test_calculate_date_range_week(self):
        """Test date range calculation for week period."""
        start_date, end_date = DashboardService._calculate_date_range("week", None, None)
        
        expected_start = date.today() - timedelta(days=7)
        expected_end = date.today()
        
        assert start_date == expected_start
        assert end_date == expected_end
    
    def test_calculate_date_range_month(self):
        """Test date range calculation for month period."""
        start_date, end_date = DashboardService._calculate_date_range("month", None, None)
        
        today = date.today()
        expected_start = today.replace(day=1)
        expected_end = today
        
        assert start_date == expected_start
        assert end_date == expected_end
    
    def test_calculate_date_range_quarter(self):
        """Test date range calculation for quarter period."""
        start_date, end_date = DashboardService._calculate_date_range("quarter", None, None)
        
        today = date.today()
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        expected_start = date(today.year, q_start_month, 1)
        expected_end = today
        
        assert start_date == expected_start
        assert end_date == expected_end
    
    def test_calculate_date_range_year(self):
        """Test date range calculation for year period."""
        start_date, end_date = DashboardService._calculate_date_range("year", None, None)
        
        today = date.today()
        expected_start = date(today.year, 1, 1)
        expected_end = today
        
        assert start_date == expected_start
        assert end_date == expected_end
    
    def test_calculate_date_range_default(self):
        """Test date range calculation for unknown period (defaults to month)."""
        start_date, end_date = DashboardService._calculate_date_range("unknown", None, None)
        
        today = date.today()
        expected_start = today.replace(day=1)
        expected_end = today
        
        assert start_date == expected_start
        assert end_date == expected_end


# =============================================================================
# PROPERTY QUERY BUILDING TESTS
# =============================================================================

class TestDashboardServicePropertyQuery:
    """Test property query building."""
    
    def test_build_property_query_admin(self):
        """Test property query building for admin user."""
        mock_user = create_mock_user("ADMIN")
        
        with patch('Backend.api.dashboard.service.select') as mock_select:
            mock_query = MagicMock()
            mock_select.return_value = mock_query
            
            result = DashboardService._build_property_query(mock_user, None)
            
            mock_select.assert_called_once_with(Property)
            assert result == mock_query
            # Admin should not have user scoping applied
            mock_query.where.assert_not_called()
    
    def test_build_property_query_landlord(self):
        """Test property query building for landlord user."""
        mock_user = create_mock_user("LANDLORD", uuid4())
        
        with patch('Backend.api.dashboard.service.select') as mock_select, \
             patch('Backend.api.dashboard.service.cast') as mock_cast:
            
            mock_query = MagicMock()
            mock_select.return_value = mock_query
            
            result = DashboardService._build_property_query(mock_user, None)
            
            mock_select.assert_called_once_with(Property)
            # Landlord should have user scoping applied
            mock_query.where.assert_called_once()
    
    def test_build_property_query_with_property_filter(self):
        """Test property query building with property ID filter."""
        mock_user = create_mock_user("ADMIN")
        
        with patch('Backend.api.dashboard.service.select') as mock_select, \
             patch('Backend.api.dashboard.service.cast') as mock_cast:
            
            mock_query = MagicMock()
            mock_select.return_value = mock_query
            
            result = DashboardService._build_property_query(mock_user, 123)
            
            mock_select.assert_called_once_with(Property)
            # Property filter should be applied
            mock_query.where.assert_called_once()


# =============================================================================
# DASHBOARD SUMMARY TESTS
# =============================================================================

class TestDashboardServiceSummary:
    """Test dashboard summary calculations."""
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary_success(self):
        """Test successful dashboard summary calculation."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        start_datetime = datetime(2024, 1, 1, tzinfo=UTC)
        end_datetime = datetime(2024, 1, 31, tzinfo=UTC)
        
        # Mock properties with units
        mock_property = create_mock_property()
        mock_property.units = [
            create_mock_unit(is_rented=True),
            create_mock_unit(is_rented=True),
            create_mock_unit(is_rented=False)
        ]
        
        # Mock session execution for properties query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_property]
        mock_session.execute.return_value = mock_result
        
        # Mock scalar queries for financial metrics - side_effect for multiple calls
        mock_session.execute.side_effect = [
            mock_result,  # Properties query
            MagicMock(scalar=MagicMock(return_value=3)),  # total_units query
            MagicMock(scalar=MagicMock(return_value=2)),  # occupied_units query
            MagicMock(scalar=MagicMock(return_value=Decimal("1000.00"))),  # monthly_revenue query
            MagicMock(scalar=MagicMock(return_value=Decimal("500.00"))),   # monthly_expenses query
            MagicMock(scalar=MagicMock(return_value=Decimal("200.00"))),   # maintenance_expenses query
            MagicMock(scalar=MagicMock(return_value=Decimal("300.00")))   # outstanding_rent query
        ]
        
        summary = await DashboardService._get_dashboard_summary(
            mock_session, mock_property_query, start_datetime, end_datetime
        )
        
        assert isinstance(summary, DashboardSummary)
        assert summary.total_properties == 1
        assert summary.total_units == 3
        assert summary.occupied_units == 2
        assert summary.vacancy_rate == Decimal("33.33")  # 1/3 * 100
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary_empty_properties(self):
        """Test dashboard summary with no properties."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        start_datetime = datetime(2024, 1, 1, tzinfo=UTC)
        end_datetime = datetime(2024, 1, 31, tzinfo=UTC)
        
        # Mock empty properties
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.scalar.return_value = 0
        
        summary = await DashboardService._get_dashboard_summary(
            mock_session, mock_property_query, start_datetime, end_datetime
        )
        
        assert isinstance(summary, DashboardSummary)
        assert summary.total_properties == 0
        assert summary.total_units == 0
        assert summary.occupied_units == 0
        assert summary.vacancy_rate == Decimal("0.0")
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary_error_handling(self):
        """Test dashboard summary error handling."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        start_datetime = datetime(2024, 1, 1, tzinfo=UTC)
        end_datetime = datetime(2024, 1, 31, tzinfo=UTC)
        
        # Mock session to raise an error
        mock_session.execute.side_effect = Exception("Database error")
        
        with patch('Backend.api.dashboard.service.logger') as mock_logger:
            summary = await DashboardService._get_dashboard_summary(
                mock_session, mock_property_query, start_datetime, end_datetime
            )
            
            # Should return default values on error
            assert isinstance(summary, DashboardSummary)
            assert summary.total_properties == 0
            assert summary.total_units == 0
            mock_logger.error.assert_called_once()


# =============================================================================
# OCCUPANCY DATA TESTS
# =============================================================================

class TestDashboardServiceOccupancy:
    """Test occupancy data calculations."""
    
    def test_calculate_occupancy_data(self):
        """Test occupancy data calculation from summary."""
        summary = DashboardSummary(
            total_properties=5,
            total_units=10,
            occupied_units=8,
            vacancy_rate=Decimal("20.0"),
            monthly_revenue=Decimal("8000.00"),
            monthly_expenses=Decimal("2000.00"),
            outstanding_rent=Decimal("1000.00"),
            maintenance_expenses=Decimal("500.00")
        )
        
        occupancy = DashboardService._calculate_occupancy_data(summary)
        
        assert isinstance(occupancy, OccupancyData)
        assert occupancy.total_units == 10
        assert occupancy.occupied_units == 8
        assert occupancy.vacant_units == 2
        assert occupancy.occupancy_rate == Decimal("80.0")  # 100 - 20


# =============================================================================
# REVENUE TRENDS TESTS
# =============================================================================

class TestDashboardServiceRevenueTrends:
    """Test revenue trends calculations."""
    
    @pytest.mark.asyncio
    async def test_get_revenue_trends_success(self):
        """Test successful revenue trends calculation."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        
        # Mock properties result
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            create_mock_property(1), create_mock_property(2)
        ]
        
        # Mock payment and expense queries
        mock_payment_rows = [
            (date(2024, 1, 1), Decimal("5000.00")),
            (date(2024, 2, 1), Decimal("5200.00"))
        ]
        mock_expense_rows = [
            (date(2024, 1, 1), Decimal("1000.00")),
            (date(2024, 2, 1), Decimal("1100.00"))
        ]
        
        # Mock session execute calls
        mock_session.execute.side_effect = [
            # Properties query
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[create_mock_property()])))),
            # Payment query - mock the .all() method properly
            MagicMock(all=MagicMock(return_value=mock_payment_rows)),
            # Expense query - mock the .all() method properly
            MagicMock(all=MagicMock(return_value=mock_expense_rows))
        ]
        
        revenue_data = await DashboardService._get_revenue_trends(
            mock_session, mock_property_query
        )
        
        assert isinstance(revenue_data, RevenueData)
        assert len(revenue_data.months) == 12
        assert len(revenue_data.revenue) == 12
        assert len(revenue_data.expenses) == 12
        assert len(revenue_data.net_income) == 12
    
    @pytest.mark.asyncio
    async def test_get_revenue_trends_no_properties(self):
        """Test revenue trends with no properties."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        
        # Mock empty properties result
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        
        revenue_data = await DashboardService._get_revenue_trends(
            mock_session, mock_property_query
        )
        
        assert isinstance(revenue_data, RevenueData)
        assert len(revenue_data.months) == 0
        assert len(revenue_data.revenue) == 0
        assert len(revenue_data.expenses) == 0
        assert len(revenue_data.net_income) == 0
    
    @pytest.mark.asyncio
    async def test_get_revenue_trends_error_handling(self):
        """Test revenue trends error handling."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        
        # Mock session to raise an error
        mock_session.execute.side_effect = Exception("Database error")
        
        with patch('Backend.api.dashboard.service.logger') as mock_logger:
            revenue_data = await DashboardService._get_revenue_trends(
                mock_session, mock_property_query
            )
            
            # Should return empty data on error
            assert isinstance(revenue_data, RevenueData)
            assert len(revenue_data.months) == 0
            mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_revenue_trends_array_validation(self):
        """Test revenue trends array length validation."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        
        # Mock properties result
        mock_session.execute.return_value.scalars.return_value.all.return_value = [create_mock_property()]
        
        # Mock mismatched array lengths
        mock_payment_rows = [(date(2024, 1, 1), Decimal("5000.00"))]  # 1 item
        mock_expense_rows = []  # 0 items
        
        mock_session.execute.side_effect = [
            # Properties query
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[create_mock_property()])))),
            # Payment query
            MagicMock(all=MagicMock(return_value=mock_payment_rows)),
            # Expense query
            MagicMock(all=MagicMock(return_value=mock_expense_rows))
        ]
        
        with patch('Backend.api.dashboard.service.logger') as mock_logger:
            revenue_data = await DashboardService._get_revenue_trends(
                mock_session, mock_property_query
            )
            
            # Should still return valid data
            assert isinstance(revenue_data, RevenueData)
            assert len(revenue_data.months) == 12


# =============================================================================
# PAYMENTS DUE TESTS
# =============================================================================

class TestDashboardServicePaymentsDue:
    """Test payments due calculations."""
    
    @pytest.mark.asyncio
    async def test_get_payments_due_success(self):
        """Test successful payments due retrieval."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        
        # Mock properties and invoices
        mock_invoice = create_mock_invoice()
        
        mock_session.execute.side_effect = [
            # Properties query
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[create_mock_property()])))),
            # Invoices query
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_invoice]))))
        ]
        
        payments_due = await DashboardService._get_payments_due(
            mock_session, mock_property_query
        )
        
        assert len(payments_due) == 1
        assert isinstance(payments_due[0], PaymentDue)
        assert payments_due[0].id == 1
        assert payments_due[0].tenant_name == "John Doe"
        assert payments_due[0].amount == Decimal("1200.00")
    
    @pytest.mark.asyncio
    async def test_get_payments_due_no_properties(self):
        """Test payments due with no properties."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        
        # Mock empty properties result
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        
        payments_due = await DashboardService._get_payments_due(
            mock_session, mock_property_query
        )
        
        assert len(payments_due) == 0
    
    @pytest.mark.asyncio
    async def test_get_payments_due_tenant_name_fallbacks(self):
        """Test payments due tenant name fallback logic."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        
        # Create mock invoice with tenant having company name only
        mock_invoice = create_mock_invoice()
        mock_invoice.tenant.first_name = None
        mock_invoice.tenant.last_name = None
        mock_invoice.tenant.company_name = "Acme Corp"
        
        mock_session.execute.side_effect = [
            # Properties query
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[create_mock_property()])))),
            # Invoices query
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_invoice]))))
        ]
        
        payments_due = await DashboardService._get_payments_due(
            mock_session, mock_property_query
        )
        
        assert len(payments_due) == 1
        assert payments_due[0].tenant_name == "Acme Corp"
    
    @pytest.mark.asyncio
    async def test_get_payments_due_unknown_tenant(self):
        """Test payments due with unknown tenant name."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        
        # Create mock invoice with no tenant name
        mock_invoice = create_mock_invoice()
        mock_invoice.tenant.first_name = None
        mock_invoice.tenant.last_name = None
        mock_invoice.tenant.company_name = None
        
        mock_session.execute.side_effect = [
            # Properties query
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[create_mock_property()])))),
            # Invoices query
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_invoice]))))
        ]
        
        payments_due = await DashboardService._get_payments_due(
            mock_session, mock_property_query
        )
        
        assert len(payments_due) == 1
        assert payments_due[0].tenant_name == "Unknown Tenant"
    
    @pytest.mark.asyncio
    async def test_get_payments_due_overdue_calculation(self):
        """Test payments due overdue days calculation."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        
        # Create mock invoice with past due date
        mock_invoice = create_mock_invoice()
        mock_invoice.due_date = date.today() - timedelta(days=5)
        
        mock_session.execute.side_effect = [
            # Properties query
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[create_mock_property()])))),
            # Invoices query
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_invoice]))))
        ]
        
        payments_due = await DashboardService._get_payments_due(
            mock_session, mock_property_query
        )
        
        assert len(payments_due) == 1
        assert payments_due[0].days_overdue == 5
    
    @pytest.mark.asyncio
    async def test_get_payments_due_error_handling(self):
        """Test payments due error handling."""
        mock_session = AsyncMock()
        mock_property_query = MagicMock()
        
        # Mock session to raise an error
        mock_session.execute.side_effect = Exception("Database error")
        
        with patch('Backend.api.dashboard.service.logger') as mock_logger:
            payments_due = await DashboardService._get_payments_due(
                mock_session, mock_property_query
            )
            
            # Should return empty list on error
            assert len(payments_due) == 0
            mock_logger.error.assert_called_once()


# =============================================================================
# MAIN DASHBOARD SERVICE TESTS
# =============================================================================

class TestDashboardServiceMain:
    """Test main dashboard service method."""
    
    @pytest.mark.asyncio
    async def test_get_dashboard_success(self):
        """Test successful complete dashboard retrieval."""
        mock_session = AsyncMock()
        mock_user = create_mock_user("ADMIN")
        
        # Mock all service method calls
        mock_summary = DashboardSummary(
            total_properties=5, total_units=20, occupied_units=18,
            vacancy_rate=Decimal("10.0"), monthly_revenue=Decimal("15000.00"),
            monthly_expenses=Decimal("3000.00"), outstanding_rent=Decimal("2500.00"),
            maintenance_expenses=Decimal("1200.00")
        )
        
        with patch.object(DashboardService, '_calculate_date_range') as mock_date_range, \
             patch.object(DashboardService, '_build_property_query') as mock_build_query, \
             patch.object(DashboardService, '_get_dashboard_summary') as mock_get_summary, \
             patch.object(DashboardService, '_calculate_occupancy_data') as mock_calc_occupancy, \
             patch.object(DashboardService, '_get_revenue_trends') as mock_get_revenue, \
             patch.object(DashboardService, '_get_payments_due') as mock_get_payments, \
             patch('Backend.api.dashboard.service.date_to_utc_range') as mock_date_to_utc:
            
            # Setup mocks
            mock_date_range.return_value = (date(2024, 1, 1), date(2024, 1, 31))
            mock_date_to_utc.return_value = (
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 31, tzinfo=UTC)
            )
            mock_build_query.return_value = MagicMock()
            mock_get_summary.return_value = mock_summary
            mock_calc_occupancy.return_value = OccupancyData(
                total_units=20, occupied_units=18, vacant_units=2, occupancy_rate=Decimal("90.0")
            )
            mock_get_revenue.return_value = RevenueData(
                months=["Jan"], revenue=[Decimal("15000")], expenses=[Decimal("3000")], net_income=[Decimal("12000")]
            )
            mock_get_payments.return_value = [PaymentDue(
                id=1, tenant_name="John Doe", amount=Decimal("1200.00"),
                due_date=date(2024, 2, 1), days_overdue=None, status=PaymentStatus.PENDING
            )]
            
            # Call the main method
            result = await DashboardService.get_dashboard(
                session=mock_session,
                current_user=mock_user,
                property_id=None,
                time_period="month"
            )
            
            # Verify result
            summary, occupancy, revenue, payments_due = result
            assert isinstance(summary, DashboardSummary)
            assert isinstance(occupancy, OccupancyData)
            assert isinstance(revenue, RevenueData)
            assert isinstance(payments_due, list)
            assert len(payments_due) == 1
            
            # Verify all methods were called
            mock_date_range.assert_called_once()
            mock_build_query.assert_called_once()
            mock_get_summary.assert_called_once()
            mock_calc_occupancy.assert_called_once()
            mock_get_revenue.assert_called_once()
            mock_get_payments.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_dashboard_with_overrides(self):
        """Test dashboard retrieval with date overrides."""
        mock_session = AsyncMock()
        mock_user = create_mock_user("LANDLORD")
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        with patch.object(DashboardService, '_calculate_date_range') as mock_date_range, \
             patch.object(DashboardService, '_build_property_query'), \
             patch.object(DashboardService, '_get_dashboard_summary') as mock_get_summary, \
             patch.object(DashboardService, '_calculate_occupancy_data'), \
             patch.object(DashboardService, '_get_revenue_trends'), \
              patch.object(DashboardService, '_get_payments_due'), \
              patch('Backend.api.dashboard.service.date_to_utc_range') as mock_date_to_utc:
            
            # Mock minimal returns
            mock_get_summary.return_value = DashboardSummary(
                total_properties=0, total_units=0, occupied_units=0,
                vacancy_rate=Decimal("0.0"), monthly_revenue=Decimal("0.0"),
                monthly_expenses=Decimal("0.0"), outstanding_rent=Decimal("0.0"),
                maintenance_expenses=Decimal("0.0")
            )
            
            # Ensure date_to_utc_range returns a valid UTC-aware tuple for overrides path
            mock_date_to_utc.return_value = (
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 31, tzinfo=UTC)
            )

            # Call with overrides
            await DashboardService.get_dashboard(
                session=mock_session,
                current_user=mock_user,
                property_id=123,
                time_period="custom",
                start_date_override=start_date,
                end_date_override=end_date
            )
            
            # Verify date range calculation was called with overrides
            mock_date_range.assert_called_once_with("custom", start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_get_dashboard_error_handling(self):
        """Test dashboard error handling."""
        mock_session = AsyncMock()
        mock_user = create_mock_user("ADMIN")
        
        with patch.object(DashboardService, '_calculate_date_range') as mock_date_range:
            # Make date range calculation raise an error
            mock_date_range.side_effect = Exception("Date calculation error")
            
            # Should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await DashboardService.get_dashboard(
                    session=mock_session,
                    current_user=mock_user,
                    property_id=None,
                    time_period="month"
                )
            
            assert exc_info.value.status_code == 500
            assert "Failed to retrieve dashboard data" in str(exc_info.value.detail)