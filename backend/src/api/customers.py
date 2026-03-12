"""Customer API endpoints for unified profile and history."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..database.connection import get_session_dependency
from ..database.models import Customer
from ..services.customer_identification import CustomerIdentificationService
from ..services.conversation_service import ConversationService

logger = logging.getLogger(__name__)

router = APIRouter()


class CustomerIdentifierResponse(BaseModel):
    """Customer identifier response."""
    type: str
    value: str
    verified: bool


class LinkEmailRequest(BaseModel):
    """Request to link email to customer."""
    email: str = Field(..., description="Email address to link")
    verified: bool = Field(False, description="Whether email is verified")


class LinkPhoneRequest(BaseModel):
    """Request to link phone to customer."""
    phone: str = Field(..., description="Phone number to link")
    verified: bool = Field(False, description="Whether phone is verified")


class MergeCustomersRequest(BaseModel):
    """Request to merge customers."""
    primary_customer_id: str = Field(..., description="Customer to keep")
    secondary_customer_id: str = Field(..., description="Customer to merge")


class CustomerProfileResponse(BaseModel):
    """Customer profile response."""
    customer_id: str
    email: str | None
    phone: str | None
    name: str | None
    identifiers: list[CustomerIdentifierResponse]
    metadata: dict


class CustomerHistoryResponse(BaseModel):
    """Customer history response."""
    customer: CustomerProfileResponse
    conversations: list[dict]
    total_conversations: int
    total_messages: int


@router.get("/customers/{customer_id}/profile", response_model=CustomerProfileResponse)
async def get_customer_profile(
    customer_id: str,
    session = Depends(get_session_dependency)
):
    """Get customer profile with all identifiers.

    Args:
        customer_id: Customer UUID
        session: Database session

    Returns:
        Customer profile with identifiers

    Raises:
        HTTPException: If customer not found
    """
    try:
        # Parse UUID
        try:
            customer_uuid = UUID(customer_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid customer ID format")

        # Get customer
        customer = await session.get(Customer, customer_uuid)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        # Get identifiers
        identification_service = CustomerIdentificationService(session)
        identifiers = await identification_service.get_customer_identifiers(customer_uuid)

        return CustomerProfileResponse(
            customer_id=str(customer.id),
            email=customer.email,
            phone=customer.phone,
            name=customer.name,
            identifiers=[
                CustomerIdentifierResponse(
                    type=identifier.identifier_type.value,
                    value=identifier.identifier_value,
                    verified=identifier.verified
                )
                for identifier in identifiers
            ],
            metadata=customer.metadata_
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching customer profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch customer profile"
        )


@router.get("/customers/{customer_id}/history", response_model=CustomerHistoryResponse)
async def get_customer_history(
    customer_id: str,
    limit: int = 50,
    include_closed: bool = True,
    session = Depends(get_session_dependency)
):
    """Get unified customer conversation history across all channels.

    Args:
        customer_id: Customer UUID
        limit: Maximum messages per conversation (default 50)
        include_closed: Include closed conversations (default True)
        session: Database session

    Returns:
        Customer history with conversations from all channels

    Raises:
        HTTPException: If customer not found
    """
    try:
        # Parse UUID
        try:
            customer_uuid = UUID(customer_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid customer ID format")

        # Get customer
        customer = await session.get(Customer, customer_uuid)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        # Get identifiers
        identification_service = CustomerIdentificationService(session)
        identifiers = await identification_service.get_customer_identifiers(customer_uuid)

        # Get conversation history
        conversation_service = ConversationService(session)
        conversations = await conversation_service.get_customer_conversation_history(
            customer_id=customer_uuid,
            limit=limit,
            include_closed=include_closed
        )

        # Calculate totals
        total_conversations = len(conversations)
        total_messages = sum(conv['message_count'] for conv in conversations)

        return CustomerHistoryResponse(
            customer=CustomerProfileResponse(
                customer_id=str(customer.id),
                email=customer.email,
                phone=customer.phone,
                name=customer.name,
                identifiers=[
                    CustomerIdentifierResponse(
                        type=identifier.identifier_type.value,
                        value=identifier.identifier_value,
                        verified=identifier.verified
                    )
                    for identifier in identifiers
                ],
                metadata=customer.metadata_
            ),
            conversations=conversations,
            total_conversations=total_conversations,
            total_messages=total_messages
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching customer history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch customer history"
        )


@router.post("/customers/{customer_id}/identifiers/email")
async def link_email_to_customer(
    customer_id: str,
    request: LinkEmailRequest,
    session = Depends(get_session_dependency)
):
    """Link an email address to a customer.

    Args:
        customer_id: Customer UUID
        request: Email linking request
        session: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If customer not found or email already linked
    """
    try:
        # Parse UUID
        try:
            customer_uuid = UUID(customer_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid customer ID format")

        # Get customer
        customer = await session.get(Customer, customer_uuid)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        # Link email
        identification_service = CustomerIdentificationService(session)
        try:
            identifier = await identification_service.link_email_to_customer(
                customer_id=customer_uuid,
                email=request.email,
                verified=request.verified
            )

            return {
                "status": "success",
                "message": f"Email {request.email} linked to customer",
                "identifier_id": str(identifier.id)
            }

        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking email to customer: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to link email to customer"
        )


@router.post("/customers/{customer_id}/identifiers/phone")
async def link_phone_to_customer(
    customer_id: str,
    request: LinkPhoneRequest,
    session = Depends(get_session_dependency)
):
    """Link a phone number to a customer.

    Args:
        customer_id: Customer UUID
        request: Phone linking request
        session: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If customer not found or phone already linked
    """
    try:
        # Parse UUID
        try:
            customer_uuid = UUID(customer_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid customer ID format")

        # Get customer
        customer = await session.get(Customer, customer_uuid)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        # Link phone
        identification_service = CustomerIdentificationService(session)
        try:
            identifier = await identification_service.link_phone_to_customer(
                customer_id=customer_uuid,
                phone=request.phone,
                verified=request.verified
            )

            return {
                "status": "success",
                "message": f"Phone {request.phone} linked to customer",
                "identifier_id": str(identifier.id)
            }

        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking phone to customer: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to link phone to customer"
        )


@router.post("/customers/merge")
async def merge_customers(
    request: MergeCustomersRequest,
    session = Depends(get_session_dependency)
):
    """Merge two customer records.

    Moves all identifiers from secondary to primary customer.
    Note: Does not move conversations - that should be done separately.

    Args:
        request: Merge customers request
        session: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If customers not found or invalid
    """
    try:
        # Parse UUIDs
        try:
            primary_uuid = UUID(request.primary_customer_id)
            secondary_uuid = UUID(request.secondary_customer_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid customer ID format")

        # Merge customers
        identification_service = CustomerIdentificationService(session)
        try:
            primary = await identification_service.merge_customers(
                primary_customer_id=primary_uuid,
                secondary_customer_id=secondary_uuid
            )

            return {
                "status": "success",
                "message": "Customers merged successfully",
                "primary_customer_id": str(primary.id)
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging customers: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to merge customers"
        )
