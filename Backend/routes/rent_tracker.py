from flask import Blueprint, request, jsonify
from models.lease import Lease  
from models.payment import Payment
from models.property import Property
from models.tenant import Tenant
from models.user import User
from middleware.auth_middleware import token_required
from datetime import datetime
import calendar
from bson import ObjectId
import logging

rent_tracker_bp = Blueprint('rent_tracker', __name__)

@rent_tracker_bp.route('/api/rent-tracker', methods=['GET'])
@token_required
def get_rent_tracker(current_user):
    try:
        # Get the month and year from query params or default to current month/year
        month = request.args.get('month', datetime.now().month, type=int)
        year = request.args.get('year', datetime.now().year, type=int)
        
        # Validate month and year
        if not 1 <= month <= 12:
            return jsonify({"error": "Invalid month. Month must be between 1 and 12"}), 400
        if not 1900 <= year <= 2100:
            return jsonify({"error": "Invalid year. Year must be between 1900 and 2100"}), 400
            
        # Get all active leases for the user's organization
        active_leases = Lease.find_active_leases_by_org(current_user["organizationId"])
        
        # Get the first and last day of the selected month
        _, last_day = calendar.monthrange(year, month)
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, last_day, 23, 59, 59)
        
        rent_tracker_data = []
        
        for lease in active_leases:
            # Get property and tenant details
            property_doc = Property.find_by_id(lease["propertyId"])
            if not property_doc:
                continue
                
            tenant_docs = []
            for tenant_id in lease.get("tenantIds", []):
                tenant = Tenant.find_by_id(tenant_id)
                if tenant:
                    tenant_docs.append(tenant)
            
            # Get payments for this lease in the selected month
            payments = Payment.find_by_lease_in_period(lease["_id"], start_date, end_date)
            
            # Calculate total rent paid for this month
            total_paid = sum(payment.get("amount", 0) for payment in payments)
            
            # Determine status
            status = "unpaid"
            if total_paid >= lease.get("rentAmount", 0):
                status = "paid"
            elif total_paid > 0:
                status = "partial"
                
            tenant_names = []
            tenant_emails = []
            for tenant in tenant_docs:
                if tenant.get("firstName") and tenant.get("lastName"):
                    tenant_names.append(f"{tenant['firstName']} {tenant['lastName']}")
                if tenant.get("email"):
                    tenant_emails.append(tenant["email"])
            
            rent_tracker_data.append({
                "leaseId": str(lease["_id"]),
                "propertyId": str(lease["propertyId"]),
                "propertyName": property_doc.get("name", "Unnamed Property"),
                "propertyAddress": property_doc.get("address", "No Address"),
                "tenantIds": [str(tid) for tid in lease.get("tenantIds", [])],
                "tenantNames": tenant_names,
                "tenantEmails": tenant_emails,
                "rentAmount": lease.get("rentAmount", 0),
                "amountPaid": total_paid,
                "dueDate": lease.get("paymentDueDay", 1),
                "status": status,
                "payments": [{
                    "id": str(payment["_id"]), 
                    "date": payment.get("date"),
                    "amount": payment.get("amount", 0)
                } for payment in payments]
            })
        
        return jsonify({
            "month": month,
            "year": year,
            "rentTracker": rent_tracker_data
        }), 200
    
    except Exception as e:
        logging.error(f"Error in rent tracker: {str(e)}")
        return jsonify({"error": str(e)}), 500 