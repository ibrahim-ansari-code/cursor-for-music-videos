import logging
import json
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from pydantic import BaseModel
import fitz  # PyMuPDF
from sqlalchemy.orm import selectinload
import re # Added import for regex

from Backend.database import get_session
from Backend.models.lease import Lease, LeaseStatus, LeaseDocument
from Backend.models.user import User
from Backend.api.auth import get_current_user
from Backend.utils.llm_utils import analyze_lease_text
from Backend.models.enums import UserType
from Backend.models.property import Property, PropertyUnit
from Backend.models.tenant import Tenant

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/leases",
    tags=["leases"],
)

# API models
class LeaseBase(BaseModel):
    start_date: date
    end_date: date
    monthly_rent: float
    security_deposit: float
    is_renewable: bool = True
    auto_renew: bool = False
    rent_due_day: int = 1
    late_fee_amount: Optional[float] = None
    late_fee_after_days: Optional[int] = None
    special_terms: Optional[str] = None
    property_id: int
    unit_id: Optional[int] = None
    tenant_id: int

class LeaseCreate(LeaseBase):
    status: Optional[LeaseStatus] = LeaseStatus.DRAFT

class LeaseUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    monthly_rent: Optional[float] = None
    security_deposit: Optional[float] = None
    status: Optional[LeaseStatus] = None
    is_renewable: Optional[bool] = None
    auto_renew: Optional[bool] = None
    rent_due_day: Optional[int] = None
    late_fee_amount: Optional[float] = None
    late_fee_after_days: Optional[int] = None
    special_terms: Optional[str] = None

class LeaseResponse(LeaseBase):
    id: int
    status: LeaseStatus
    created_at: datetime
    updated_at: datetime
    tenant: Optional[Tenant] = None
    property: Optional[Property] = None
    
    class Config:
        from_attributes = True

class LeaseDocumentResponse(BaseModel):
    id: int
    name: str
    file_path: str
    document_type: str
    upload_date: datetime
    
    class Config:
        from_attributes = True

class LeaseAnalysisResponse(BaseModel):
    monthly_rent: float
    start_date: date
    end_date: date
    security_deposit: float
    tenant_name: str
    unit: Optional[str] = None

# API endpoints
@router.post("/", response_model=LeaseResponse, status_code=status.HTTP_201_CREATED)
async def create_lease(
    lease_data: LeaseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new lease"""
    # Log detailed user information for debugging
    logger.info(f"Create lease request by user: id={current_user.id}, email={current_user.email}, type={current_user.user_type}")
    
    # Case-insensitive comparison of user types
    user_type = current_user.user_type.upper() if current_user.user_type else None
    logger.info(f"Normalized user type: {user_type}")
    
    # Define scope based on user type
    scope = None
    if user_type == "ADMIN":
        scope = "global"
    elif user_type == "LANDLORD":
        scope = "own_properties"
    else:
        logger.warning(f"Unauthorized lease creation attempt by user {current_user.id} with type {user_type}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create leases"
        )

    # If user is a landlord, verify they own the property
    if scope == "own_properties":
        from sqlalchemy import text
        property_ownership_query = text("""
            SELECT id FROM properties 
            WHERE id = :property_id AND owner_id = :owner_id
        """)
        result = await session.execute(
            property_ownership_query, 
            {"property_id": lease_data.property_id, "owner_id": current_user.id}
        )
        property_record = result.first()
        
        if not property_record:
            logger.warning(f"Landlord {current_user.id} attempted to create lease for property {lease_data.property_id} they don't own")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create leases for this property"
            )
    
    # Validate tenant using raw SQL
    from sqlalchemy import text
    tenant_query = text("SELECT id FROM tenants WHERE id = :tenant_id")
    tenant_result = await session.execute(tenant_query, {"tenant_id": lease_data.tenant_id})
    tenant_record = tenant_result.first()

    if not tenant_record:
        logger.error(f"Tenant not found with ID: {lease_data.tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID"
        )

    # Validate property using raw SQL
    property_query = text("SELECT id FROM properties WHERE id = :property_id")
    property_result = await session.execute(property_query, {"property_id": lease_data.property_id})
    property_record = property_result.first()
    if not property_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid property ID"
        )

    # Validate unit if provided
    if lease_data.unit_id:
        unit_query = text("""
            SELECT id FROM property_units 
            WHERE id = :unit_id AND property_id = :property_id
        """)
        unit_result = await session.execute(
            unit_query, 
            {"unit_id": lease_data.unit_id, "property_id": lease_data.property_id}
        )
        unit_record = unit_result.first()
        if not unit_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid unit ID"
            )

    # Create lease using raw SQL
    now = datetime.utcnow()
    insert_query = text("""
        INSERT INTO leases (
            start_date, end_date, monthly_rent, security_deposit, status, 
            is_renewable, auto_renew, rent_due_day, late_fee_amount, late_fee_after_days, 
            special_terms, property_id, unit_id, tenant_id, created_at, updated_at
        ) VALUES (
            :start_date, :end_date, :monthly_rent, :security_deposit, :status,
            :is_renewable, :auto_renew, :rent_due_day, :late_fee_amount, :late_fee_after_days,
            :special_terms, :property_id, :unit_id, :tenant_id, :created_at, :updated_at
        )
        RETURNING id
    """)
    
    try:
        params = {
            "start_date": lease_data.start_date,
            "end_date": lease_data.end_date,
            "monthly_rent": lease_data.monthly_rent,
            "security_deposit": lease_data.security_deposit,
            "status": getattr(lease_data, "status", LeaseStatus.DRAFT.value),
            "is_renewable": lease_data.is_renewable,
            "auto_renew": lease_data.auto_renew,
            "rent_due_day": lease_data.rent_due_day,
            "late_fee_amount": lease_data.late_fee_amount,
            "late_fee_after_days": lease_data.late_fee_after_days,
            "special_terms": lease_data.special_terms,
            "property_id": lease_data.property_id,
            "unit_id": lease_data.unit_id,
            "tenant_id": lease_data.tenant_id,
            "created_at": now,
            "updated_at": now
        }
        
        result = await session.execute(insert_query, params)
        lease_id = result.scalar_one()
        await session.commit()
        
        # Fetch the created lease data
        lease_query = text("""
            SELECT 
                l.id, l.start_date, l.end_date, l.monthly_rent, l.security_deposit, 
                l.status, l.is_renewable, l.auto_renew, l.rent_due_day, 
                l.late_fee_amount, l.late_fee_after_days, l.special_terms,
                l.property_id, l.unit_id, l.tenant_id, l.created_at, l.updated_at
            FROM leases l
            WHERE l.id = :lease_id
        """)
        
        lease_result = await session.execute(lease_query, {"lease_id": lease_id})
        lease_data = lease_result.first()
        
        # Convert the result to a dict for the response
        response_data = {
            "id": lease_data.id,
            "start_date": lease_data.start_date,
            "end_date": lease_data.end_date, 
            "monthly_rent": lease_data.monthly_rent,
            "security_deposit": lease_data.security_deposit,
            "status": lease_data.status,
            "is_renewable": lease_data.is_renewable,
            "auto_renew": lease_data.auto_renew,
            "rent_due_day": lease_data.rent_due_day,
            "late_fee_amount": lease_data.late_fee_amount,
            "late_fee_after_days": lease_data.late_fee_after_days,
            "special_terms": lease_data.special_terms,
            "property_id": lease_data.property_id,
            "unit_id": lease_data.unit_id,
            "tenant_id": lease_data.tenant_id,
            "created_at": lease_data.created_at,
            "updated_at": lease_data.updated_at,
            # These would be populated by SQLAlchemy relationships
            # Since we're using raw SQL, we need to provide empty placeholders
            "tenant": None,
            "property": None
        }
        
        # If lease is created with status ACTIVE, update tenant's current_property_id
        if lease_data.status == "ACTIVE":
            try:
                logger.info(f"Updating tenant's current property: tenant ID={lease_data.tenant_id}, property ID={lease_data.property_id}")
                
                # Update tenant's current_property_id
                update_tenant_query = text("""
                    UPDATE tenants 
                    SET current_property_id = :property_id, updated_at = :now
                    WHERE id = :tenant_id
                """)
                
                await session.execute(
                    update_tenant_query, 
                    {"tenant_id": lease_data.tenant_id, "property_id": lease_data.property_id, "now": now}
                )
                await session.commit()
                
                logger.info(f"Tenant's current property updated successfully")
            except Exception as tenant_update_error:
                logger.error(f"Error updating tenant's current property: {str(tenant_update_error)}", exc_info=True)
                # Don't fail the whole operation if this part fails, just log the error
        
        logger.info(f"Lease created: {lease_id} with status {lease_data.status} by user {current_user.id}")
        return response_data
        
    except Exception as db_error:
        await session.rollback()
        logger.error(f"Database error during lease creation: {str(db_error)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(db_error)}"
        )

@router.get("/", response_model=List[LeaseResponse])
async def get_leases(
    status: Optional[LeaseStatus] = None,
    property_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all leases with optional filtering"""
    # Eagerly load tenant, property, and unit relationships
    query = select(Lease).options(
        selectinload(Lease.tenant),
        selectinload(Lease.property),
        selectinload(Lease.unit)
    )
    
    # Apply filters
    conditions = []
    if status:
        conditions.append(Lease.status == status)
    if property_id:
        conditions.append(Lease.property_id == property_id)
    if tenant_id:
        conditions.append(Lease.tenant_id == tenant_id)
    
    # Add conditions to query if any exist
    if conditions:
        query = query.where(and_(*conditions))
    
    # Add access control based on user type
    if current_user.user_type == UserType.TENANT:
        # Tenants can only see their own leases
        query = query.where(Lease.tenant_id == current_user.id)
    elif current_user.user_type == UserType.LANDLORD:
        # Landlords can see leases for their properties
        query = query.join(Property).where(Property.owner_id == current_user.id)
    
    result = await session.execute(query)
    leases = result.scalars().unique().all()
    return leases

@router.get("/{lease_id}", response_model=LeaseResponse)
async def get_lease(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific lease by ID"""
    query = select(Lease).where(Lease.id == lease_id)
    result = await session.execute(query)
    lease = result.scalar_one_or_none()
    
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with ID {lease_id} not found"
        )
    
    # Check access permissions
    if current_user.user_type == UserType.TENANT and lease.tenant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this lease"
        )
    
    return lease

@router.put("/{lease_id}", response_model=LeaseResponse)
async def update_lease(
    lease_id: int,
    lease_data: LeaseUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update a lease"""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update leases"
        )
    
    query = select(Lease).where(Lease.id == lease_id)
    result = await session.execute(query)
    lease = result.scalar_one_or_none()
    
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with ID {lease_id} not found"
        )
    
    # Update lease fields
    lease_data_dict = lease_data.dict(exclude_unset=True)
    for key, value in lease_data_dict.items():
        setattr(lease, key, value)
    
    # Update the updated_at timestamp
    lease.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(lease)
    
    logger.info(f"Lease updated: {lease.id} by user {current_user.id}")
    return lease

@router.post("/{lease_id}/validate", response_model=LeaseResponse)
async def validate_lease(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Validate a lease, moving it from DRAFT to PENDING status"""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to validate leases"
        )
    
    query = select(Lease).where(Lease.id == lease_id)
    result = await session.execute(query)
    lease = result.scalar_one_or_none()
    
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with ID {lease_id} not found"
        )
    
    if lease.status != LeaseStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lease is not in DRAFT status (current status: {lease.status})"
        )
    
    # Update lease status to PENDING
    lease.status = LeaseStatus.PENDING
    lease.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(lease)
    
    logger.info(f"Lease validated: {lease.id} by user {current_user.id}")
    return lease

@router.post("/{lease_id}/status", response_model=LeaseResponse)
async def update_lease_status(
    lease_id: int,
    status_data: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update the status of a lease (activate, terminate, etc.)"""
    # Log detailed information about the request
    logger.info(f"Lease status update request: lease ID={lease_id}, user ID={current_user.id}, email={current_user.email}, user_type={current_user.user_type}")
    logger.info(f"Request data: {status_data}")
    
    try:
        # Case-insensitive comparison of user types
        user_type = current_user.user_type.upper() if current_user.user_type else None
        logger.info(f"Normalized user type: {user_type}")
        
        if user_type not in ["ADMIN", "LANDLORD"]:
            logger.warning(f"Unauthorized lease status update attempt by user {current_user.id} with type {user_type}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update lease status"
            )
    
        # Get status from request body
        new_status = status_data.get("status")
        if not new_status:
            logger.error("Status field missing from request body")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Status is required in request body"
            )
        
        # Validate status value
        valid_statuses = [s.value for s in LeaseStatus]
        if new_status not in valid_statuses:
            logger.error(f"Invalid status value received: {new_status}. Valid values are: {valid_statuses}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status. Valid values are: {', '.join(valid_statuses)}"
            )
        
        # First, check if the lease exists
        from sqlalchemy import text
        check_query = text("SELECT id, status FROM leases WHERE id = :lease_id")
        result = await session.execute(check_query, {"lease_id": lease_id})
        lease_record = result.first()
        
        if not lease_record:
            logger.warning(f"Lease not found with ID: {lease_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lease with ID {lease_id} not found"
            )
    
        old_status = lease_record.status
        now = datetime.utcnow()
        
        # Update the lease status using raw SQL
        update_query = text("""
            UPDATE leases 
            SET status = :new_status, updated_at = :now
            WHERE id = :lease_id
            RETURNING id
        """)
        
        try:
            result = await session.execute(
                update_query, 
                {"lease_id": lease_id, "new_status": new_status, "now": now}
            )
            await session.commit()
            
            # Get the updated lease data
            query = text("""
                SELECT 
                    l.id, l.start_date, l.end_date, l.monthly_rent, l.security_deposit, 
                    l.status, l.is_renewable, l.auto_renew, l.rent_due_day, 
                    l.late_fee_amount, l.late_fee_after_days, l.special_terms,
                    l.property_id, l.unit_id, l.tenant_id, l.created_at, l.updated_at
                FROM leases l
                WHERE l.id = :lease_id
            """)
            
            result = await session.execute(query, {"lease_id": lease_id})
            lease_data = result.first()
            
            if not lease_data:
                logger.error(f"Failed to retrieve lease after status update")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve lease data after update"
                )
            
            # Convert the result to a dict for the response
            response_data = {
                "id": lease_data.id,
                "start_date": lease_data.start_date,
                "end_date": lease_data.end_date, 
                "monthly_rent": lease_data.monthly_rent,
                "security_deposit": lease_data.security_deposit,
                "status": lease_data.status,
                "is_renewable": lease_data.is_renewable,
                "auto_renew": lease_data.auto_renew,
                "rent_due_day": lease_data.rent_due_day,
                "late_fee_amount": lease_data.late_fee_amount,
                "late_fee_after_days": lease_data.late_fee_after_days,
                "special_terms": lease_data.special_terms,
                "property_id": lease_data.property_id,
                "unit_id": lease_data.unit_id,
                "tenant_id": lease_data.tenant_id,
                "created_at": lease_data.created_at,
                "updated_at": lease_data.updated_at,
                # These would be populated by SQLAlchemy relationships
                # Since we're using raw SQL, we need to provide empty placeholders
                "tenant": None,
                "property": None
            }
            
            # If lease is activated, update tenant's current_property_id
            if new_status == "ACTIVE":
                try:
                    logger.info(f"Updating tenant's current property: tenant ID={lease_data.tenant_id}, property ID={lease_data.property_id}")
                    
                    # Update tenant's current_property_id
                    update_tenant_query = text("""
                        UPDATE tenants 
                        SET current_property_id = :property_id, updated_at = :now
                        WHERE id = :tenant_id
                    """)
                    
                    await session.execute(
                        update_tenant_query, 
                        {"tenant_id": lease_data.tenant_id, "property_id": lease_data.property_id, "now": now}
                    )
                    await session.commit()
                    
                    logger.info(f"Tenant's current property updated successfully")
                except Exception as tenant_update_error:
                    logger.error(f"Error updating tenant's current property: {str(tenant_update_error)}", exc_info=True)
                    # Don't fail the whole operation if this part fails, just log the error
            
            logger.info(f"Lease status updated successfully: ID {lease_id} status changed from {old_status} to {new_status} by user {current_user.id}")
            return response_data
            
        except Exception as db_error:
            await session.rollback()
            logger.error(f"Database error during lease status update: {str(db_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(db_error)}"
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error updating lease status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lease status: {str(e)}"
        )

@router.post("/{lease_id}/upload", response_model=LeaseDocumentResponse)
async def upload_lease_document(
    lease_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Upload a document associated with a lease"""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload lease documents"
        )
    
    # Check if lease exists
    query = select(Lease).where(Lease.id == lease_id)
    result = await session.execute(query)
    lease = result.scalar_one_or_none()
    
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with ID {lease_id} not found"
        )
    
    # In a real application, we would save the file to a storage system
    # For this example, we'll just pretend we saved it and return the path
    file_path = f"/uploads/leases/{lease_id}/{file.filename}"
    
    # Create document record
    document = LeaseDocument(
        name=file.filename,
        file_path=file_path,
        document_type=document_type,
        lease_id=lease_id,
        uploaded_by_id=current_user.id
    )
    
    session.add(document)
    await session.commit()
    await session.refresh(document)
    
    logger.info(f"Lease document uploaded: {document.id} for lease {lease_id} by user {current_user.id}")
    return document

@router.get("/{lease_id}/documents", response_model=List[LeaseDocumentResponse])
async def get_lease_documents(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all documents associated with a lease"""
    # Check if lease exists
    query = select(Lease).where(Lease.id == lease_id)
    result = await session.execute(query)
    lease = result.scalar_one_or_none()
    
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with ID {lease_id} not found"
        )
    
    # Check access permissions
    if current_user.user_type == UserType.TENANT and lease.tenant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this lease document"
        )
    
    # Get documents
    query = select(LeaseDocument).where(LeaseDocument.lease_id == lease_id)
    result = await session.execute(query)
    documents = result.scalars().all()
    
    return documents

@router.post("/analyze", response_model=LeaseAnalysisResponse)
async def analyze_lease(
    file: UploadFile = File(...),
    property_id: int = Form(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze a lease document and extract key information.
    """
    try:
        logger.info(f"Starting lease analysis for property_id: {property_id}")
        
        # Read file content
        content = await file.read()
        text_content = content.decode('utf-8')
        
        # Log the first 100 characters of content for debugging
        logger.debug(f"File content preview: {text_content[:100]}...")
        
        # Analyze the lease text
        analysis_result = analyze_lease_text(text_content)
        logger.info("Lease analysis completed successfully")
        logger.debug(f"Analysis result: {analysis_result}")
        
        # Extract required fields from the nested structure
        response_data = {
            "monthly_rent": float(analysis_result['rent_payment']['monthly_rent']),
            "start_date": analysis_result['term_details']['lease_start_date'],
            "end_date": analysis_result['term_details']['lease_end_date'],
            "security_deposit": float(analysis_result['deposits']['security_deposit']),
            "tenant_name": analysis_result['core_identifiers']['tenant_name'],
            "unit": analysis_result['core_identifiers'].get('unit_number', '')
        }
        
        logger.info(f"Formatted response data: {response_data}")
        return response_data
        
    except ValueError as e:
        logger.error(f"Validation error in lease analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error analyzing lease: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze lease: {str(e)}"
        )

@router.post("/parse", response_model=LeaseAnalysisResponse)
async def parse_lease(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Parse a lease PDF and extract key fields using LLM analysis.
    """
    # Log user info for debugging
    logger.info(f"Parse lease request from user ID: {current_user.id}, email: {current_user.email}, type: {current_user.user_type}")
    
    # Check if user is authorized based on their type
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    
    if user_type not in [UserType.ADMIN.value, UserType.LANDLORD.value, 'ADMIN', 'LANDLORD']:
        logger.warning(f"Authorization failed: User {current_user.id} with type {user_type} attempted to parse lease")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to parse leases"
        )
    
    logger.info(f"User {current_user.id} authorized to parse lease")
    
    try:
        # Read PDF content
        content = await file.read()
        pdf_document = fitz.open(stream=content, filetype="pdf")
        
        # Extract text from all pages
        text = ""
        for page in pdf_document:
            text += page.get_text()
        
        # Close the PDF document
        pdf_document.close()
        
        # Analyze text using LLM
        logger.info(f"Sending lease text for analysis (first 100 chars): {text[:100]!r}")
        logger.info(f"Total characters sent to LLM: {len(text)}")

        raw_parsed_data = analyze_lease_text(text)

        # Log the full raw data
        logger.info(f"Raw LLM parsed data:\n{json.dumps(raw_parsed_data, indent=2)}")
        
        # Restructure the data to match LeaseAnalysisResponse model
        parsed_data = {}
        try:
            # Safely parse monthly_rent
            raw_monthly_rent = raw_parsed_data.get('rent_payment', {}).get('monthly_rent', '0')
            logger.info(f"Attempting to parse monthly_rent from raw string: {raw_monthly_rent!r}")
            
            monthly_rent_value = 0.0
            try:
                # Attempt direct float conversion first
                monthly_rent_value = float(raw_monthly_rent)
            except ValueError:
                # If direct conversion fails, try regex to find the first number
                logger.warning(f"Direct float conversion failed for monthly_rent. Attempting regex extraction.")
                # Regex to find the first floating point number (potentially with commas)
                match = re.match(r"^\s*([\d,]+(?:\.\d+)?|\d+(?:\.\d+)?)", str(raw_monthly_rent).strip())
                if match:
                    number_str = match.group(1).replace(",", "") # Remove commas before conversion
                    try:
                        monthly_rent_value = float(number_str)
                        logger.info(f"Successfully extracted monthly_rent using regex: {monthly_rent_value}")
                    except ValueError:
                        logger.error(f"Could not convert regex match '{number_str}' to float.")
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Could not extract a valid rent amount from: '{raw_monthly_rent}'"
                        )
                else:
                    logger.error(f"Could not find a valid number pattern in monthly_rent string: '{raw_monthly_rent}'")
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Could not parse monthly rent value: '{raw_monthly_rent}'"
                    )
            
            parsed_data['monthly_rent'] = monthly_rent_value
            parsed_data['start_date'] = raw_parsed_data.get('term_details', {}).get('lease_start_date', '')
            parsed_data['end_date'] = raw_parsed_data.get('term_details', {}).get('lease_end_date', '')
            
            # Safely parse security_deposit
            raw_security_deposit = raw_parsed_data.get('deposits', {}).get('security_deposit', '0')
            logger.info(f"Attempting to parse security_deposit from raw string: {raw_security_deposit!r}")
            security_deposit_value = 0.0
            try:
                security_deposit_value = float(raw_security_deposit)
            except ValueError:
                logger.warning(f"Direct float conversion failed for security_deposit. Attempting regex extraction.")
                # Use the same improved regex
                match = re.match(r"^\s*([\d,]+(?:\.\d+)?|\d+(?:\.\d+)?)", str(raw_security_deposit).strip())
                if match:
                    number_str = match.group(1).replace(",", "") # Remove commas before conversion
                    try:
                        security_deposit_value = float(number_str)
                        logger.info(f"Successfully extracted security_deposit using regex: {security_deposit_value}")
                    except ValueError:
                        logger.error(f"Could not convert security_deposit regex match '{number_str}' to float.")
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Could not extract a valid security deposit amount from: '{raw_security_deposit}'"
                        )
                else:
                    logger.error(f"Could not find a valid number pattern in security_deposit string: '{raw_security_deposit}'")
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Could not parse security deposit value: '{raw_security_deposit}'"
                    )
            parsed_data['security_deposit'] = security_deposit_value
            
            parsed_data['tenant_name'] = raw_parsed_data.get('core_identifiers', {}).get('tenant_name', '')
            parsed_data['unit'] = raw_parsed_data.get('core_identifiers', {}).get('unit_number', '')
        
        except KeyError as e:
            logger.error(f"Missing key in LLM response: {e}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Missing expected field in parsed lease data: {e}")
        except ValueError as e:
            logger.error(f"Value conversion error during parsing: {e}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid data format in parsed lease: {e}")
            
        logger.info(f"Restructured data: {parsed_data}")
        
        # Convert string dates to date objects
        try:
            if parsed_data['start_date']:
                parsed_data['start_date'] = datetime.strptime(parsed_data['start_date'], '%Y-%m-%d').date()
            if parsed_data['end_date']:
                parsed_data['end_date'] = datetime.strptime(parsed_data['end_date'], '%Y-%m-%d').date()
        except ValueError as e:
            logger.error(f"Date parsing error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date format in lease: {str(e)}"
            )
        
        logger.info(f"Lease parsed successfully by user {current_user.id}")
        return parsed_data
        
    except Exception as e:
        # Log the detailed error including stack trace
        logger.error(f"Failed to parse lease document: {str(e)}", exc_info=True) 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # Provide a more specific error message if possible, otherwise keep generic
            detail=f"Failed to parse lease document: {str(e)}" 
        )
