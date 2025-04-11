import logging
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from pydantic import BaseModel
import fitz  # PyMuPDF
import io

from Backend.database import get_session
from Backend.models.lease import Lease, LeaseStatus, LeaseDocument
from Backend.models.user import User
from Backend.api.auth import get_current_user
from Backend.utils.llm_utils import analyze_lease_text
from Backend.models.enums import UserType

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
    pass

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
    
    class Config:
        orm_mode = True

class LeaseDocumentResponse(BaseModel):
    id: int
    name: str
    file_path: str
    document_type: str
    upload_date: datetime
    
    class Config:
        orm_mode = True

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
    
    # Debug header information
    request_user_type = None
    for header in scope.get("headers", []):  # type: ignore
        if header[0].decode("utf-8").lower() == "x-debug-user-type":
            request_user_type = header[1].decode("utf-8")
            logger.info(f"Debug header user type: {request_user_type}")
    
    # Case-insensitive comparison of user types
    user_type = current_user.user_type.upper()
    logger.info(f"Normalized user type: {user_type}")
    
    # Validate that the current user has permission to create leases
    if user_type not in ["ADMIN", "LANDLORD"]:
        logger.warning(f"Unauthorized lease creation attempt by user {current_user.id} with type {user_type}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create leases"
        )

    # Validate tenant
    tenant_query = select(User).where(User.id == lease_data.tenant_id, User.user_type == UserType.TENANT)
    tenant_result = await session.execute(tenant_query)
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID"
        )

    # Validate property and unit
    property_query = select(Property).where(Property.id == lease_data.property_id)
    property_result = await session.execute(property_query)
    property = property_result.scalar_one_or_none()
    if not property:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid property ID"
        )

    if lease_data.unit_id:
        unit_query = select(PropertyUnit).where(PropertyUnit.id == lease_data.unit_id, PropertyUnit.property_id == lease_data.property_id)
        unit_result = await session.execute(unit_query)
        unit = unit_result.scalar_one_or_none()
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid unit ID"
            )

    # Create the lease
    new_lease = Lease(**lease_data.dict())
    session.add(new_lease)
    await session.commit()
    await session.refresh(new_lease)

    logger.info(f"Lease created: {new_lease.id} by user {current_user.id}")
    return new_lease

@router.get("/", response_model=List[LeaseResponse])
async def get_leases(
    status: Optional[LeaseStatus] = None,
    property_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all leases with optional filtering"""
    query = select(Lease)
    
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
        query = query.join(Property).where(Property.landlord_id == current_user.id)
    
    result = await session.execute(query)
    leases = result.scalars().all()
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
    status: LeaseStatus,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update the status of a lease (activate, terminate, etc.)"""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update lease status"
        )
    
    query = select(Lease).where(Lease.id == lease_id)
    result = await session.execute(query)
    lease = result.scalar_one_or_none()
    
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with ID {lease_id} not found"
        )
    
    # Update lease status
    lease.status = status
    lease.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(lease)
    
    logger.info(f"Lease status updated to {status}: {lease.id} by user {current_user.id}")
    return lease

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
    Analyze a lease PDF using GPT-4 to extract key fields.
    """
    # Log user info for debugging
    logger.info(f"Analyze lease request from user ID: {current_user.id}, email: {current_user.email}, type: {current_user.user_type}")
    
    # Check if user is authorized based on their type
    user_type = current_user.user_type.upper() if isinstance(current_user.user_type, str) else current_user.user_type
    
    if user_type not in [UserType.ADMIN.value, UserType.LANDLORD.value, 'ADMIN', 'LANDLORD']:
        logger.warning(f"Authorization failed: User {current_user.id} with type {user_type} attempted to analyze lease")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to analyze leases"
        )
    
    logger.info(f"User {current_user.id} authorized to analyze lease")
    
    # Validate property exists
    property_query = select(Property).where(Property.id == property_id)
    property_result = await session.execute(property_query)
    property = property_result.scalar_one_or_none()
    if not property:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid property ID"
        )
    
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
        
        # Analyze text using GPT-4
        logger.info(f"Sending lease text for analysis, length: {len(text[:100])}...")
        parsed_data = analyze_lease_text(text)
        
        # Convert string dates to date objects
        try:
            if 'start_date' in parsed_data and parsed_data['start_date']:
                parsed_data['start_date'] = datetime.strptime(parsed_data['start_date'], '%Y-%m-%d').date()
            if 'end_date' in parsed_data and parsed_data['end_date']:
                parsed_data['end_date'] = datetime.strptime(parsed_data['end_date'], '%Y-%m-%d').date()
        except ValueError as e:
            logger.error(f"Date parsing error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date format in lease: {str(e)}"
            )
        
        logger.info(f"Lease analyzed successfully by user {current_user.id}")
        return parsed_data
        
    except Exception as e:
        logger.error(f"Failed to analyze lease: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze lease document: {str(e)}"
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
        logger.info(f"Sending lease text for analysis, length: {len(text[:100])}...")
        raw_parsed_data = analyze_lease_text(text)
        
        # Restructure the data to match LeaseAnalysisResponse model
        parsed_data = {
            'monthly_rent': float(raw_parsed_data.get('rent_payment', {}).get('monthly_rent', 0)),
            'start_date': raw_parsed_data.get('term_details', {}).get('lease_start_date', ''),
            'end_date': raw_parsed_data.get('term_details', {}).get('lease_end_date', ''),
            'security_deposit': float(raw_parsed_data.get('deposits', {}).get('security_deposit', 0)),
            'tenant_name': raw_parsed_data.get('core_identifiers', {}).get('tenant_name', ''),
            'unit': raw_parsed_data.get('core_identifiers', {}).get('unit_number', '')
        }
        
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
        logger.error(f"Failed to parse lease: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse lease document: {str(e)}"
        )
