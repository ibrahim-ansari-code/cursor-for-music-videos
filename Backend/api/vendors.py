import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from Backend.database import get_session
from Backend.models.vendor import Vendor, VendorDocument, VendorStatus
from Backend.models.property import PropertyVendorLink
from Backend.models.user import User, UserType
from Backend.api.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/vendors",
    tags=["vendors"],
)

# API models
class VendorBase(BaseModel):
    company_name: str
    business_type: str
    tax_id: Optional[str] = None
    website: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    insurance_expiry_date: Optional[datetime] = None

class VendorCreate(VendorBase):
    user_id: int

class VendorUpdate(BaseModel):
    company_name: Optional[str] = None
    business_type: Optional[str] = None
    tax_id: Optional[str] = None
    website: Optional[str] = None
    status: Optional[VendorStatus] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    insurance_expiry_date: Optional[datetime] = None

class VendorResponse(VendorBase):
    id: int
    user_id: int
    status: VendorStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class VendorDocumentResponse(BaseModel):
    id: int
    name: str
    file_path: str
    document_type: str
    expiry_date: Optional[datetime] = None
    upload_date: datetime
    
    class Config:
        orm_mode = True

class PropertyAssignmentRequest(BaseModel):
    property_id: int
    is_active: bool = True

# API endpoints
@router.post("/", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    vendor_data: VendorCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new vendor"""
    # If a user is creating their own vendor profile, override user_id with current user's ID
    if current_user.user_type == UserType.VENDOR:
        vendor_data.user_id = current_user.id
    # If admin is creating a vendor profile for someone else, check that the user exists
    elif current_user.user_type == UserType.ADMIN:
        # Check if user exists
        query = select(User).where(User.id == vendor_data.user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {vendor_data.user_id} not found"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create vendor profiles"
        )
    
    # Check if the user already has a vendor profile
    query = select(Vendor).where(Vendor.user_id == vendor_data.user_id)
    result = await session.execute(query)
    existing_vendor = result.scalar_one_or_none()
    
    if existing_vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with ID {vendor_data.user_id} already has a vendor profile"
        )
    
    # Create new vendor
    new_vendor = Vendor(**vendor_data.dict())
    session.add(new_vendor)
    await session.commit()
    await session.refresh(new_vendor)
    
    logger.info(f"Vendor created: {new_vendor.id} for user {vendor_data.user_id}")
    return new_vendor

@router.get("/", response_model=List[VendorResponse])
async def get_vendors(
    status: Optional[VendorStatus] = None,
    business_type: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all vendors with optional filtering"""
    # Build query with filters
    query = select(Vendor)
    
    if status:
        query = query.where(Vendor.status == status)
    if business_type:
        query = query.where(Vendor.business_type == business_type)
    
    # Apply access control based on user type
    if current_user.user_type == UserType.VENDOR:
        # Vendors can only see their own profile
        query = query.where(Vendor.user_id == current_user.id)
    
    result = await session.execute(query)
    vendors = result.scalars().all()
    return vendors

@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific vendor by ID"""
    query = select(Vendor).where(Vendor.id == vendor_id)
    result = await session.execute(query)
    vendor = result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found"
        )
    
    # Apply access control
    if current_user.user_type == UserType.VENDOR and vendor.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this vendor profile"
        )
    
    return vendor

@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: int,
    vendor_data: VendorUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update a vendor profile"""
    query = select(Vendor).where(Vendor.id == vendor_id)
    result = await session.execute(query)
    vendor = result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found"
        )
    
    # Apply access control
    if current_user.user_type == UserType.VENDOR:
        if vendor.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this vendor profile"
            )
        
        # Vendors cannot update their own status
        if vendor_data.status is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vendors cannot update their own status"
            )
    
    # Update fields
    vendor_data_dict = vendor_data.dict(exclude_unset=True)
    for key, value in vendor_data_dict.items():
        setattr(vendor, key, value)
    
    # Update timestamp
    vendor.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(vendor)
    
    logger.info(f"Vendor updated: {vendor.id} by user {current_user.id}")
    return vendor

@router.post("/{vendor_id}/status", response_model=VendorResponse)
async def update_vendor_status(
    vendor_id: int,
    status: VendorStatus,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update the status of a vendor (approve, deny, deactivate)"""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update vendor status"
        )
    
    query = select(Vendor).where(Vendor.id == vendor_id)
    result = await session.execute(query)
    vendor = result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found"
        )
    
    # Update vendor status
    vendor.status = status
    vendor.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(vendor)
    
    logger.info(f"Vendor status updated to {status}: {vendor.id} by user {current_user.id}")
    return vendor

@router.post("/{vendor_id}/upload", response_model=VendorDocumentResponse)
async def upload_vendor_document(
    vendor_id: int,
    document_type: str = Form(...),
    expiry_date: Optional[datetime] = Form(None),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Upload a document associated with a vendor"""
    # Check if vendor exists
    query = select(Vendor).where(Vendor.id == vendor_id)
    result = await session.execute(query)
    vendor = result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found"
        )
    
    # Check permissions
    if current_user.user_type == UserType.VENDOR and vendor.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload documents for this vendor"
        )
    
    # In a real application, we would save the file to a storage system
    # For this example, we'll just pretend we saved it and return the path
    file_path = f"/uploads/vendors/{vendor_id}/{file.filename}"
    
    # Create document record
    document = VendorDocument(
        name=file.filename,
        file_path=file_path,
        document_type=document_type,
        expiry_date=expiry_date,
        vendor_id=vendor_id
    )
    
    session.add(document)
    await session.commit()
    await session.refresh(document)
    
    logger.info(f"Vendor document uploaded: {document.id} for vendor {vendor_id}")
    return document

@router.get("/{vendor_id}/documents", response_model=List[VendorDocumentResponse])
async def get_vendor_documents(
    vendor_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all documents associated with a vendor"""
    # Check if vendor exists
    query = select(Vendor).where(Vendor.id == vendor_id)
    result = await session.execute(query)
    vendor = result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found"
        )
    
    # Apply access control
    if current_user.user_type == UserType.VENDOR and vendor.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access documents for this vendor"
        )
    
    # Get documents
    query = select(VendorDocument).where(VendorDocument.vendor_id == vendor_id)
    result = await session.execute(query)
    documents = result.scalars().all()
    
    return documents

@router.post("/{vendor_id}/properties", response_model=VendorResponse)
async def assign_vendor_to_property(
    vendor_id: int,
    assignment: PropertyAssignmentRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Assign a vendor to a property"""
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to assign vendors to properties"
        )
    
    # Check if vendor exists
    query = select(Vendor).where(Vendor.id == vendor_id)
    result = await session.execute(query)
    vendor = result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found"
        )
    
    # Check if property exists
    # In a real app, we'd verify that the property exists and that the current user has access to it
    
    # Check if the assignment already exists
    query = select(PropertyVendorLink).where(
        PropertyVendorLink.vendor_id == vendor_id,
        PropertyVendorLink.property_id == assignment.property_id
    )
    result = await session.execute(query)
    existing_link = result.scalar_one_or_none()
    
    if existing_link:
        # Update the existing link
        existing_link.is_active = assignment.is_active
    else:
        # Create a new link
        new_link = PropertyVendorLink(
            vendor_id=vendor_id,
            property_id=assignment.property_id,
            is_active=assignment.is_active
        )
        session.add(new_link)
    
    await session.commit()
    
    # Refresh the vendor to get updated relationships
    await session.refresh(vendor)
    
    logger.info(f"Vendor {vendor_id} assigned to property {assignment.property_id} by user {current_user.id}")
    return vendor

@router.post("/ai/onboarding-help", status_code=status.HTTP_200_OK)
async def get_vendor_onboarding_help(
    query: str,
    current_user: User = Depends(get_current_user)
):
    """AI assistance for vendor onboarding"""
    # This is a placeholder for the chatbot API to assist vendors during onboarding
    # In a real implementation, this would connect to an AI service
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query is required"
        )
    
    # Return a mock response
    responses = {
        "insurance": "Vendors need to provide proof of liability insurance. Upload your insurance certificate in the documents section.",
        "payment": "Payment terms are typically net-30 from the date of invoice approval. Make sure to include your invoice number on all communications.",
        "documents": "Required documents include: W-9 form, Certificate of Insurance, and business license. You can upload these in the Documents section.",
        "approval": "Once you've submitted all required documents, our team will review your application within 5 business days."
    }
    
    # Simple keyword matching for demo purposes
    for keyword, response in responses.items():
        if keyword.lower() in query.lower():
            return {"response": response}
    
    # Default response
    return {
        "response": "I'm here to help with your onboarding process. You can ask about insurance requirements, payment terms, required documents, or the approval process."
    }
