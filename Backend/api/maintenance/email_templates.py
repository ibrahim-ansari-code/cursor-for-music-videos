"""
Maintenance & Vendor Email Templates

Professional email templates for maintenance request notifications
using the Brikli brand design system.
"""
from typing import Optional
from decimal import Decimal
from datetime import date

from Backend.api.notifications.email_templates import (
    BrikliEmailTemplate,
    EmailSection,
    EmailNotice,
    EmailCTA,
    EmailMetadataRow
)
from Backend.models.enums import MaintenancePriority, MaintenanceStatus


class VendorEmailTemplates:
    """Email templates for vendor notifications"""
    
    @staticmethod
    def create_vendor_assignment_email(
        vendor_name: str,
        vendor_email: str,
        landlord_name: str,
        landlord_email: str,
        landlord_phone: Optional[str],
        property_address: str,
        unit_number: Optional[str],
        tenant_name: Optional[str],
        tenant_phone: Optional[str],
        issue_title: str,
        issue_description: Optional[str],
        priority: MaintenancePriority,
        estimated_cost: Optional[Decimal],
        scheduled_date: Optional[date],
        photos: Optional[list[str]],
        request_id: int,
        frontend_url: str
    ) -> tuple[str, str]:
        """
        Generate email for vendor assignment notification.
        
        Returns:
            tuple: (subject, html_body)
        """
        
        # Build greeting
        greeting = f"Hi {vendor_name}," if vendor_name else "Hi there,"
        
        # Build content sections
        sections = [
            EmailSection(
                text=f"You've been assigned a new maintenance request by {landlord_name}."
            ),
        ]
        
        # Build metadata rows
        metadata = [
            EmailMetadataRow(label="Property", value=property_address, emoji="📍"),
        ]
        
        if unit_number:
            metadata.append(EmailMetadataRow(label="Unit", value=unit_number, emoji="🏠"))
        
        if tenant_name:
            tenant_contact = tenant_name
            if tenant_phone:
                tenant_contact += f" | {tenant_phone}"
            metadata.append(EmailMetadataRow(label="Tenant", value=tenant_contact, emoji="👤"))
        
        # Issue details section
        metadata.append(EmailMetadataRow(label="Issue", value=issue_title, emoji="🔧"))
        metadata.append(
            EmailMetadataRow(
                label="Priority", 
                value=BrikliEmailTemplate.get_priority_badge_html(priority.value)
            )
        )
        
        if issue_description:
            sections.append(
                EmailSection(text=f"Description: {issue_description}")
            )
        
        if estimated_cost:
            metadata.append(
                EmailMetadataRow(
                    label="Est. Cost", 
                    value=f"${estimated_cost:,.2f}", 
                    emoji="💰"
                )
            )
        
        if scheduled_date:
            metadata.append(
                EmailMetadataRow(
                    label="Scheduled", 
                    value=scheduled_date.strftime("%B %d, %Y"), 
                    emoji="📅"
                )
            )
        
        # Landlord contact
        landlord_contact = landlord_name
        if landlord_phone:
            landlord_contact += f" | {landlord_phone}"
        landlord_contact += f" | {landlord_email}"
        metadata.append(EmailMetadataRow(label="Landlord", value=landlord_contact, emoji="📞"))
        
        # Photos notice
        notice = None
        if photos and len(photos) > 0:
            notice = EmailNotice(
                emoji="📷",
                title="Photos Available",
                message=f"{len(photos)} photo(s) attached to this request. View them in the full request details.",
                color="#3b82f6",  # blue
                bg_color="#eff6ff"
            )
        
        # CTA
        view_request_url = f"{frontend_url}/maintenance/{request_id}"
        cta = EmailCTA(
            text="View Full Request",
            url=view_request_url
        )
        
        # Generate email
        subject = f"New Maintenance Request - {property_address}"
        html_body = BrikliEmailTemplate.create_email(
            title="New Maintenance Assignment",
            greeting=greeting,
            sections=sections,
            metadata=metadata,
            cta=cta,
            notice=notice,
            footer_note="You're receiving this email because you've been assigned to a maintenance request."
        )
        
        return subject, html_body
    
    @staticmethod
    def create_tenant_status_update_email(
        tenant_name: str,
        tenant_email: str,
        property_address: str,
        unit_number: Optional[str],
        issue_title: str,
        old_status: MaintenanceStatus,
        new_status: MaintenanceStatus,
        vendor_name: Optional[str],
        vendor_company: Optional[str],
        vendor_phone: Optional[str],
        vendor_email: Optional[str],
        request_id: int,
        frontend_url: str
    ) -> tuple[str, str]:
        """
        Generate email for tenant status update (Uber Eats style).
        
        Returns:
            tuple: (subject, html_body)
        """
        
        # Build greeting
        greeting = f"Hi {tenant_name},"
        
        # Status progression visual
        status_progression = VendorEmailTemplates._get_status_progression_html(new_status)
        
        # Build content sections
        status_message = VendorEmailTemplates._get_status_message(new_status, vendor_company or vendor_name)
        sections = [
            EmailSection(text=f"Your maintenance request has been updated: {issue_title}"),
            EmailSection(text=status_message, is_bold=True)
        ]
        
        # Build metadata
        metadata = [
            EmailMetadataRow(label="Property", value=property_address, emoji="📍"),
        ]
        
        if unit_number:
            metadata.append(EmailMetadataRow(label="Unit", value=unit_number, emoji="🏠"))
        
        metadata.append(
            EmailMetadataRow(
                label="Status", 
                value=f"{old_status.value.replace('_', ' ').title()} → {new_status.value.replace('_', ' ').title()}"
            )
        )
        
        # Vendor contact (if assigned and in progress/completed)
        notice = None
        if (vendor_name or vendor_company) and new_status in [MaintenanceStatus.IN_PROGRESS, MaintenanceStatus.COMPLETED]:
            vendor_display = vendor_company or vendor_name
            vendor_details = []
            if vendor_phone:
                vendor_details.append(f"📞 {vendor_phone}")
            if vendor_email:
                vendor_details.append(f"📧 {vendor_email}")
            
            vendor_info_text = f"Vendor: {vendor_display}"
            if vendor_details:
                vendor_info_text += "\n" + " | ".join(vendor_details)
            
            notice = EmailNotice(
                emoji="🔧",
                title="Vendor Contact",
                message=vendor_info_text,
                color="#10b981",  # green
                bg_color="#ecfdf5"
            )
        
        # CTA
        view_request_url = f"{frontend_url}/maintenance/{request_id}"
        cta = EmailCTA(
            text="View Request Details",
            url=view_request_url
        )
        
        # Add status progression HTML (custom section)
        custom_html_section = f"""
      <div style="background-color: #f9fafb; border-radius: 10px; padding: 20px; margin: 24px 0;">
        <h3 style="font-size: 14px; font-weight: 600; color: #111827; margin: 0 0 16px 0; text-transform: uppercase;">Progress</h3>
        {status_progression}
      </div>
"""
        
        # Generate email with custom section
        subject = f"Maintenance Update - {issue_title}"
        base_html = BrikliEmailTemplate.create_email(
            title="Maintenance Request Update",
            greeting=greeting,
            sections=sections,
            metadata=metadata,
            cta=cta,
            notice=notice,
            footer_note="You're receiving this email because you opted in to maintenance request notifications."
        )
        
        # Insert custom section before CTA
        html_body = base_html.replace(
            '<div class="cta">',
            custom_html_section + '\n      <div class="cta">'
        )
        
        return subject, html_body
    
    @staticmethod
    def _get_status_progression_html(current_status: MaintenanceStatus) -> str:
        """Generate visual status progression (Uber Eats style)"""
        
        statuses = [
            ("Submitted", MaintenanceStatus.PENDING),
            ("Assigned", MaintenanceStatus.PENDING),  # No separate status, inferred
            ("In Progress", MaintenanceStatus.IN_PROGRESS),
            ("Completed", MaintenanceStatus.COMPLETED)
        ]
        
        html = '<div style="display: flex; flex-direction: column; gap: 12px;">'
        
        for i, (label, status) in enumerate(statuses):
            # Determine if this step is complete, current, or upcoming
            is_completed = False
            is_current = False
            
            if current_status == MaintenanceStatus.COMPLETED:
                is_completed = True
            elif current_status == MaintenanceStatus.IN_PROGRESS:
                if i < 3:
                    is_completed = True
                elif i == 2:
                    is_current = True
            elif current_status == MaintenanceStatus.PENDING:
                if i == 0:
                    is_current = True
            
            # Icon
            if is_completed:
                icon = "✓"
                icon_color = "#10b981"  # green
            elif is_current:
                icon = "→"
                icon_color = "#3b82f6"  # blue
            else:
                icon = "○"
                icon_color = "#9ca3af"  # gray
            
            # Text color
            text_color = "#111827" if (is_completed or is_current) else "#9ca3af"
            font_weight = "600" if is_current else "400"
            
            html += f'''
          <div style="display: flex; align-items: center; gap: 12px;">
            <span style="width: 24px; height: 24px; border-radius: 50%; background-color: {icon_color}; color: white; display: inline-flex; align-items: center; justify-content: center; font-size: 14px; font-weight: bold;">{icon}</span>
            <span style="font-size: 14px; color: {text_color}; font-weight: {font_weight};">{label}</span>
            {' <span style="font-size: 12px; color: #3b82f6; font-weight: 600;">← YOU ARE HERE</span>' if is_current else ''}
          </div>'''
        
        html += '</div>'
        return html
    
    @staticmethod
    def _get_status_message(status: MaintenanceStatus, vendor_name: Optional[str]) -> str:
        """Get friendly status message for tenant"""
        
        messages = {
            MaintenanceStatus.PENDING: "Your request has been submitted and is awaiting assignment.",
            MaintenanceStatus.IN_PROGRESS: f"Work has begun{' by ' + vendor_name if vendor_name else ''}. We'll notify you when it's complete.",
            MaintenanceStatus.COMPLETED: "The work has been completed! Please verify everything is resolved.",
            MaintenanceStatus.CANCELLED: "This maintenance request has been cancelled."
        }
        
        return messages.get(status, "Your maintenance request status has been updated.")
    
    @staticmethod
    def create_landlord_confirmation_email(
        landlord_name: str,
        vendor_name: str,
        vendor_company: Optional[str],
        property_address: str,
        unit_number: Optional[str],
        issue_title: str,
        request_id: int,
        frontend_url: str
    ) -> tuple[str, str]:
        """
        Generate confirmation email for landlord after assigning vendor.
        
        Returns:
            tuple: (subject, html_body)
        """
        
        greeting = f"Hi {landlord_name},"
        vendor_display = vendor_company or vendor_name
        
        sections = [
            EmailSection(
                text=f"You've successfully assigned {vendor_display} to your maintenance request."
            ),
            EmailSection(
                text="The vendor has been notified and will receive all the request details."
            )
        ]
        
        metadata = [
            EmailMetadataRow(label="Property", value=property_address, emoji="📍"),
            EmailMetadataRow(label="Vendor", value=vendor_display, emoji="🔧"),
            EmailMetadataRow(label="Issue", value=issue_title, emoji="📋")
        ]
        
        if unit_number:
            metadata.insert(1, EmailMetadataRow(label="Unit", value=unit_number, emoji="🏠"))
        
        view_request_url = f"{frontend_url}/maintenance/{request_id}"
        cta = EmailCTA(
            text="View Request",
            url=view_request_url
        )
        
        notice = EmailNotice(
            emoji="✅",
            title="What's Next?",
            message="The vendor will contact you or the tenant directly to schedule the work. You'll receive updates as the status changes.",
            color="#10b981",
            bg_color="#ecfdf5"
        )
        
        subject = f"Vendor Assigned - {property_address}"
        html_body = BrikliEmailTemplate.create_email(
            title="Vendor Successfully Assigned",
            greeting=greeting,
            sections=sections,
            metadata=metadata,
            cta=cta,
            notice=notice
        )
        
        return subject, html_body

