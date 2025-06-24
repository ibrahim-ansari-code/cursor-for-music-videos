"""Receipt parsing functionality for payment and expense receipts."""
import base64
import json
import logging
import os
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

import fitz  # PyMuPDF for PDF parsing
from openai.types.chat import (
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionMessageParam,
)

from Backend.utils.tax_utils import validate_and_process_tax_details
from .client import get_client
from .exceptions import PaymentReceiptAnalysisError
from .prompts import SYSTEM_PROMPT_EXPENSE_RECEIPT, SYSTEM_PROMPT_PAYMENT_RECEIPT
from .utils import _extract_json_from_markdown

# Configure logging
logger = logging.getLogger(__name__)


async def _analyze_receipt_content(
    file_content: bytes,
    filename: str,
    system_prompt: str,
    receipt_type: str
) -> Dict[str, Any]:
    """
    Analyzes a receipt file (PDF or image) and extracts structured details using Azure OpenAI.

    This is a generic base function for `analyze_payment_receipt_content` and 
    `analyze_expense_receipt_content`. It handles file processing, LLM interaction, 
    and response parsing.

    Returns:
        A dictionary containing extracted receipt fields.
    """
    azure_client = get_client()
    file_extension = os.path.splitext(filename)[1].lower()

    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
    ]
    raw_text_preview = ""

    if file_extension == '.pdf':
        try:
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            extracted_text = "".join(page.get_text("text")  # type: ignore[method-undefined]
                                     for page in pdf_document)
            pdf_document.close()
            logger.info("Extracted text from PDF for %s: %s",
                        receipt_type, filename)
            if not extracted_text.strip():
                logger.warning(
                    "No text could be extracted from PDF: %s", filename)
                raise ValueError(
                    f"No text could be extracted from PDF {receipt_type} receipt. Please ensure the PDF contains selectable text.")
            messages.append({"role": "user", "content": extracted_text})
            raw_text_preview = extracted_text[:200].replace('\n', ' ')
        except Exception as e:
            logger.exception(
                "Failed to extract text from PDF %s: %s", filename, e)
            raise ValueError(
                f"Could not process PDF file {filename}: {e}") from e
    elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp']:
        logger.info("Processing image file for GPT-4o vision (%s): %s",
                    receipt_type, filename)
        base64_image = base64.b64encode(file_content).decode('utf-8')
        image_url_content = f"data:image/{file_extension[1:]};base64,{base64_image}"

        user_message_content: List[ChatCompletionContentPartTextParam | ChatCompletionContentPartImageParam] = [
            {"type": "text", "text": f"Please extract the {receipt_type} details from this receipt image according to the JSON schema provided in the system prompt."},
            {"type": "image_url", "image_url": {
                "url": image_url_content, "detail": "auto"}},
        ]
        messages.append({"role": "user", "content": user_message_content})
        raw_text_preview = f"Image file processed: {filename}"
    else:
        logger.warning("Unsupported file type for LLM analysis: %s", filename)
        raise ValueError(
            f"Unsupported file type: {file_extension}. Please upload a PDF or common image format.")

    try:
        logger.info("Starting %s receipt analysis for: %s (type: %s)",
                    receipt_type, filename, file_extension)
        response = azure_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "Lease-Parser-GPT-4o"),
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
            timeout=30.0,
            response_format={"type": "json_object"},
        )

        llm_response_content = response.choices[0].message.content
        if llm_response_content is None:
            error_msg = f"No content in LLM response for {receipt_type} receipt: {filename}."
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug("LLM raw response for %s receipt (%s): %s...",
                     receipt_type, filename, llm_response_content[:200])

        try:
            parsed_data = json.loads(llm_response_content)
            logger.debug("Successfully parsed LLM JSON response directly.")
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse LLM response directly as JSON, trying markdown extraction.")
            try:
                json_str = _extract_json_from_markdown(llm_response_content)
                parsed_data = json.loads(json_str)
                logger.debug(
                    "Successfully parsed JSON after markdown extraction.")
            except (json.JSONDecodeError, ValueError) as json_err:
                error_msg = f"Failed to parse JSON from LLM response for {filename}: {json_err}"
                logger.exception(error_msg)
                logger.exception("LLM response content: %s",
                                 llm_response_content)
                raise ValueError(error_msg) from json_err

        parsed_data['raw_text_preview'] = raw_text_preview

        # Basic validation and defaulting
        parsed_data['payment_date'] = str(parsed_data.get('payment_date', ""))
        try:
            amount_str = str(parsed_data.get(
                'subtotal_amount', '0.0') or '0.0')
            parsed_data['subtotal_amount'] = Decimal(amount_str)
        except (InvalidOperation, TypeError):
            logger.warning("Could not parse subtotal_amount '%s' as Decimal. Defaulting to 0.0.",
                           parsed_data.get('subtotal_amount'))
            parsed_data['subtotal_amount'] = Decimal('0.0')
        try:
            amount_str = str(parsed_data.get('total_amount', '0.0') or '0.0')
            parsed_data['total_amount'] = Decimal(amount_str)
        except (InvalidOperation, TypeError):
            logger.warning(
                "Could not parse total_amount '%s' as Decimal. Defaulting to 0.0.", parsed_data.get('total_amount'))
            parsed_data['total_amount'] = Decimal('0.0')
        try:
            amount_str = str(parsed_data.get('total_tax_amount', '0.0') or '0.0')
            parsed_data['total_tax_amount'] = Decimal(amount_str)
        except (InvalidOperation, TypeError):
            logger.warning(
                "Could not parse total_tax_amount '%s' as Decimal. Defaulting to 0.0.", parsed_data.get('total_tax_amount'))
            parsed_data['total_tax_amount'] = Decimal('0.0')
        parsed_data['currency'] = str(parsed_data.get('currency', ""))
        parsed_data['payment_method'] = str(
            parsed_data.get('payment_method', ""))
        parsed_data['description_notes'] = str(
            parsed_data.get('description_notes', ""))

        # Validate tax_details if present (for expense receipts) using centralized tax utilities
        if 'tax_details' in parsed_data:
            tax_details_list = parsed_data.get('tax_details', [])
            validated_tax_details, total_tax_from_details = validate_and_process_tax_details(tax_details_list)
            parsed_data['tax_details'] = validated_tax_details
            
            # Ensure total_tax_amount is consistent with the sum of validated tax details
            if total_tax_from_details > 0:
                parsed_data['total_tax_amount'] = total_tax_from_details

    except json.JSONDecodeError as e:
        logger.exception(
            "Failed to parse LLM response as JSON for %s receipt %s: %s", receipt_type, filename, e)
        raise ValueError(
            f"Invalid JSON response from LLM for {receipt_type} receipt {filename}: {e}") from e
    except ValueError as e:
        logger.exception(
            "ValueError during %s receipt analysis for %s: %s", receipt_type, filename, e)
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error analyzing %s receipt %s: %s", receipt_type, filename, e)
        raise PaymentReceiptAnalysisError(
            f"Failed to analyze {receipt_type} receipt {filename}: {e}") from e

    logger.info("%s receipt analysis completed for: %s",
                receipt_type.capitalize(), filename)
    return parsed_data


async def analyze_payment_receipt_content(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Analyzes a payment receipt file (PDF or image) and extracts structured payment details 
    using Azure OpenAI GPT-4o with vision capabilities.

    This function is a wrapper around `_analyze_receipt_content` that provides the system 
    prompt and receipt type for payment receipts.

    Returns:
        A dictionary containing extracted payment receipt fields such as payment date, 
        subtotal, total amount, currency, payment method, description notes, and a raw 
        text preview.
    """
    return await _analyze_receipt_content(
        file_content=file_content,
        filename=filename,
        system_prompt=SYSTEM_PROMPT_PAYMENT_RECEIPT,
        receipt_type="payment"
    )


async def analyze_expense_receipt_content(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Analyzes an expense receipt file (PDF or image) and extracts structured data using 
    Azure OpenAI GPT-4o with vision capabilities.

    This function is a wrapper around `_analyze_receipt_content` that provides the system 
    prompt and receipt type for expense receipts.

    Raises:
        ValueError: If the file type is unsupported, text extraction fails, or the LLM 
            response cannot be parsed as valid JSON.
        PaymentReceiptAnalysisError: If an unexpected error occurs during analysis.
    """
    return await _analyze_receipt_content(
        file_content=file_content,
        filename=filename,
        system_prompt=SYSTEM_PROMPT_EXPENSE_RECEIPT,
        receipt_type="expense"
    )
