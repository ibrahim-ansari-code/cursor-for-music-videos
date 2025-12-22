"""
Vendor Notification Service

Handles sending email notifications for maintenance requests:
- Vendor assignment notifications
- Tenant status update notifications (when enabled)
- Landlord confirmation emails

Integrates with SendGrid via the notification email service.
"""
import logging
from typing import Optional
from uuid import UUID

import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import col

from Backend.api.notifications.sendgrid_service import SendGridService
from Backend.api.maintenance.email_templates import VendorEmailTemplates
from Backend.models.maintenance import MaintenanceRequest
from Backend.models.vendor import Vendor
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.models.enums import MaintenanceStatus
from Backend.config import settings

logger = logging.getLogger(__name__)


class VendorNotificationService:
    """Service for sending maintenance & vendor-related email notifications"""
    
    @staticmethod
    async def notify_vendor_of_assignment(
        maintenance_request: MaintenanceRequest,
        session: AsyncSession
    ) -> bool:
        """
        Send email notification to vendor when assigned to a maintenance request.
        
        Args:
            maintenance_request: The maintenance request with vendor assigned
            session: Database session for loading relationships
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Validate required fields
            if not maintenance_request.vendor_id:
                logger.warning(
                    f"Cannot send vendor notification: missing vendor_id"
                )
                return False
            
            # Load all required relationships
            vendor = await VendorNotificationService._load_vendor(
                maintenance_request.vendor_id,
                session
            )
            
            if not vendor or not vendor.email:
                logger.warning(
                    f"Cannot send vendor notification: vendor {maintenance_request.vendor_id} has no email"
                )
                return False
            
            property_obj = await VendorNotificationService._load_property(
                maintenance_request.property_id,
                session
            )
            
            if not property_obj:
                logger.warning(f"Cannot send vendor notification: property not found")
                return False
            
            unit = None
            if maintenance_request.unit_id:
                unit = await VendorNotificationService._load_unit(
                    maintenance_request.unit_id,
                    session
                )
            
            tenant = None
            if maintenance_request.tenant_id:
                tenant = await VendorNotificationService._load_tenant(
                    maintenance_request.tenant_id,
                    session
                )
            
            # Load landlord from property owner, not maintenance_request.user_id
            # (maintenance_request.user_id might be the tenant who created the request)
            landlord = await VendorNotificationService._load_user(
                property_obj.user_id,
                session
            )
            
            # Generate email
            subject, html_body = VendorEmailTemplates.create_vendor_assignment_email(
                vendor_name=vendor.contact_person or vendor.company_name,
                vendor_email=vendor.email,
                landlord_name=f"{landlord.first_name} {landlord.last_name}" if landlord else "Property Owner",
                landlord_email=landlord.email if landlord else "",
                landlord_phone=landlord.phone if landlord else None,
                property_address=property_obj.address if property_obj else "Unknown Property",
                unit_number=unit.name if unit else None,
                tenant_name=f"{tenant.first_name} {tenant.last_name}" if tenant else None,
                tenant_phone=tenant.phone if tenant else None,
                issue_title=maintenance_request.issue_title,
                issue_description=maintenance_request.description,
                priority=maintenance_request.priority,
                estimated_cost=maintenance_request.estimated_cost,
                scheduled_date=maintenance_request.scheduled_date,
                photos=maintenance_request.photos,
                request_id=maintenance_request.id or 0,
                frontend_url=settings.FRONTEND_URL
            )
            
            # Send email via SendGrid
            success = await SendGridService.send_raw_email(
                to_email=vendor.email,
                to_name=vendor.contact_person or vendor.company_name,
                subject=subject,
                html_content=html_body
            )
            
            if success:
                logger.info(
                    f"Vendor assignment email sent successfully to {vendor.email}",
                    extra={
                        'maintenance_request_id': maintenance_request.id,
                        'vendor_id': vendor.id,
                        'notification_type': 'vendor_assignment'
                    }
                )
            else:
                logger.error(
                    f"Failed to send vendor assignment email to {vendor.email}",
                    extra={
                        'maintenance_request_id': maintenance_request.id,
                        'vendor_id': vendor.id
                    }
                )
            
            return success
            
        except Exception as e:
            logger.exception(f"Error sending vendor assignment notification")
            sentry_sdk.capture_exception(e, extra={
                'maintenance_request_id': maintenance_request.id,
                'vendor_id': maintenance_request.vendor_id,
                'notification_type': 'vendor_assignment'
            })
            return False
    
    @staticmethod
    async def notify_landlord_of_assignment(
        maintenance_request: MaintenanceRequest,
        session: AsyncSession
    ) -> bool:
        """
        Send confirmation email to landlord after assigning vendor.
        
        Args:
            maintenance_request: The maintenance request
            session: Database session
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Validate required fields
            if not maintenance_request.vendor_id:
                logger.warning(f"Cannot send landlord confirmation: missing vendor_id")
                return False
            
            vendor = await VendorNotificationService._load_vendor(
                maintenance_request.vendor_id,
                session
            )
            
            if not vendor:
                logger.warning(f"Cannot send landlord confirmation: vendor not found")
                return False
            
            property_obj = await VendorNotificationService._load_property(
                maintenance_request.property_id,
                session
            )
            
            if not property_obj:
                logger.warning(f"Cannot send landlord confirmation: property not found")
                return False
            
            # Load landlord from property owner, not maintenance_request.user_id
            # (maintenance_request.user_id might be the tenant who created the request)
            landlord = await VendorNotificationService._load_user(
                property_obj.user_id,
                session
            )
            
            if not landlord or not landlord.email:
                logger.warning(f"Cannot send landlord confirmation: no email")
                return False
            
            unit = None
            if maintenance_request.unit_id:
                unit = await VendorNotificationService._load_unit(
                    maintenance_request.unit_id,
                    session
                )
            
            # Generate email
            subject, html_body = VendorEmailTemplates.create_landlord_confirmation_email(
                landlord_name=f"{landlord.first_name} {landlord.last_name}",
                vendor_name=vendor.contact_person or "",
                vendor_company=vendor.company_name,
                property_address=property_obj.address if property_obj else "Unknown Property",
                unit_number=unit.name if unit else None,
                issue_title=maintenance_request.issue_title,
                request_id=maintenance_request.id or 0,
                frontend_url=settings.FRONTEND_URL
            )
            
            # Send email
            success = await SendGridService.send_raw_email(
                to_email=landlord.email,
                to_name=f"{landlord.first_name} {landlord.last_name}",
                subject=subject,
                html_content=html_body
            )
            
            if success:
                logger.info(
                    f"Landlord confirmation email sent to {landlord.email}",
                    extra={
                        'maintenance_request_id': maintenance_request.id,
                        'notification_type': 'landlord_confirmation'
                    }
                )
            
            return success
            
        except Exception as e:
            logger.exception("Error sending landlord confirmation")
            sentry_sdk.capture_exception(e)
            return False
    
    @staticmethod
    async def notify_tenant_of_status_change(
        maintenance_request: MaintenanceRequest,
        old_status: MaintenanceStatus,
        new_status: MaintenanceStatus,
        session: AsyncSession
    ) -> bool:
        """
        Send status update email to tenant (Uber Eats style).
        
        Only sends if maintenance_request.notify_tenant is True.
        
        Args:
            maintenance_request: The maintenance request
            old_status: Previous status
            new_status: New status
            session: Database session
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Check if tenant notifications are enabled
            if not maintenance_request.notify_tenant:
                logger.debug(
                    f"Skipping tenant notification for request {maintenance_request.id}: notify_tenant=False"
                )
                return True  # Not an error, just disabled
            
            # Check if tenant exists
            if not maintenance_request.tenant_id:
                logger.debug(
                    f"Skipping tenant notification for request {maintenance_request.id}: no tenant"
                )
                return True
            
            # Load tenant
            tenant = await VendorNotificationService._load_tenant(
                maintenance_request.tenant_id,
                session
            )
            
            if not tenant or not tenant.email:
                logger.warning(
                    f"Cannot send tenant notification: tenant {maintenance_request.tenant_id} has no email"
                )
                return False
            
            # Load other entities
            property_obj = await VendorNotificationService._load_property(
                maintenance_request.property_id,
                session
            )
            
            unit = None
            if maintenance_request.unit_id:
                unit = await VendorNotificationService._load_unit(
                    maintenance_request.unit_id,
                    session
                )
            
            vendor = None
            vendor_company = None
            vendor_phone = None
            vendor_email = None
            if maintenance_request.vendor_id:
                vendor = await VendorNotificationService._load_vendor(
                    maintenance_request.vendor_id,
                    session
                )
                if vendor:
                    vendor_company = vendor.company_name
                    vendor_phone = vendor.phone
                    vendor_email = vendor.email
            
            # Generate email - use TENANT_PORTAL_URL for tenant emails
            subject, html_body = VendorEmailTemplates.create_tenant_status_update_email(
                tenant_name=f"{tenant.first_name} {tenant.last_name}",
                tenant_email=tenant.email,
                property_address=property_obj.address if property_obj else "Unknown Property",
                unit_number=unit.name if unit else None,
                issue_title=maintenance_request.issue_title,
                old_status=old_status,
                new_status=new_status,
                vendor_name=vendor.contact_person if vendor else None,
                vendor_company=vendor_company,
                vendor_phone=vendor_phone,
                vendor_email=vendor_email,
                request_id=maintenance_request.id or 0,
                tenant_portal_url=settings.TENANT_PORTAL_URL
            )
            
            # Send email
            success = await SendGridService.send_raw_email(
                to_email=tenant.email,
                to_name=f"{tenant.first_name} {tenant.last_name}",
                subject=subject,
                html_content=html_body
            )
            
            if success:
                logger.info(
                    f"Tenant status update email sent to {tenant.email}",
                    extra={
                        'maintenance_request_id': maintenance_request.id,
                        'tenant_id': tenant.id,
                        'old_status': old_status.value,
                        'new_status': new_status.value,
                        'notification_type': 'tenant_status_update'
                    }
                )
            
            return success
            
        except Exception as e:
            logger.exception("Error sending tenant status update")
            sentry_sdk.capture_exception(e)
            return False
    
    # Helper methods to load relationships
    
    @staticmethod
    async def _load_vendor(vendor_id: int, session: AsyncSession) -> Optional[Vendor]:
        """Load vendor by ID"""
        result = await session.execute(
            select(Vendor).where(col(Vendor.id) == vendor_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def _load_property(property_id: int, session: AsyncSession) -> Optional[Property]:
        """Load property"""
        result = await session.execute(
            select(Property).where(col(Property.id) == property_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def _load_unit(unit_id: int, session: AsyncSession) -> Optional[PropertyUnit]:
        """Load property unit"""
        result = await session.execute(
            select(PropertyUnit).where(col(PropertyUnit.id) == unit_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def _load_tenant(tenant_id: int, session: AsyncSession) -> Optional[Tenant]:
        """Load tenant"""
        stmt = select(Tenant).where(col(Tenant.id) == tenant_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def _load_user(user_id: UUID, session: AsyncSession) -> Optional[User]:
        """Load user (landlord)"""
        result = await session.execute(
            select(User).where(col(User.id) == user_id)
        )
        return result.scalar_one_or_none()

