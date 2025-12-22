import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.enums import UserType
from Backend.models.user import User

from .schemas import DashboardResponse, TenantDashboardResponse
from .service import DashboardService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_model=DashboardResponse)
async def get_dashboard_data(
    property_id: int | None = None,
    time_period: str = "month",
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DashboardResponse:
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access dashboard data",
        )

    summary, occupancy, revenue, payments_due = await DashboardService.get_dashboard(
        session=session,
        current_user=current_user,
        property_id=property_id,
        time_period=time_period,
        start_date_override=start_date,
        end_date_override=end_date,
    )

    return DashboardResponse(
        summary=summary,
        occupancy=occupancy,
        revenue=revenue,
        payments_due=payments_due,
    )


@router.get("/tenant", response_model=TenantDashboardResponse)
async def get_tenant_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TenantDashboardResponse:
    """Get dashboard data for tenant users."""
    if current_user.user_type != UserType.TENANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access tenant dashboard data",
        )

    (
        my_unit_section,
        monthly_rent_section,
        next_payment_section,
        maintenance_section,
    ) = await DashboardService.get_tenant_dashboard(
        session=session,
        current_user=current_user,
    )

    return TenantDashboardResponse(
        my_unit=my_unit_section,
        monthly_rent=monthly_rent_section,
        next_payment=next_payment_section,
        maintenance=maintenance_section,
    )
