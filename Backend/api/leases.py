import logging
import json
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, text # Imported text
from pydantic import BaseModel
import fitz  # PyMuPDF
from sqlalchemy.orm import selectinload
import re # Added import for regex

from Backend.database import get_session
from Backend.models.lease import Lease, LeaseStatus, LeaseDocument
from Backend.models.user import User
from Backend.api.auth import get_current_user
from Backend.utils.llm_utils import analyze_lease_text
from Backend.utils.azure_blob import upload_lease_to_blob
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

# --- Helper Function for Permission Checks ---
async def check_lease_permission(
    lease_id: int,
    session: AsyncSession,
    current_user: User,
    action: str = "view"
) -> Lease:
    """Check if the current user has permission to access/modify the lease."""
    query = (
        select(Lease)
        .options(selectinload(Lease.property))
        .where(Lease.id == lease_id)
    )
    result = await session.execute(query)
    lease = result.scalar_one_or_none()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with ID {lease_id} not found"
        )

    # Admin can do anything
    if current_user.is_admin:
        return lease

    # Tenant check
    if current_user.user_type == UserType.TENANT:
        if lease.tenant_id == current_user.id and action == "view":
            return lease
        else:
            logger.warning(f"Tenant {current_user.id} permission denied for {action} lease {lease_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to {action} this lease"
            )

    # Landlord check (must own the property)
    if current_user.user_type == UserType.LANDLORD:
        if lease.property and lease.property.user_id == current_user.id:
            return lease
        else:
            logger.warning(f"Landlord {current_user.id} permission denied for {action} lease {lease_id} on property {lease.property_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to {action} this lease"
            )

    # Default deny if none of the above
    logger.error(f"Unknown user type or permission error for user {current_user.id}, action {action}, lease {lease_id}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Not authorized to {action} this lease"
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
    file_url: Optional[str] = None

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

class LeaseUploadResponse(BaseModel):
    file_url: str

# New route for uploading lease PDFs to Azure Blob Storage
@router.post("/upload-lease", response_model=LeaseUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_lease(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a lease PDF to Azure Blob Storage and return the public URL.
    This is used as part of the lease import pipeline.
    """
    try:
        logger.info(f"Uploading lease file: {file.filename} for user ID: {current_user.id}")
        
        # Check if user is authorized based on their type
        user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
        
        if user_type not in [UserType.ADMIN.value, UserType.LANDLORD.value, 'ADMIN', 'LANDLORD']:
            logger.warning(f"Authorization failed: User {current_user.id} with type {user_type} attempted to upload lease")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to upload leases"
            )
        
        # Check if file is a PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are accepted"
            )
            
        # Upload the file to Azure Blob Storage
        file_url = await upload_lease_to_blob(file, current_user.id)
        
        logger.info(f"Lease file uploaded successfully: {file_url}")
        return {"file_url": file_url}
    
    except Exception as e:
        # Log the detailed error including stack trace
        logger.error(f"Failed to upload lease document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload lease document: {str(e)}"
        )

# API endpoints
@router.post("/", response_model=LeaseResponse, status_code=status.HTTP_201_CREATED)
async def create_lease(
    lease_data: LeaseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new lease, ensuring user owns the property."""
    logger.info(f"Create lease request by user: id={current_user.id}, email={current_user.email}, type={current_user.user_type}")
    file_url = getattr(lease_data, "file_url", None)
    if file_url:
        logger.info(f"Lease creation includes document URL: {file_url}")

    # Fetch the property to check ownership
    property_query = select(Property).where(Property.id == lease_data.property_id)
    property_result = await session.execute(property_query)
    target_property = property_result.scalar_one_or_none()

    if not target_property:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid property ID"
        )

    # Check ownership (Landlord must own, Admin bypasses)
    if not current_user.is_admin and target_property.user_id != current_user.id:
        logger.warning(f"User {current_user.id} (Landlord) attempted to create lease for property {lease_data.property_id} they don't own")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create leases for this property"
        )

    # Validate tenant
    tenant_query = select(Tenant.id).where(Tenant.id == lease_data.tenant_id)
    tenant_exists = await session.scalar(tenant_query)
    if not tenant_exists:
        logger.error(f"Tenant not found with ID: {lease_data.tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID"
        )

    # Validate unit if provided
    if lease_data.unit_id:
        unit_query = select(PropertyUnit.id).where(
            and_(PropertyUnit.id == lease_data.unit_id, PropertyUnit.property_id == lease_data.property_id)
        )
        unit_exists = await session.scalar(unit_query)
        if not unit_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid unit ID or unit does not belong to the specified property"
            )

    # Create lease using ORM
    new_lease = Lease(
        **lease_data.model_dump(exclude={"file_url"}), # Exclude file_url if present
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    try:
        session.add(new_lease)
        await session.flush() # Get the lease ID

        # If file_url is provided, create a lease document record
        if file_url:
            try:
                logger.info(f"Creating lease document record for lease {new_lease.id} with URL: {file_url}")
                document = LeaseDocument(
                    name="Lease Agreement",
                    file_path=file_url,
                    document_type="contract",
                    upload_date=datetime.utcnow(),
                    lease_id=new_lease.id,
                    uploaded_by_id=current_user.id
                )
                session.add(document)
                logger.info(f"Lease document record created successfully for lease {new_lease.id}")
            except Exception as doc_error:
                logger.error(f"Error creating lease document record: {str(doc_error)}", exc_info=True)
                # Don't fail the whole lease creation if document record fails

        # If lease is created with status ACTIVE, update tenant's current_property_id
        if new_lease.status == LeaseStatus.ACTIVE:
            try:
                logger.info(f"Updating tenant's current property: tenant ID={new_lease.tenant_id}, property ID={new_lease.property_id}")
                update_tenant_query = (
                    text("UPDATE tenants SET current_property_id = :property_id, updated_at = :now WHERE id = :tenant_id")
                )
                await session.execute(
                    update_tenant_query,
                    {"tenant_id": new_lease.tenant_id, "property_id": new_lease.property_id, "now": datetime.utcnow()}
                )
                logger.info(f"Tenant's current property updated successfully")
            except Exception as tenant_update_error:
                logger.error(f"Error updating tenant's current property: {str(tenant_update_error)}", exc_info=True)

        await session.commit() # Commit lease and document (if any)
        await session.refresh(new_lease, attribute_names=['tenant', 'property']) # Refresh with relations for response

        logger.info(f"Lease created: {new_lease.id} with status {new_lease.status} by user {current_user.id}")
        return new_lease # Return the ORM object, Pydantic will handle response model

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
    """Get leases, respecting user roles and ownership."""
    query = select(Lease).options(
        selectinload(Lease.tenant),
        selectinload(Lease.property),
        selectinload(Lease.unit)
    )

    # Base filters from query params
    conditions = []
    if status:
        conditions.append(Lease.status == status)
    if property_id:
        conditions.append(Lease.property_id == property_id)
    if tenant_id:
        # Allow landlords/admins to filter by tenant_id
        if current_user.user_type != UserType.TENANT:
            conditions.append(Lease.tenant_id == tenant_id)
        else:
            # If the current user is a tenant, they can only filter for *their own* tenant_id
            if current_user.id != tenant_id:
                 logger.warning(f"Tenant {current_user.id} attempted to filter leases for tenant {tenant_id}")
                 # Return empty list if tenant tries to filter for someone else
                 return []
            conditions.append(Lease.tenant_id == current_user.id)

    # Apply access control based on user type
    if current_user.user_type == UserType.TENANT:
        # Tenants can only see their own leases (redundant if tenant_id filter applied, but safe)
        conditions.append(Lease.tenant_id == current_user.id)
    elif current_user.user_type == UserType.LANDLORD:
        # Landlords can only see leases for properties they own
        # Join with Property table and filter by user_id
        query = query.join(Lease.property).where(Property.user_id == current_user.id)
    # Admin sees all (no additional user_id filter needed)

    # Apply combined conditions
    if conditions:
        query = query.where(and_(*conditions))

    result = await session.execute(query)
    leases = result.scalars().unique().all()
    return leases

@router.get("/{lease_id}", response_model=LeaseResponse)
async def get_lease(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific lease by ID, checking permissions."""
    lease = await check_lease_permission(lease_id, session, current_user, action="view")
    return lease

@router.put("/{lease_id}", response_model=LeaseResponse)
async def update_lease(
    lease_id: int,
    lease_data: LeaseUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update a lease, checking permissions."""
    lease = await check_lease_permission(lease_id, session, current_user, action="update")

    # Update lease fields
    lease_data_dict = lease_data.model_dump(exclude_unset=True)
    original_status = lease.status
    status_changed = 'status' in lease_data_dict and lease_data_dict['status'] != original_status
    new_status = lease_data_dict.get('status')

    for key, value in lease_data_dict.items():
        setattr(lease, key, value)

    # Update the updated_at timestamp (handled by model default/onupdate? check model)
    # lease.updated_at = datetime.utcnow() # May not be needed if model handles it

    try:
        session.add(lease) # Add the modified object to the session

        # Handle tenant current_property_id update if status changed to ACTIVE
        if status_changed and new_status == LeaseStatus.ACTIVE:
            try:
                logger.info(f"Updating tenant's current property on lease activation: tenant ID={lease.tenant_id}, property ID={lease.property_id}")
                update_tenant_query = (
                    text("UPDATE tenants SET current_property_id = :property_id, updated_at = :now WHERE id = :tenant_id")
                )
                await session.execute(
                    update_tenant_query,
                    {"tenant_id": lease.tenant_id, "property_id": lease.property_id, "now": datetime.utcnow()}
                )
                logger.info(f"Tenant's current property updated successfully due to lease activation")
            except Exception as tenant_update_error:
                logger.error(f"Error updating tenant's current property on lease activation: {str(tenant_update_error)}", exc_info=True)
                # Decide if this should block the lease update or just be logged

        await session.commit()
        await session.refresh(lease)

        logger.info(f"Lease updated: {lease.id} by user {current_user.id}")
        return lease
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating lease {lease_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lease: {str(e)}"
        )

@router.post("/{lease_id}/validate", response_model=LeaseResponse)
async def validate_lease(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Validate a lease (DRAFT -> PENDING), checking permissions."""
    lease = await check_lease_permission(lease_id, session, current_user, action="validate")

    if lease.status != LeaseStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lease is not in DRAFT status (current status: {lease.status})"
        )

    # Update lease status to PENDING
    lease.status = LeaseStatus.PENDING
    # lease.updated_at = datetime.utcnow() # Handled by model?

    try:
        session.add(lease)
        await session.commit()
        await session.refresh(lease)

        logger.info(f"Lease validated: {lease.id} by user {current_user.id}")
        return lease
    except Exception as e:
        await session.rollback()
        logger.error(f"Error validating lease {lease_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate lease: {str(e)}"
        )

@router.post("/{lease_id}/status", response_model=LeaseResponse)
async def update_lease_status(
    lease_id: int,
    status_data: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update the status of a lease, checking permissions."""
    logger.info(f"Lease status update request: lease ID={lease_id}, user ID={current_user.id}, data: {status_data}")

    # Check permission first using the helper function
    lease = await check_lease_permission(lease_id, session, current_user, action="update status")

    new_status_str = status_data.get("status")
    if not new_status_str:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Status is required")

    try:
        new_status = LeaseStatus(new_status_str) # Validate and convert to Enum
    except ValueError:
        valid_statuses = [s.value for s in LeaseStatus]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{new_status_str}'. Valid values are: {', '.join(valid_statuses)}"
        )

    original_status = lease.status
    if original_status == new_status:
        logger.info(f"Lease {lease_id} status already '{new_status}'. No update needed.")
        return lease # Return current lease data if status hasn't changed

    lease.status = new_status
    # lease.updated_at = datetime.utcnow() # Handled by model?

    try:
        session.add(lease)

        # Handle tenant current_property_id update if status changed to ACTIVE
        if new_status == LeaseStatus.ACTIVE and original_status != LeaseStatus.ACTIVE:
            try:
                logger.info(f"Updating tenant's current property on lease activation: tenant ID={lease.tenant_id}, property ID={lease.property_id}")
                update_tenant_query = (
                    text("UPDATE tenants SET current_property_id = :property_id, updated_at = :now WHERE id = :tenant_id")
                )
                await session.execute(
                    update_tenant_query,
                    {"tenant_id": lease.tenant_id, "property_id": lease.property_id, "now": datetime.utcnow()}
                )
                logger.info(f"Tenant's current property updated successfully due to lease activation")
            except Exception as tenant_update_error:
                logger.error(f"Error updating tenant's current property on lease activation: {str(tenant_update_error)}", exc_info=True)
                # Decide if this should block the lease update or just be logged

        await session.commit()
        await session.refresh(lease)

        logger.info(f"Lease status updated successfully: ID {lease_id} status changed from {original_status} to {new_status} by user {current_user.id}")
        return lease

    except Exception as db_error:
        await session.rollback()
        logger.error(f"Database error during lease status update for lease {lease_id}: {str(db_error)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error updating lease status: {str(db_error)}"
        )

@router.post("/{lease_id}/upload", response_model=LeaseDocumentResponse)
async def upload_lease_document(
    lease_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Upload a document associated with a lease, checking permissions."""
    lease = await check_lease_permission(lease_id, session, current_user, action="upload document to")

    # Upload file (replace with actual blob storage logic)
    try:
        file_url = await upload_lease_to_blob(file, current_user.id, lease_id=lease_id)
        logger.info(f"Lease document uploaded to blob storage: {file_url}")
    except Exception as upload_error:
        logger.error(f"Failed to upload lease document to blob storage: {str(upload_error)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(upload_error)}"
        )

    # Create document record
    document = LeaseDocument(
        name=file.filename,
        file_path=file_url, # Use the actual URL from blob storage
        document_type=document_type,
        lease_id=lease_id,
        uploaded_by_id=current_user.id,
        upload_date=datetime.utcnow()
    )

    try:
        session.add(document)
        await session.commit()
        await session.refresh(document)

        logger.info(f"Lease document record created: {document.id} for lease {lease_id} by user {current_user.id}")
        return document
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating lease document record for lease {lease_id}: {str(e)}", exc_info=True)
        # Consider deleting the uploaded blob if DB insert fails
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save document record: {str(e)}"
        )

@router.get("/{lease_id}/documents", response_model=List[LeaseDocumentResponse])
async def get_lease_documents(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all documents associated with a lease, checking permissions."""
    lease = await check_lease_permission(lease_id, session, current_user, action="view documents for")

    # Get documents
    query = select(LeaseDocument).where(LeaseDocument.lease_id == lease_id)
    result = await session.execute(query)
    documents = result.scalars().all()

    return documents

# Analyze and Parse endpoints likely need permission checks too,
# depending on whether they operate on existing leases or just raw files.
# Assuming they operate on files before a lease is created/saved,
# we only need to check if the user *can* create leases (Landlord/Admin).

@router.post("/analyze", response_model=LeaseAnalysisResponse)
async def analyze_lease(
    file: UploadFile = File(...),
    # property_id: int = Form(...), # property_id might not be needed if analyzing before creation
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Analyze a lease document (check user can create leases)."""
    # Check if user is authorized to perform actions related to lease creation
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    if user_type not in [UserType.ADMIN.value, UserType.LANDLORD.value, 'ADMIN', 'LANDLORD']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to analyze leases")

    try:
        logger.info(f"Starting lease analysis by user {current_user.id}")
        content = await file.read()
        # Assuming UTF-8, handle potential decoding errors
        try:
             text_content = content.decode('utf-8')
        except UnicodeDecodeError:
             logger.warning("Failed to decode lease file as UTF-8, trying latin-1")
             try:
                 text_content = content.decode('latin-1')
             except UnicodeDecodeError as decode_err:
                 logger.error(f"Failed to decode lease file content: {decode_err}")
                 raise HTTPException(status_code=400, detail="Could not decode file content.")

        logger.debug(f"File content preview: {text_content[:100]}...")
        analysis_result = analyze_lease_text(text_content)
        logger.info("Lease analysis completed successfully")
        logger.debug(f"Analysis result: {analysis_result}")

        # Safely extract and convert data
        monthly_rent_raw = analysis_result.get('rent_payment', {}).get('monthly_rent', '0')
        security_deposit_raw = analysis_result.get('deposits', {}).get('security_deposit', '0')

        def parse_currency(value_str):
            if not isinstance(value_str, str):
                value_str = str(value_str)
            # Remove currency symbols, commas, and whitespace
            cleaned_str = re.sub(r"[$,\s]", "", value_str)
            try:
                return float(cleaned_str)
            except ValueError:
                logger.warning(f"Could not parse currency value: {value_str!r}")
                return 0.0 # Default to 0 if parsing fails

        response_data = {
            "monthly_rent": parse_currency(monthly_rent_raw),
            "start_date": analysis_result.get('term_details', {}).get('lease_start_date'),
            "end_date": analysis_result.get('term_details', {}).get('lease_end_date'),
            "security_deposit": parse_currency(security_deposit_raw),
            "tenant_name": analysis_result.get('core_identifiers', {}).get('tenant_name'),
            "unit": analysis_result.get('core_identifiers', {}).get('unit_number')
        }

        # Validate date formats (ensure they are YYYY-MM-DD or can be parsed)
        try:
            if response_data["start_date"]:
                response_data["start_date"] = date.fromisoformat(response_data["start_date"])
            if response_data["end_date"]:
                response_data["end_date"] = date.fromisoformat(response_data["end_date"])
        except (ValueError, TypeError) as date_err:
             logger.error(f"Invalid date format received from LLM: {date_err}")
             # Decide how to handle - raise error or return null/original string?
             # Raising error for now to enforce format.
             raise HTTPException(status_code=422, detail=f"Invalid date format in analyzed data: {date_err}")


        logger.info(f"Formatted response data: {response_data}")
        return response_data

    except ValueError as e:
        logger.error(f"Validation error in lease analysis: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing lease: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to analyze lease: {str(e)}")

@router.post("/parse", response_model=LeaseAnalysisResponse)
async def parse_lease(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Parse a lease PDF (check user can create leases)."""
    # Check if user is authorized
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    if user_type not in [UserType.ADMIN.value, UserType.LANDLORD.value, 'ADMIN', 'LANDLORD']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to parse leases")
    logger.info(f"User {current_user.id} authorized to parse lease")

    try:
        await file.seek(0) # Reset file pointer to the beginning
        content = await file.read()
        if not content:
            logger.error("File content is empty after reading.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file content is empty or could not be read.")
            
        pdf_document = fitz.open(stream=content, filetype="pdf")
        text = "".join(page.get_text() for page in pdf_document)
        pdf_document.close()

        logger.info(f"Sending lease text for analysis (first 100 chars): {text[:100]!r}")
        raw_parsed_data = analyze_lease_text(text)
        logger.info(f"Raw LLM parsed data:\n{json.dumps(raw_parsed_data, indent=2)}")

        # --- Safely extract and parse data (improved parsing logic) ---
        parsed_data = {}
        try:
            # Function to safely parse currency strings
            def parse_currency(value_str):
                if not isinstance(value_str, str):
                    value_str = str(value_str)
                # Remove currency symbols, commas, and whitespace
                cleaned_str = re.sub(r"[$,\s]", "", value_str)
                # Handle potential edge cases like empty strings or non-numeric chars
                if not cleaned_str or not re.match(r"^\d*\.?\d+$", cleaned_str):
                    logger.warning(f"Could not parse currency value: {value_str!r}. Defaulting to 0.0")
                    return 0.0
                try:
                    return float(cleaned_str)
                except ValueError:
                    logger.warning(f"Could not convert cleaned currency value to float: {cleaned_str!r}. Defaulting to 0.0")
                    return 0.0

            parsed_data['monthly_rent'] = parse_currency(raw_parsed_data.get('rent_payment', {}).get('monthly_rent', '0'))
            parsed_data['security_deposit'] = parse_currency(raw_parsed_data.get('deposits', {}).get('security_deposit', '0'))

            # Safely get dates and tenant name
            parsed_data['start_date'] = raw_parsed_data.get('term_details', {}).get('lease_start_date')
            parsed_data['end_date'] = raw_parsed_data.get('term_details', {}).get('lease_end_date')
            parsed_data['tenant_name'] = raw_parsed_data.get('core_identifiers', {}).get('tenant_name')
            parsed_data['unit'] = raw_parsed_data.get('core_identifiers', {}).get('unit_number')

            # Validate and convert dates
            for key in ['start_date', 'end_date']:
                date_str = parsed_data.get(key)
                if date_str:
                    try:
                        parsed_data[key] = date.fromisoformat(date_str)
                    except (ValueError, TypeError):
                        logger.error(f"Invalid date format for {key}: {date_str!r}")
                        raise HTTPException(status_code=422, detail=f"Invalid date format for {key}: '{date_str}'")
                else:
                    parsed_data[key] = None # Ensure None if missing/empty

        except Exception as parse_error: # Catch broader errors during parsing
            logger.error(f"Error processing LLM response data: {parse_error}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Error processing parsed lease data: {parse_error}")

        logger.info(f"Restructured data: {parsed_data}")
        return parsed_data # Return dict matching LeaseAnalysisResponse

    except Exception as e:
        logger.error(f"Failed to parse lease document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to parse lease document: {str(e)}")
