"""
Tool handlers for the Brikli Assistant

This module implements the actual logic for each tool that the assistant can use.
All handlers ensure proper data scoping to the authenticated user.
"""
import json
import logging
from typing import Any, Dict, List, Union
from uuid import UUID
from datetime import datetime, timedelta, date, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from sqlmodel import col

from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.tenant import Tenant, TenantUnitLink
from Backend.models.lease import Lease
from Backend.models.accounting.payment import Payment
from Backend.models.accounting.invoice import Invoice
from Backend.models.accounting.expense import Expense
from Backend.models.maintenance import MaintenanceRequest

# Import existing schemas instead of creating duplicates
from Backend.api.tenants.schemas import TenantResponse, LeaseResponseSimple
from Backend.api.properties.schemas import PropertyResponse
from Backend.api.leases.schemas import LeaseResponse
from Backend.api.maintenance.schemas import MaintenanceSummaryResponse
from Backend.api.dashboard.schemas import DashboardSummary

logger = logging.getLogger(__name__)


class ToolHandlers:
    """Handlers for Azure AI Assistant tool calls"""

    @staticmethod
    async def handle_tool_call(
        tool_name: str,
        arguments: str,
        user_id: UUID,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Route tool calls to appropriate handlers

        Args:
            tool_name: Name of the tool to execute
            arguments: JSON string of tool arguments
            user_id: ID of the user making the request
            session: Database session

        Returns:
            Tool execution results
        """
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON arguments for tool {tool_name}: {e}")
            return {"error": "Invalid arguments format", "details": str(e)}

        handlers = {
            "search_properties": ToolHandlers.search_properties,
            "get_tenant_info": ToolHandlers.get_tenant_info,
            "search_lease_documents": ToolHandlers.search_lease_documents,
            "get_financial_summary": ToolHandlers.get_financial_summary,
            "get_maintenance_requests": ToolHandlers.get_maintenance_requests,
            "get_lease_expiry_info": ToolHandlers.get_lease_expiry_info,
            "get_payment_status": ToolHandlers.get_payment_status,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            result = await handler(args, user_id, session)
            # Log successful tool execution for analytics
            logger.info(f"Tool {tool_name} executed successfully for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Error in tool {tool_name} for user {user_id}: {str(e)}", exc_info=True)
            return {"error": f"Tool execution failed: {str(e)}"}

    @staticmethod
    async def search_properties(args: Dict[str, Any], user_id: UUID, session: AsyncSession) -> Dict[str, Any]:
        """Search for properties based on criteria"""

        # Build query
        query = select(Property).where(col(Property.user_id) == user_id)

        # Apply filters
        if args.get("status") and args["status"] != "All":
            # Map status to PropertyStatus enum values
            status_map = {"Active": "ACTIVE", "Inactive": "INACTIVE"}
            if args["status"] in status_map:
                query = query.where(col(Property.status) == status_map[args["status"]])

        if args.get("city"):
            query = query.where(col(Property.city).ilike(f"%{args['city']}%"))

        if args.get("property_type") and args["property_type"] != "All":
            query = query.where(col(Property.property_type) == args["property_type"])

        # Execute query with units loaded
        query = query.options(selectinload(getattr(Property, "units")))
        result = await session.execute(query)
        properties = result.scalars().all()

        # Filter by rent range and vacancy if needed
        property_data: List[Dict[str, Any]] = []
        for prop in properties:
            # Calculate property metrics
            total_units = len(prop.units)
            vacant_units = sum(1 for unit in prop.units if not unit.is_rented)
            occupied_units = total_units - vacant_units

            # Calculate rent range
            if prop.units:
                rents = [unit.monthly_rent for unit in prop.units if unit.monthly_rent]
                min_rent = min(rents) if rents else 0
                max_rent = max(rents) if rents else 0
                total_potential_rent = sum(unit.monthly_rent or 0 for unit in prop.units)
                actual_rent = sum(unit.monthly_rent or 0 for unit in prop.units if unit.is_rented)
            else:
                min_rent = max_rent = total_potential_rent = actual_rent = 0

            # Apply rent filters
            if args.get("min_rent") and max_rent < args["min_rent"]:
                continue
            if args.get("max_rent") and min_rent > args["max_rent"]:
                continue

            # Apply vacancy filter
            if args.get("has_vacancies") and vacant_units == 0:
                continue

            property_data.append({
                "id": str(prop.id),
                "name": prop.name,
                "address": f"{prop.address}, {prop.city}, {prop.province} {prop.postal_code}",
                "status": prop.status.value if hasattr(prop.status, 'value') else str(prop.status),
                "type": prop.property_type,
                "total_units": total_units,
                "vacant_units": vacant_units,
                "occupied_units": occupied_units,
                "occupancy_rate": float((occupied_units / total_units * 100) if total_units > 0 else 0),
                "rent_range": f"${min_rent:,.0f} - ${max_rent:,.0f}" if min_rent != max_rent else f"${min_rent:,.0f}",
                "monthly_income": float(actual_rent),
                "potential_income": float(total_potential_rent),
                "created_at": prop.created_at.isoformat() if prop.created_at else None
            })

        return {
            "properties": property_data,
            "total": len(property_data),
            "summary": {
                "total_properties": len(property_data),
                "total_units": sum(p["total_units"] for p in property_data),
                "total_vacant": sum(p["vacant_units"] for p in property_data),
                "average_occupancy": sum(p["occupancy_rate"] for p in property_data) / len(property_data) if property_data else 0,
                "total_monthly_income": sum(p["monthly_income"] for p in property_data)
            }
        }

    @staticmethod
    async def get_tenant_info(args: Dict[str, Any], user_id: UUID, session: AsyncSession) -> Dict[str, Any]:
        """Get tenant information with optional payment history"""

        # Build query
        query = select(Tenant).where(col(Tenant.landlord_id) == user_id)

        # Apply filters
        if args.get("tenant_name"):
            name = args["tenant_name"].lower()
            query = query.where(
                or_(
                    func.lower(col(Tenant.first_name)).contains(name),
                    func.lower(col(Tenant.last_name)).contains(name),
                    func.lower(func.concat(col(Tenant.first_name), ' ', col(Tenant.last_name))).contains(name)
                )
            )

        if args.get("property_id"):
            try:
                property_id = int(args["property_id"])
                query = query.where(col(Tenant.current_property_id) == property_id)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid property_id format: {args['property_id']}")
                return {"error": "Invalid property_id: must be a valid integer"}

        if args.get("unit_id"):
            try:
                unit_id = int(args["unit_id"])
                # Join through the TenantUnitLink table
                query = query.join(TenantUnitLink, col(Tenant.id) == col(TenantUnitLink.tenant_id)).where(
                    col(TenantUnitLink.unit_id) == unit_id
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid unit_id format: {args['unit_id']}")
                return {"error": "Invalid unit_id: must be a valid integer"}

        if args.get("status") and args["status"] != "All":
            query = query.where(col(Tenant.status) == args["status"])

        # Execute query with proper relationships
        result = await session.execute(query.options(
            selectinload(getattr(Tenant, "current_property")),
            selectinload(getattr(Tenant, "assigned_units"))
        ))
        tenants = result.scalars().all()

        tenant_data: List[Dict[str, Any]] = []
        for tenant in tenants:
            # Get unit name if tenant has assigned units
            unit_name = None
            if tenant.assigned_units:
                unit_name = tenant.assigned_units[0].name

            data: Dict[str, Any] = {
                "id": str(tenant.id),
                "name": f"{tenant.first_name} {tenant.last_name}",
                "email": tenant.email,
                "phone": tenant.phone,
                "status": tenant.status.value if hasattr(tenant.status, 'value') else str(tenant.status),
                "unit": unit_name,
                "property": tenant.current_property.name if tenant.current_property else None
            }

            # Get current lease if requested
            if args.get("include_lease_details", True):
                lease_result = await session.execute(
                    select(Lease).where(
                        and_(
                            col(Lease.tenant_id) == tenant.id,
                            col(Lease.status).in_(["Active", "Pending"])
                        )
                    ).order_by(desc(col(Lease.start_date)))
                )
                lease = lease_result.scalar_one_or_none()

                if lease:
                    data["lease"] = {
                        "id": str(lease.id),
                        "start_date": lease.start_date.isoformat(),
                        "end_date": lease.end_date.isoformat(),
                        "monthly_rent": float(lease.monthly_rent),
                        "status": lease.status.value if hasattr(lease.status, 'value') else str(lease.status),
                        "days_until_expiry": (lease.end_date - date.today()).days
                    }

            # Get payment history if requested
            if args.get("include_payment_history"):
                payments_result = await session.execute(
                    select(Payment).where(
                        col(Payment.tenant_id) == tenant.id
                    ).order_by(desc(col(Payment.payment_date))).limit(6)
                )
                payments = payments_result.scalars().all()

                data["recent_payments"] = [
                    {
                        "id": str(p.id),
                        "date": p.payment_date.isoformat(),
                        "amount": float(p.amount),
                        "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
                        "payment_method": p.payment_method,
                        "transaction_reference": p.transaction_reference
                    }
                    for p in payments
                ]

            tenant_data.append(data)

        return {
            "tenants": tenant_data,
            "total": len(tenant_data)
        }

    @staticmethod
    async def search_lease_documents(args: Dict[str, Any], user_id: UUID, session: AsyncSession) -> Dict[str, Any]:
        """Search through documents using vector similarity"""

        # Import here to avoid circular dependency
        from Backend.llm.embedding_service import EmbeddingService  # type: ignore

        embedding_service = EmbeddingService()

        # Perform semantic search
        results = await embedding_service.search_documents(
            query=args["query"],
            user_id=user_id,
            document_type=args.get("document_type", "all"),
            limit=args.get("limit", 5),
            session=session
        )

        if not results:
            return {
                "found": False,
                "message": f"No relevant information found for: {args['query']}",
                "results": []
            }

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "content": result["content"],
                "source_type": result["source_type"],
                "source_id": result["source_id"],
                "relevance_score": f"{result['similarity']:.2%}",
                "metadata": result.get("chunk_metadata", {})
            })

        # Create context summary
        context_summary = "\n\n".join([
            f"[Source: {r['source_type']} - Relevance: {r['relevance_score']}]\n{r['content']}"
            for r in formatted_results
        ])

        return {
            "found": True,
            "query": args["query"],
            "results": formatted_results,
            "total_results": len(formatted_results),
            "context_summary": context_summary
        }

    @staticmethod
    async def get_financial_summary(args: Dict[str, Any], user_id: UUID, session: AsyncSession) -> Dict[str, Any]:
        """Get financial summary for specified period"""

        # Determine date range
        end_date = datetime.now().date()
        start_date = end_date

        period = args["period"]
        if period == "current_month":
            start_date = end_date.replace(day=1)
        elif period == "last_month":
            last_month = end_date.replace(day=1) - timedelta(days=1)
            start_date = last_month.replace(day=1)
            end_date = last_month
        elif period == "current_quarter":
            quarter = (end_date.month - 1) // 3
            start_date = end_date.replace(month=quarter*3 + 1, day=1)
        elif period == "last_quarter":
            current_quarter = (end_date.month - 1) // 3
            if current_quarter == 0:
                start_date = end_date.replace(year=end_date.year - 1, month=10, day=1)
                end_date = end_date.replace(year=end_date.year - 1, month=12, day=31)
            else:
                start_date = end_date.replace(month=(current_quarter-1)*3 + 1, day=1)
                end_date = start_date.replace(month=start_date.month + 2)
                end_date = end_date.replace(day=1) - timedelta(days=1)
        elif period == "current_year":
            start_date = end_date.replace(month=1, day=1)
        elif period == "last_year":
            start_date = end_date.replace(year=end_date.year - 1, month=1, day=1)
            end_date = end_date.replace(year=end_date.year - 1, month=12, day=31)
        elif period == "custom":
            if not args.get("start_date") or not args.get("end_date"):
                return {"error": "start_date and end_date are required for custom period"}
            start_date = datetime.fromisoformat(args["start_date"]).date()
            end_date = datetime.fromisoformat(args["end_date"]).date()

        # Build queries
        property_id = args.get("property_id")
        property_id_int = int(property_id) if property_id else None

        # Get income (payments)
        payment_query = select(Payment).join(
            Tenant, col(Payment.tenant_id) == col(Tenant.id)
        ).where(
            and_(
                col(Tenant.landlord_id) == user_id,
                col(Payment.payment_date) >= start_date,
                col(Payment.payment_date) <= end_date,
                col(Payment.status).in_(["Paid", "Partial"])
            )
        )

        if property_id_int:
            payment_query = payment_query.where(
                col(Tenant.current_property_id) == property_id_int
            )

        # Get expenses
        expense_query = select(Expense).join(
            Property, col(Expense.property_id) == col(Property.id)
        ).where(
            and_(
                col(Property.user_id) == user_id,
                col(Expense.expense_date) >= start_date,
                col(Expense.expense_date) <= end_date
            )
        )

        if property_id_int:
            expense_query = expense_query.where(col(Expense.property_id) == property_id_int)

        # Execute queries
        payment_result = await session.execute(payment_query)
        payments = payment_result.scalars().all()

        expense_result = await session.execute(expense_query)
        expenses = expense_result.scalars().all()

        # Calculate totals
        total_income = sum(float(p.amount) for p in payments)
        total_expenses = sum(float(e.total_amount) for e in expenses)
        net_income = total_income - total_expenses

        # Prepare response
        summary: Dict[str, Any] = {
            "period": {
                "type": period,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "income": {
                "total": total_income,
                "payment_count": len(payments),
                "average_payment": total_income / len(payments) if payments else 0
            },
            "expenses": {
                "total": total_expenses,
                "expense_count": len(expenses),
                "average_expense": total_expenses / len(expenses) if expenses else 0
            },
            "net_income": net_income,
            "profit_margin": (net_income / total_income * 100) if total_income > 0 else 0
        }

        # Add details if requested
        if args.get("include_details"):
            # Group expenses by category
            expense_by_category: Dict[str, Dict[str, Union[int, float]]] = {}
            for expense in expenses:
                category = expense.category or "Uncategorized"
                if category not in expense_by_category:
                    expense_by_category[category] = {"count": 0, "total": 0.0}
                expense_by_category[category]["count"] += 1
                expense_by_category[category]["total"] += float(expense.total_amount)

            summary["expense_breakdown"] = dict(expense_by_category)

            # Add top expenses
            top_expenses = sorted(expenses, key=lambda e: e.total_amount, reverse=True)[:5]
            top_expenses_list = [
                {
                    "description": e.description,
                    "amount": float(e.total_amount),
                    "date": e.expense_date.isoformat(),
                    "category": e.category
                }
                for e in top_expenses
            ]
            summary["top_expenses"] = top_expenses_list

        return dict(summary)

    @staticmethod
    async def get_maintenance_requests(args: Dict[str, Any], user_id: UUID, session: AsyncSession) -> Dict[str, Any]:
        """Get maintenance requests based on filters"""

        # Build query
        query = select(MaintenanceRequest).join(
            Property, col(MaintenanceRequest.property_id) == col(Property.id)
        ).where(col(Property.user_id) == user_id)

        # Apply filters
        if args.get("status") and args["status"] != "All":
            query = query.where(col(MaintenanceRequest.status) == args["status"])

        if args.get("priority") and args["priority"] != "All":
            query = query.where(col(MaintenanceRequest.priority) == args["priority"])

        if args.get("property_id"):
            query = query.where(col(MaintenanceRequest.property_id) == int(args["property_id"]))

        if args.get("unit_id"):
            query = query.where(col(MaintenanceRequest.unit_id) == int(args["unit_id"]))

        if args.get("days"):
            cutoff_date = datetime.now() - timedelta(days=args["days"])
            query = query.where(col(MaintenanceRequest.created_at) >= cutoff_date)

        if not args.get("include_completed", True):
            query = query.where(col(MaintenanceRequest.status) != "Completed")

        # Order by priority and date
        query = query.order_by(
            desc(col(MaintenanceRequest.priority)),
            desc(col(MaintenanceRequest.created_at))
        )

        # Execute with related data
        query = query.options(
            selectinload(getattr(MaintenanceRequest, "property")),
            selectinload(getattr(MaintenanceRequest, "unit")),
            selectinload(getattr(MaintenanceRequest, "tenant"))
        )
        result = await session.execute(query)
        requests = result.scalars().all()

        # Format results
        request_data = []
        for req in requests:
            request_data.append({
                "id": str(req.id),
                "title": req.issue_title,
                "description": req.description,
                "status": req.status.value if hasattr(req.status, 'value') else str(req.status),
                "priority": req.priority.value if hasattr(req.priority, 'value') else str(req.priority),
                "property": req.property.name if req.property else None,
                "unit": req.unit.name if req.unit else None,
                "tenant": f"{req.tenant.first_name} {req.tenant.last_name}" if req.tenant else None,
                "created_at": req.created_at.isoformat(),
                "scheduled_date": req.scheduled_date.isoformat() if req.scheduled_date else None,
                "completed_date": req.completed_date.isoformat() if req.completed_date else None,
                "estimated_cost": float(req.estimated_cost) if req.estimated_cost else None,
                "actual_cost": float(req.actual_cost) if req.actual_cost else None,
                "days_open": (datetime.now(UTC) - req.created_at).days if req.status.upper() != "COMPLETED" else None,
                # "preferred_time": req.preferred_time.isoformat() if req.preferred_time else None
            })

        # Calculate summary statistics
        summary: Dict[str, Any] = {
            "total_requests": len(request_data),
            "by_status": {},
            "by_priority": {},
            "average_days_to_complete": 0.0,
            "total_estimated_cost": 0.0,
            "total_actual_cost": 0.0
        }

        completed_times = []
        for req in requests:
            # Count by status
            status = req.status.value if hasattr(req.status, 'value') else str(req.status)
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

            # Count by priority
            priority = req.priority.value if hasattr(req.priority, 'value') else str(req.priority)
            summary["by_priority"][priority] = summary["by_priority"].get(priority, 0) + 1

            # Calculate costs
            if req.estimated_cost:
                summary["total_estimated_cost"] += float(req.estimated_cost)
            if req.actual_cost:
                summary["total_actual_cost"] += float(req.actual_cost)

            # Calculate completion time
            if req.completed_date and req.created_at:
                days_to_complete = (req.completed_date - req.created_at).days
                completed_times.append(days_to_complete)

        if completed_times:
            summary["average_days_to_complete"] = sum(completed_times) / len(completed_times)

        return {
            "requests": request_data,
            "total": len(request_data),
            "summary": summary
        }

    @staticmethod
    async def get_lease_expiry_info(args: Dict[str, Any], user_id: UUID, session: AsyncSession) -> Dict[str, Any]:
        """Get information about upcoming lease expirations"""

        days_ahead = args.get("days_ahead", 90)
        cutoff_date = date.today() + timedelta(days=days_ahead)

        # Build query
        query = select(Lease).join(
            Tenant, col(Lease.tenant_id) == col(Tenant.id)
        ).where(
            and_(
                col(Tenant.landlord_id) == user_id,
                col(Lease.status) == "ACTIVE"
            )
        )

        # Include expired if requested
        if args.get("include_expired"):
            query = query.where(
                or_(
                    col(Lease.end_date) <= cutoff_date,
                    col(Lease.end_date) < date.today()
                )
            )
        else:
            query = query.where(
                and_(
                    col(Lease.end_date) <= cutoff_date,
                    col(Lease.end_date) >= date.today()
                )
            )

        # Filter by property if specified
        if args.get("property_id"):
            query = query.join(
                PropertyUnit, col(Lease.unit_id) == col(PropertyUnit.id)
            ).where(col(PropertyUnit.property_id) == int(args["property_id"]))

        # Order by expiry date
        query = query.order_by(col(Lease.end_date))

        # Execute with related data
        query = query.options(
            selectinload(getattr(Lease, "tenant")),
            selectinload(getattr(Lease, "unit")).selectinload(getattr(PropertyUnit, "property"))
        )
        result = await session.execute(query)
        leases = result.scalars().all()

        # Format results
        lease_data: List[Dict[str, Any]] = []
        for lease in leases:
            days_until_expiry = (lease.end_date - date.today()).days
            status = "Expired" if days_until_expiry < 0 else f"Expires in {days_until_expiry} days"

            lease_data.append({
                "id": str(lease.id),
                "tenant": f"{lease.tenant.first_name} {lease.tenant.last_name}" if lease.tenant else None,
                "property": lease.unit.property.name if lease.unit and lease.unit.property else None,
                "unit": lease.unit.name if lease.unit else None,
                "start_date": lease.start_date.isoformat(),
                "end_date": lease.end_date.isoformat(),
                "monthly_rent": float(lease.monthly_rent),
                "days_until_expiry": days_until_expiry,
                "status": status,
                "renewal_status": "Needs attention" if days_until_expiry < 30 else "Upcoming"
            })

        # Group by urgency
        urgent = [l for l in lease_data if l["days_until_expiry"] < 30]
        upcoming = [l for l in lease_data if 30 <= l["days_until_expiry"] <= 60]
        future = [l for l in lease_data if l["days_until_expiry"] > 60]
        expired = [l for l in lease_data if l["days_until_expiry"] < 0]

        return {
            "leases": lease_data,
            "total": len(lease_data),
            "summary": {
                "expired": len(expired),
                "urgent": len(urgent),
                "upcoming": len(upcoming),
                "future": len(future),
                "total_monthly_rent_at_risk": sum(l["monthly_rent"] for l in lease_data)
            },
            "by_urgency": {
                "expired": expired,
                "urgent": urgent,
                "upcoming": upcoming,
                "future": future
            }
        }

    @staticmethod
    async def get_payment_status(args: Dict[str, Any], user_id: UUID, session: AsyncSession) -> Dict[str, Any]:
        """Get current payment status and outstanding balances"""

        # Get current date info
        today = date.today()
        current_month_start = today.replace(day=1)

        # Build invoice query
        invoice_query = select(Invoice).join(
            Tenant, col(Invoice.tenant_id) == col(Tenant.id)
        ).where(
            and_(
                col(Tenant.landlord_id) == user_id,
                col(Invoice.due_date) >= current_month_start - timedelta(days=90)  # Last 3 months
            )
        )

        # Apply filters
        status_filter = args.get("status", "all")
        if status_filter == "overdue":
            invoice_query = invoice_query.where(
                and_(
                    col(Invoice.status).in_(["Pending", "Partial"]),
                    col(Invoice.due_date) < today
                )
            )
        elif status_filter == "pending":
            invoice_query = invoice_query.where(
                and_(
                    col(Invoice.status) == "Pending",
                    col(Invoice.due_date) >= today
                )
            )
        elif status_filter == "paid":
            invoice_query = invoice_query.where(col(Invoice.status) == "Paid")

        if args.get("property_id"):
            invoice_query = invoice_query.where(
                col(Tenant.current_property_id) == int(args["property_id"])
            )

        if args.get("tenant_id"):
            invoice_query = invoice_query.where(col(Invoice.tenant_id) == int(args["tenant_id"]))

        # Execute query
        invoice_query = invoice_query.options(
            selectinload(getattr(Invoice, "tenant"))
        )
        result = await session.execute(invoice_query)
        invoices = result.scalars().all()

        # Process results
        payment_data = []
        total_outstanding = 0.0
        total_overdue = 0.0

        for invoice in invoices:
            # Need to calculate paid amount separately since Invoice doesn't have payments relationship
            # For now, we'll use the invoice amount and status
            # Get the actual status value
            status_value = invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status)
            paid_amount = float(invoice.amount) if status_value == "Paid" else 0
            balance = float(invoice.amount) - paid_amount
            is_overdue = invoice.due_date.date() < today and balance > 0

            if is_overdue:
                total_overdue += balance
            if balance > 0:
                total_outstanding += balance

            payment_info = {
                "invoice_id": str(invoice.id),
                "tenant": f"{invoice.tenant.first_name} {invoice.tenant.last_name}" if invoice.tenant else None,
                "due_date": invoice.due_date.isoformat(),
                "total_amount": float(invoice.amount),
                "paid_amount": paid_amount,
                "balance": balance,
                "status": invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status),
                "is_overdue": is_overdue,
                "days_overdue": (today - invoice.due_date.date()).days if is_overdue else 0
            }

            # Note: Payment history would need to be fetched separately
            # as Invoice model doesn't have a payments relationship

            payment_data.append(payment_info)

        # Sort by urgency
        payment_data.sort(key=lambda x: (not x["is_overdue"], x["due_date"]))

        return {
            "payments": payment_data,
            "total": len(payment_data),
            "summary": {
                "total_outstanding": total_outstanding,
                "total_overdue": total_overdue,
                "overdue_count": sum(1 for p in payment_data if p["is_overdue"]),
                "pending_count": sum(1 for p in payment_data if p["status"] == "Pending"),
                "paid_count": sum(1 for p in payment_data if p["status"] == "Paid")
            }
        }