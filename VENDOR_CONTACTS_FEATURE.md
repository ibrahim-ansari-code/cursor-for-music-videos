# Vendor Address Book & Automated Notifications for Maintenance Requests

## Jira Ticket

### Title

Vendor Address Book & Automated Notifications for Maintenance Requests

### Description

Introduce a Landlord Contact/Address Book where landlords can store vendor details (company/tradesmen) including name, trade category, phone number, and email.

When submitting a new Maintenance Request, landlords can assign the job to a specific vendor from their contact list. Upon assignment:

- The vendor receives an email + SMS notification with request details.
- The landlord sees the assigned vendor in the request record.

***Optional toggle: Notify Tenant**

If enabled, the tenant receives email + SMS notifications when:

- Request is submitted
- Vendor accepts the job
- Work begins
- Job is completed

This flow mirrors the Uber Eats-style status notifications (submitted → accepted → in progress → completed).

### Acceptance Criteria

1. Landlord can add, edit, delete vendors in a dedicated "Vendor Contacts" section.
2. Each vendor record stores: name, trade type, phone, email.
3. Maintenance Request form allows assigning a vendor from saved contacts.
4. On submission, vendor receives email + SMS with full request details.
5. Landlord can toggle "Notify Tenant" per request.
6. If enabled, tenants receive status notifications (email + SMS) as the request progresses.
7. Statuses must be trackable: Submitted, Assigned, In Progress, Completed.

### Technical Notes

- Extend DB schema to include vendor_contacts (linked to landlord/org).
- Integrate with email + SMS providers (Twilio, SendGrid, etc.).
- Add notification templates for both vendor and tenant messages.
- Add request status transitions to trigger notifications.

---

## Implementation Investigation

### Current System Analysis

#### Existing Components to Review

1. **Maintenance System**
   - Current maintenance request flow
   - Existing status management
   - Database models and schemas

2. **Notification System**
   - Current email/SMS infrastructure
   - Notification templates
   - Delivery mechanisms

3. **User Management**
   - How landlords/organizations are structured
   - Tenant relationships

4. **Frontend Components**
   - Maintenance UI components
   - Form patterns
   - Modal patterns

### Implementation Plan

(To be filled after investigation)
