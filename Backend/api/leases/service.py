# Standard library imports
import json
import logging
import re
from datetime import date
from decimal import Decimal
from uuid import UUID as PythonUUID

# Third-party imports
import fitz
from fastapi import File, Form, HTTPException, UploadFile, status
from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlmodel import col

# Local application imports
from Backend.api.leases.schemas import LeaseAnalysisResponse, LeaseCreate, LeaseUpdate
from Backend.database import get_session
from Backend.models.enums import UserType
from Backend.models.lease import Lease, LeaseDocument, LeaseStatus
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.utils.azure_blob import upload_lease_to_blob
from Backend.utils.datetime_utils import create_audit_datetime
from Backend.llm.lease_parser import analyze_lease_text

# Configure logging
logger = logging.getLogger(__name__)


async def _apply_active_lease_side_effects(lease: Lease, session: AsyncSession) -> None:
    try:
        logger.info("Applying active lease side effects for lease ID: %s", lease.id)
        stmt = (
            update(Tenant)
            .where(col(Tenant.id) == lease.tenant_id)
            .values(current_property_id=lease.property_id, updated_at=create_audit_datetime())
        )
        await session.execute(stmt)
        logger.info("Tenant's current property updated successfully for lease ID: %s", lease.id)

        if lease.unit_id:
            logger.info("Updating PropertyUnit %s for active lease %s", lease.unit_id, lease.id)
            unit_query = select(PropertyUnit).where(col(PropertyUnit.id) == lease.unit_id).with_for_update()
            unit_result = await session.execute(unit_query)
            unit_to_update = unit_result.scalar_one_or_none()

            if unit_to_update:
                unit_to_update.tenant_id = lease.tenant_id
                unit_to_update.is_rented = True
                unit_to_update.monthly_rent = lease.monthly_rent
                unit_to_update.updated_at = create_audit_datetime()
                logger.info(
                    "PropertyUnit %s updated for lease %s: tenant_id=%s, is_rented=%s, monthly_rent=%s",
                    unit_to_update.id,
                    lease.id,
                    unit_to_update.tenant_id,
                    unit_to_update.is_rented,
                    unit_to_update.monthly_rent,
                )
            else:
                logger.error(
                    "PropertyUnit with ID %s not found for lease %s during side effect application. Rolling back.",
                    lease.unit_id,
                    lease.id,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Property unit {lease.unit_id} not found or conflict during lease activation side effects.",
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error applying active lease side effects for lease %s", lease.id)
        raise


async def _revoke_active_lease_side_effects(lease: Lease, session: AsyncSession) -> None:
    try:
        logger.info("Revoking active lease side effects for lease ID: %s", lease.id)
        if lease.unit_id:
            logger.info("Updating PropertyUnit %s for deactivated lease %s", lease.unit_id, lease.id)
            unit_query = select(PropertyUnit).where(col(PropertyUnit.id) == lease.unit_id).with_for_update()
            unit_result = await session.execute(unit_query)
            unit_to_update = unit_result.scalar_one_or_none()
            if unit_to_update and unit_to_update.tenant_id == lease.tenant_id:
                unit_to_update.is_rented = False
                unit_to_update.tenant_id = None
                unit_to_update.updated_at = create_audit_datetime()
                logger.info("PropertyUnit %s marked as vacant for lease %s", unit_to_update.id, lease.id)
            elif unit_to_update:
                logger.warning(
                    "PropertyUnit %s tenant_id %s does not match lease tenant_id %s. Skipping unit update.",
                    lease.unit_id,
                    unit_to_update.tenant_id,
                    lease.tenant_id,
                )
            else:
                logger.warning(
                    "PropertyUnit %s not found during lease deactivation for lease %s.", lease.unit_id, lease.id
                )

        if lease.tenant_id and lease.property_id:
            other_active_leases_query = (
                select(col(Lease.id))
                .where(
                    col(Lease.tenant_id) == lease.tenant_id,
                    col(Lease.status) == LeaseStatus.ACTIVE,
                    col(Lease.id) != lease.id,
                )
                .limit(1)
            )
            other_active_lease_exists = await session.scalar(other_active_leases_query)

            if not other_active_lease_exists:
                logger.info("No other active leases found for tenant %s. Clearing current_property_id.", lease.tenant_id)
                tenant_to_update = await session.get(Tenant, lease.tenant_id)
                if tenant_to_update and tenant_to_update.current_property_id == lease.property_id:
                    stmt = (
                        update(Tenant)
                        .where(col(Tenant.id) == lease.tenant_id)
                        .values(current_property_id=None, updated_at=create_audit_datetime())
                    )
                    await session.execute(stmt)
                    logger.info("Cleared current_property_id for tenant %s.", lease.tenant_id)
                elif tenant_to_update:
                    logger.info(
                        "Tenant %s current_property_id (%s) does not match deactivated lease property_id (%s). Not clearing.",
                        lease.tenant_id,
                        tenant_to_update.current_property_id,
                        lease.property_id,
                    )
                else:
                    logger.warning("Tenant %s not found for clearing current_property_id.", lease.tenant_id)
            else:
                logger.info("Tenant %s has other active leases. Not clearing current_property_id.", lease.tenant_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error revoking active lease side effects for lease %s", lease.id)
        raise


async def check_lease_permission(
    lease_id: int, session: AsyncSession, current_user: User, action: str = "view"
) -> Lease:
    query = select(Lease).options(selectinload(getattr(Lease, "property"))).where(col(Lease.id) == lease_id)
    result = await session.execute(query)
    lease = result.scalar_one_or_none()

    if not lease:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lease with ID {lease_id} not found")

    if current_user.is_admin:
        return lease

    if current_user.user_type == UserType.TENANT:
        tenant_query = select(Tenant).where(col(Tenant.user_id) == current_user.id)
        tenant_result = await session.execute(tenant_query)
        tenant = tenant_result.scalar_one_or_none()
        
        if tenant and lease.tenant_id == tenant.id and action == "view":
            return lease
        else:
            logger.warning(f"Tenant {current_user.id} permission denied for {action} lease {lease_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Not authorized to {action} this lease"
            )

    if current_user.user_type == UserType.LANDLORD:
        if lease.property and lease.property.user_id == current_user.id:
            return lease
        else:
            logger.warning(
                f"Landlord {current_user.id} permission denied for {action} lease {lease_id} on property {lease.property_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Not authorized to {action} this lease"
            )

    logger.error(
        f"Unknown user type or permission error for user {current_user.id}, action {action}, lease {lease_id}"
    )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not authorized to {action} this lease")


async def upload_lease(file: UploadFile, current_user: User):
    logger.info(f"Uploading lease file: {file.filename} for user ID: {current_user.id}")

    if current_user.user_type not in [UserType.ADMIN.value, UserType.LANDLORD.value]:
        logger.warning(
            f"Authorization failed: User {current_user.id} with type {current_user.user_type} attempted to upload lease"
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to upload leases")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are accepted")

    file_url = await upload_lease_to_blob(file, current_user.id)
    logger.info(f"Lease file uploaded successfully: {file_url}")
    return {"file_url": file_url}


async def create_lease(lease_data: LeaseCreate, current_user: User, session: AsyncSession):
    logger.info(
        "Create lease request by user: id=%s, email=%s, type=%s",
        current_user.id,
        current_user.email,
        current_user.user_type,
    )
    file_url = getattr(lease_data, "file_url", None)
    if file_url:
        logger.info("Lease creation includes document URL: %s", file_url)

    try:
        property_query = select(Property).where(col(Property.id) == lease_data.property_id)
        property_result = await session.execute(property_query)
        target_property = property_result.scalar_one_or_none()

        if not target_property:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid property ID")

        if not current_user.is_admin and target_property.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} (Landlord) attempted to create lease for property {lease_data.property_id} they don't own"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create leases for this property"
            )

        tenant_query = select(Tenant).where(col(Tenant.id) == lease_data.tenant_id)
        tenant_exists = await session.scalar(tenant_query)
        if not tenant_exists:
            logger.error(f"Tenant not found with ID: {lease_data.tenant_id}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")

        if lease_data.unit_id:
            unit_query = select(col(PropertyUnit.id)).where(
                and_(
                    col(PropertyUnit.id) == lease_data.unit_id, col(PropertyUnit.property_id) == lease_data.property_id
                )
            )
            unit_exists = await session.scalar(unit_query)
            if not unit_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid unit ID or unit does not belong to the specified property",
                )

        new_lease = Lease(
            **lease_data.model_dump(exclude={"file_url"}),
            created_at=create_audit_datetime(),
            updated_at=create_audit_datetime(),
        )

        session.add(new_lease)
        await session.flush()

        if new_lease.id is None:
            logger.error("Lease ID is None after database flush. Rolling back session.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Critical error: Lease ID missing after flush."
            )

        if file_url:
            try:
                logger.info("Creating lease document record for lease %s with URL: %s", new_lease.id, file_url)
                document = LeaseDocument(
                    name="Lease Agreement",
                    file_path=file_url,
                    document_type="contract",
                    upload_date=create_audit_datetime(),
                    lease_id=new_lease.id,
                    uploaded_by_id=current_user.id,
                )
                session.add(document)
                logger.info("Lease document record created successfully for lease %s", new_lease.id)
            except Exception:
                logger.exception("Error creating lease document record")

        if new_lease.status == LeaseStatus.ACTIVE:
            await _apply_active_lease_side_effects(new_lease, session)

        await session.commit()
        await session.refresh(new_lease, attribute_names=["tenant", "property"])

        logger.info("Lease created: %s with status %s by user %s", new_lease.id, new_lease.status, current_user.id)
        return new_lease
    except HTTPException:
        # Re-raise HTTPExceptions as they already have proper status codes
        raise
    except Exception as e:
        logger.exception("Unexpected error in create_lease: %s", str(e))
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lease: {str(e)}"
        )


async def get_leases(
    current_user: User, session: AsyncSession, lease_status: LeaseStatus | None, property_id: int | None, tenant_id: int | None
):
    logger.info(
        "Fetching leases for user %s (type: %s) with filters - status: %s, property_id: %s, tenant_id: %s",
        current_user.id, current_user.user_type, lease_status, property_id, tenant_id
    )
    
    try:
        query = select(Lease).options(
            selectinload(getattr(Lease, "tenant")),
            selectinload(getattr(Lease, "property")),
            selectinload(getattr(Lease, "unit")),
        )

        conditions = []
        if lease_status:
            conditions.append(col(Lease.status) == lease_status)
            logger.debug("Added status filter: %s", lease_status)
        if property_id:
            conditions.append(col(Lease.property_id) == property_id)
            logger.debug("Added property_id filter: %s", property_id)
        if tenant_id:
            if current_user.user_type != UserType.TENANT:
                conditions.append(col(Lease.tenant_id) == tenant_id)
                logger.debug("Added tenant_id filter: %s", tenant_id)
            else:
                # Look up tenant by user_id
                logger.debug("Looking up tenant for user_id: %s", current_user.id)
                tenant_query = select(Tenant).where(col(Tenant.user_id) == current_user.id)
                tenant_result = await session.execute(tenant_query)
                tenant = tenant_result.scalar_one_or_none()
                
                if not tenant or tenant.id != tenant_id:
                    logger.warning(f"Tenant {current_user.id} attempted to filter leases for tenant {tenant_id}")
                    return []
                conditions.append(col(Lease.tenant_id) == tenant.id)
                logger.debug("Added tenant_id filter for tenant user: %s", tenant.id)

        if current_user.user_type == UserType.TENANT:
            # Look up tenant by user_id
            logger.debug("Fetching leases for tenant user: %s", current_user.id)
            tenant_query = select(Tenant).where(col(Tenant.user_id) == current_user.id)
            tenant_result = await session.execute(tenant_query)
            tenant = tenant_result.scalar_one_or_none()
            
            if tenant:
                conditions.append(col(Lease.tenant_id) == tenant.id)
                logger.debug("Found tenant record %s for user %s", tenant.id, current_user.id)
            else:
                logger.warning("No tenant record found for user %s", current_user.id)
                return []
        elif current_user.user_type == UserType.LANDLORD:
            logger.debug("Fetching leases for landlord user: %s", current_user.id)
            query = query.join(Property, col(Lease.property_id) == col(Property.id)).where(
                col(Property.user_id) == current_user.id
            )
            logger.debug("Added property ownership filter for landlord")

        if conditions:
            query = query.where(and_(*conditions))
            logger.debug("Applied %d conditions to lease query", len(conditions))

        logger.debug("Executing lease query...")
        result = await session.execute(query)
        leases = result.scalars().unique().all()
        logger.info("Successfully fetched %d leases for user %s", len(leases), current_user.id)
        return list(leases)
        
    except Exception as e:
        logger.exception("❌ Error fetching leases for user %s: %s", current_user.id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch leases: {str(e)}"
        )


async def get_lease(lease_id: int, current_user: User, session: AsyncSession):
    return await check_lease_permission(lease_id, session, current_user, action="view")


async def update_lease(lease_id: int, lease_data: LeaseUpdate, current_user: User, session: AsyncSession):
    lease = await check_lease_permission(lease_id, session, current_user, action="update")

    lease_data_dict = lease_data.model_dump(exclude_unset=True)

    if "status" in lease_data_dict:
        logger.warning(
            "Attempt to update status via general update endpoint for lease %s. "
            "Status field will be ignored. Use POST /leases/{lease_id}/status for status changes.",
            lease_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="`status` cannot be updated here. Use POST /leases/{lease_id}/status."
        )

    for key, value in lease_data_dict.items():
        setattr(lease, key, value)

    lease.updated_at = create_audit_datetime()

    session.add(lease)
    await session.commit()
    await session.refresh(lease, attribute_names=["tenant", "property", "unit"])

    logger.info(
        "Lease updated: %s by user %s. Fields updated: %s",
        lease.id,
        current_user.id,
        ", ".join(lease_data_dict.keys()),
    )
    return lease


async def validate_lease(lease_id: int, current_user: User, session: AsyncSession):
    lease = await check_lease_permission(lease_id, session, current_user, action="validate")

    if lease.status != LeaseStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Lease is not in DRAFT status (current status: {lease.status})"
        )

    lease.status = LeaseStatus.PENDING
    session.add(lease)
    await session.commit()
    await session.refresh(lease)

    logger.info("Lease validated: %s by user %s", lease.id, current_user.id)
    return lease


async def update_lease_status(lease_id: int, status_data: dict, current_user: User, session: AsyncSession):
    logger.info(
        f"Lease status update request: lease ID={lease_id}, user ID={current_user.id}, data: {status_data}"
    )
    lease = await check_lease_permission(lease_id, session, current_user, action="update status")

    new_status_str = status_data.get("status")
    if not new_status_str:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Status is required")

    try:
        new_status = LeaseStatus(new_status_str)
    except ValueError:
        valid_statuses = [s.value for s in LeaseStatus]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{new_status_str}'. Valid values are: {', '.join(valid_statuses)}",
        )

    original_status = lease.status
    if original_status == new_status:
        logger.info(f"Lease {lease_id} status already '{new_status}'. No update needed.")
        return lease

    lease.status = new_status
    session.add(lease)

    if new_status == LeaseStatus.ACTIVE and original_status != LeaseStatus.ACTIVE:
        await _apply_active_lease_side_effects(lease, session)
    elif new_status != LeaseStatus.ACTIVE and original_status == LeaseStatus.ACTIVE:
        await _revoke_active_lease_side_effects(lease, session)

    await session.commit()
    await session.refresh(lease, attribute_names=["tenant", "property", "unit"])

    logger.info(
        f"Lease status updated successfully: ID {lease_id} status changed from {original_status} to {new_status} by user {current_user.id}"
    )
    return lease


async def upload_lease_document(
    lease_id: int, document_type: str, file: UploadFile, current_user: User, session: AsyncSession
):
    await check_lease_permission(lease_id, session, current_user, action="upload document to")

    try:
        file_url = await upload_lease_to_blob(file, current_user.id)
        logger.info(f"Lease document uploaded to blob storage: {file_url}")
    except Exception as upload_error:
        logger.exception("Failed to upload lease document to blob storage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload file: {str(upload_error)}"
        )

    document = LeaseDocument(
        name=file.filename or "Lease Document",
        file_path=file_url,
        document_type=document_type,
        lease_id=lease_id,
        uploaded_by_id=current_user.id,
    )

    session.add(document)
    await session.commit()
    await session.refresh(document)

    logger.info(
        f"Lease document record created: {document.id} for lease {lease_id} by user {current_user.id}"
    )
    return document


async def get_lease_documents(lease_id: int, current_user: User, session: AsyncSession):
    await check_lease_permission(lease_id, session, current_user, action="view documents for")

    query = select(LeaseDocument).where(col(LeaseDocument.lease_id) == lease_id)
    result = await session.execute(query)
    documents = result.scalars().all()
    return documents


async def analyze_lease(file: UploadFile, current_user: User):
    if current_user.user_type not in [UserType.ADMIN.value, UserType.LANDLORD.value]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to analyze leases")

    try:
        logger.info(f"Starting lease analysis by user {current_user.id}")
        content = await file.read()
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("Failed to decode lease file as UTF-8, trying latin-1")
            try:
                text_content = content.decode("latin-1")
            except UnicodeDecodeError as decode_err:
                logger.error(f"Failed to decode lease file content: {decode_err}")
                raise HTTPException(status_code=400, detail="Could not decode file content.")

        logger.debug(f"File content preview: {text_content[:100]}...")
        analysis_result = await analyze_lease_text(text_content)
        logger.info("Lease analysis completed successfully")
        logger.debug(f"Analysis result: {analysis_result}")

        def parse_currency(value_str):
            if not isinstance(value_str, str):
                value_str = str(value_str)
            cleaned_str = re.sub(r"[$,\s]", "", value_str)
            try:
                return Decimal(cleaned_str)
            except Exception:
                logger.warning(f"Could not parse currency value: {value_str!r}")
                return Decimal("0.0")

        response_data = {
            "monthly_rent": parse_currency(analysis_result.get("rent_payment", {}).get("monthly_rent", "0")),
            "start_date": analysis_result.get("term_details", {}).get("lease_start_date"),
            "end_date": analysis_result.get("term_details", {}).get("lease_end_date"),
            "security_deposit": parse_currency(analysis_result.get("deposits", {}).get("security_deposit", "0")),
            "tenant_name": analysis_result.get("core_identifiers", {}).get("tenant_name"),
            "unit": analysis_result.get("core_identifiers", {}).get("unit_number"),
        }

        start_date_str = response_data["start_date"]
        end_date_str = response_data["end_date"]

        try:
            response_data["start_date"] = date.fromisoformat(start_date_str) if start_date_str else None
            response_data["end_date"] = date.fromisoformat(end_date_str) if end_date_str else None
        except ValueError as date_err:
            logger.error(
                f"Invalid date format received from LLM after defaulting: {date_err} for start: '{start_date_str}', end: '{end_date_str}'"
            )
            response_data["start_date"] = None
            response_data["end_date"] = None

        logger.info(f"Formatted response data: {response_data}")
        return LeaseAnalysisResponse(**response_data)

    except ValueError as e:
        logger.error(f"Validation error in lease analysis: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error analyzing lease")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to analyze lease: {str(e)}"
        )


async def parse_lease(file: UploadFile, current_user: User):
    if current_user.user_type not in [UserType.ADMIN.value, UserType.LANDLORD.value]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to parse leases")
    logger.info(f"User {current_user.id} authorized to parse lease")

    try:
        await file.seek(0)
        content = await file.read()
        if not content:
            logger.error("File content is empty after reading.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file content is empty or could not be read.",
            )

        pdf_document = fitz.open(stream=content, filetype="pdf")
        text = "".join(getattr(page, "get_text")() for page in pdf_document)
        pdf_document.close()

        if not text or not text.strip():
            logger.error("No text extracted from PDF file")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text could be extracted from the PDF file. Please ensure the PDF contains selectable text."
            )

        logger.info(f"Extracted {len(text)} characters from PDF")
        logger.info(f"Sending lease text for analysis (first 200 chars): {text[:200]!r}")
        
        try:
            raw_parsed_data = await analyze_lease_text(text)
        except ValueError as llm_error:
            logger.error(f"LLM analysis failed: {llm_error}")
            # Re-raise with more context
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to analyze lease document: {str(llm_error)}"
            ) from llm_error
        logger.info(f"Raw LLM parsed data:\n{json.dumps(raw_parsed_data, indent=2)}")

        parsed_data = {}
        try:

            def parse_currency(value_str):
                if not isinstance(value_str, str):
                    value_str = str(value_str)
                cleaned_str = re.sub(r"[$,\s]", "", value_str)
                if not cleaned_str or not re.match(r"^\d*\.?\d+$", cleaned_str):
                    logger.warning(f"Could not parse currency value: {value_str!r}. Defaulting to 0.0")
                    return Decimal("0.0")
                try:
                    return Decimal(cleaned_str)
                except Exception:
                    logger.warning(
                        f"Could not convert cleaned currency value to float: {cleaned_str!r}. Defaulting to 0.0"
                    )
                    return Decimal("0.0")

            parsed_data["monthly_rent"] = parse_currency(
                raw_parsed_data.get("rent_payment", {}).get("monthly_rent", "0")
            )
            parsed_data["security_deposit"] = parse_currency(
                raw_parsed_data.get("deposits", {}).get("security_deposit", "0")
            )

            parsed_data["start_date"] = raw_parsed_data.get("term_details", {}).get("lease_start_date")
            parsed_data["end_date"] = raw_parsed_data.get("term_details", {}).get("lease_end_date")
            parsed_data["tenant_name"] = raw_parsed_data.get("core_identifiers", {}).get("tenant_name")
            parsed_data["unit"] = raw_parsed_data.get("core_identifiers", {}).get("unit_number")

            start_date_str = parsed_data.get("start_date")
            end_date_str = parsed_data.get("end_date")

            try:
                parsed_data["start_date"] = date.fromisoformat(start_date_str) if start_date_str else None
                parsed_data["end_date"] = date.fromisoformat(end_date_str) if end_date_str else None
            except ValueError as date_err:
                logger.error(
                    f"Invalid date format for start_date: '{start_date_str}' or end_date: '{end_date_str}' after LLM defaulting - setting to None. Error: {date_err}"
                )
                parsed_data["start_date"] = None
                parsed_data["end_date"] = None

        except Exception as parse_error:
            logger.exception("Error processing LLM response data: %s", parse_error)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Error processing parsed lease data: {parse_error}",
            )

        logger.info(f"Restructured data: {parsed_data}")
        return LeaseAnalysisResponse(**parsed_data)

    except Exception as e:
        logger.exception("Failed to parse lease document")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to parse lease document: {str(e)}"
        )


async def delete_lease(lease_id: int, current_user: User, session: AsyncSession) -> None:
    logger.info("Delete request for lease %s by user %s", lease_id, current_user.id)
    lease = await check_lease_permission(lease_id, session, current_user, action="delete")

    try:
        if lease.status == LeaseStatus.ACTIVE:
            logger.info("Lease %s is active, revoking side effects before deletion.", lease_id)
            await _revoke_active_lease_side_effects(lease, session)

        await session.delete(lease)
        await session.commit()
        logger.info("Lease %s deleted successfully by user %s", lease_id, current_user.id)
    except Exception as e:
        await session.rollback()
        logger.exception("Error deleting lease %s", lease_id)
        if "violates foreign key constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete lease because it is still referenced by other records. "
                "Ensure migrations are applied to handle this automatically.",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lease: {str(e)}",
        ) from e 