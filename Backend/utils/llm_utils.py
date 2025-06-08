import json
import logging
import os
import regex as re
from typing import Any, Dict, List
import base64  # Added for image processing

import fitz  # Added for PDF parsing
from dotenv import find_dotenv, load_dotenv
from openai import AzureOpenAI
# Import specific types for messages from the OpenAI SDK
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionContentPartImageParam
)

# Configure logging
logger = logging.getLogger(__name__)

# Custom Exception


class PaymentReceiptAnalysisError(Exception):
    """Custom exception for errors during payment receipt analysis."""

# Load environment variables from .env file
def load_env_vars() -> None:
    """Load environment variables from .env file with improved error handling."""
    try:
        # Try to find .env file in current directory and parent directories
        env_path = find_dotenv()
        if env_path:
            logger.info("Loading environment variables from: %s", env_path)
            load_dotenv(env_path)
        else:
            logger.warning(
                "No .env file found in current or parent directories")
    except Exception as e:
        logger.error("Error loading .env file: %s", str(e))
        raise


# Required environment variables
REQUIRED_ENV_VARS = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION"
]


def validate_env_vars() -> None:
    """Validate that all required environment variables are set."""
    missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise OSError(error_msg)

    # Log that all required variables are present (without logging sensitive values)
    logger.info("All required environment variables are present")
    logger.info("Azure OpenAI Endpoint: %s",
                os.getenv('AZURE_OPENAI_ENDPOINT'))
    logger.info("Azure OpenAI Deployment: %s",
                os.getenv('AZURE_OPENAI_DEPLOYMENT'))
    logger.info("Azure OpenAI API Version: %s",
                os.getenv('AZURE_OPENAI_API_VERSION'))


def get_azure_client() -> AzureOpenAI:
    """
    Initializes and returns an Azure OpenAI client using validated environment credentials.
    
    Loads and validates required environment variables before creating the client. Raises an
    OSError if any required variable is missing, or propagates other exceptions on failure.
    """
    try:
        # Load environment variables
        load_env_vars()

        # Validate required variables
        validate_env_vars()

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

        if not api_key:
            error_msg = "AZURE_OPENAI_API_KEY is not set."
            logger.error(error_msg)
            raise OSError(error_msg)
        if not api_version:
            error_msg = "AZURE_OPENAI_API_VERSION is not set."
            logger.error(error_msg)
            raise OSError(error_msg)
        if not azure_endpoint:
            error_msg = "AZURE_OPENAI_ENDPOINT is not set."
            logger.error(error_msg)
            raise OSError(error_msg)

        # Initialize client
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint
        )

        logger.info("Azure OpenAI client initialized successfully")
        return client
    except Exception as e:
        logger.error("Failed to initialize Azure OpenAI client: %s", str(e))
        raise


# Global client variable for lazy initialization
client = None


def get_client() -> AzureOpenAI:
    """
    Returns a lazily initialized Azure OpenAI client instance.
    
    Initializes the client on first use to avoid import-time errors from missing environment variables. Subsequent calls return the cached client. Raises an exception if initialization fails.
    """
    global client
    if client is None:
        try:
            client = get_azure_client()
        except Exception as e:
            logger.error("Failed to initialize Azure OpenAI client: %s", str(e))
            raise
    return client


SYSTEM_PROMPT_PAYMENT_RECEIPT = """
You are an intelligent assistant specialized in extracting information from payment receipts (which could be provided as text extracted from a PDF, or as an image).
Analyze the provided content and return a single valid JSON object.
Do not return any markdown, commentary, or explanation. Your response must **only** contain the JSON, wrapped in triple backticks (```json ... ```).

Use empty strings `""` for any missing fields.
The `payment_date` must be in ISO format (YYYY-MM-DD). If the year is missing, assume the current year. If the full date cannot be determined, use an empty string.
The `subtotal_amount` (amount before taxes) must be a float (e.g., 100.00). If not found or not applicable, use 0.0 or try to calculate if total and taxes are obvious.
The `total_amount` (final amount paid, including all taxes) must be a float (e.g., 112.00). If not found, use 0.0.
The `currency` should be the currency code (e.g., USD, CAD, EUR) if identifiable, otherwise an empty string.
The `payment_method` could be 'Cash', 'Credit Card', 'Debit Card', 'Bank Transfer', 'Check', or other common methods. If not clear, use 'Other' or an empty string.
The `description_notes` should capture any line items, notes, or memo relevant to the payment.

The output must match this structure exactly:

```json
{
  "payment_date": "<string, YYYY-MM-DD format or empty string>",
  "subtotal_amount": "<float, e.g., 70.00>",
  "total_amount": "<float, e.g., 75.00>",
  "currency": "<string, e.g., USD, CAD>",
  "payment_method": "<string, e.g., Credit Card>",
  "description_notes": "<string, relevant notes or line items>",
  "raw_text_preview": "<string, first 200 characters of the extracted text if applicable, or a note about image processing>"
}
```

Be strict. Never include trailing commas, extra markdown, or introductory text. Just the JSON block wrapped in triple backticks.
"""

SYSTEM_PROMPT_EXPENSE_RECEIPT = """
You are an intelligent assistant specialized in extracting information from expense receipts (which could be provided as text extracted from a PDF, or as an image).
Analyze the provided content and return a single valid JSON object.
Do not return any markdown, commentary, or explanation. Your response must **only** contain the JSON, wrapped in triple backticks (```json ... ```).

Use empty strings `""` for any missing fields.
The `payment_date` (expense date) must be in ISO format (YYYY-MM-DD). If the year is missing, assume the current year. If the full date cannot be determined, use an empty string.
The `subtotal_amount` (amount before taxes) must be a float (e.g., 100.00). If not found, try to calculate by subtracting taxes from total.
The `total_amount` (final amount including all taxes and fees) must be a float (e.g., 112.00). If not found, use 0.0.
The `currency` should be the currency code (e.g., USD, CAD, EUR) if identifiable, otherwise an empty string.
The `payment_method` could be 'Cash', 'Credit Card', 'Debit Card', 'Bank Transfer', 'Check', or other common methods. If not clear, use 'Other' or an empty string.
The `description_notes` should capture the vendor name, expense category, line items, or any relevant notes about the expense.

Focus on extracting expense-specific information like vendor details, expense categories (maintenance, utilities, supplies, etc.), and tax breakdowns.

The output must match this structure exactly:

```json
{
  "payment_date": "<string, YYYY-MM-DD format or empty string>",
  "subtotal_amount": "<float, e.g., 70.00>",
  "total_amount": "<float, e.g., 75.00>",
  "currency": "<string, e.g., USD, CAD>",
  "payment_method": "<string, e.g., Credit Card>",
  "description_notes": "<string, vendor name, category, line items, or notes>",
  "raw_text_preview": "<string, first 200 characters of the extracted text if applicable, or a note about image processing>"
}
```

Be strict. Never include trailing commas, extra markdown, or introductory text. Just the JSON block wrapped in triple backticks.
"""


def _extract_json_from_markdown(content: str) -> str:
    """
    Extracts a JSON string from content that may be wrapped in markdown code blocks.
    
    Attempts to find and return JSON enclosed in triple backticks (optionally labeled as `json`) or as a direct JSON object within the content. If no such pattern is found, returns the stripped original content.
    """
    # Try to extract from markdown code blocks first
    json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    json_match = re.search(json_pattern, content)

    if json_match:
        return json_match.group(1).strip()

    # Fallback: try to extract JSON object directly
    json_pattern_direct = r'({(?:[^{}]|(?R))*})'
    json_match_direct = re.search(json_pattern_direct, content)

    if json_match_direct:
        return json_match_direct.group(1).strip()

    # If no patterns match, return the content as-is for final attempt
    return content.strip()


def analyze_payment_receipt_content(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Analyzes a payment receipt file (PDF or image) and extracts structured payment details using Azure OpenAI GPT-4o with vision capabilities.
    
    For PDF files, extracts text content and submits it to the model. For image files, encodes the image as a base64 data URL for vision analysis. The function parses the model's JSON response, validates and coerces key fields, and includes a preview of the processed content. Raises a ValueError for unsupported file types, extraction failures, or invalid responses, and a PaymentReceiptAnalysisError for unexpected errors.
    
    Returns:
        A dictionary containing extracted payment receipt fields such as payment date, subtotal, total amount, currency, payment method, description notes, and a raw text preview.
    """
    client = get_client()  # Lazy load the client

    file_extension = os.path.splitext(filename)[1].lower()

    # Explicitly type the messages list
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT_PAYMENT_RECEIPT},
    ]
    raw_text_preview = ""

    if file_extension == '.pdf':
        try:
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            extracted_text = "".join(page.get_text("text")  # type: ignore[attr-defined]
                                     for page in pdf_document)
            pdf_document.close()
            logger.info("Extracted text from PDF: %s", filename)
            if not extracted_text.strip():
                logger.warning(
                    "No text could be extracted from PDF: %s", filename)
                raise ValueError(
                    "No text could be extracted from PDF receipt. Please ensure the PDF contains selectable text.")
            messages.append({"role": "user", "content": extracted_text})
            raw_text_preview = extracted_text[:200].replace('\n', ' ')
        except Exception as e:
            logger.exception(
                "Failed to extract text from PDF %s: %s", filename, e)
            raise ValueError(
                f"Could not process PDF file {filename}: {e}") from e
    elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp']:
        logger.info("Processing image file for GPT-4o vision: %s", filename)
        base64_image = base64.b64encode(file_content).decode('utf-8')
        image_url_content = f"data:image/{file_extension[1:]};base64,{base64_image}"

        # This user message structure conforms to ChatCompletionUserMessageParam (with list content)
        user_message_content: List[ChatCompletionContentPartTextParam | ChatCompletionContentPartImageParam] = [
            {"type": "text", "text": "Please extract the payment details from this receipt image according to the JSON schema provided in the system prompt."},
            {
                "type": "image_url",
                "image_url": {"url": image_url_content, "detail": "auto"},
            },
        ]
        messages.append({"role": "user", "content": user_message_content})
        raw_text_preview = f"Image file processed: {filename}"
    else:
        logger.warning("Unsupported file type for LLM analysis: %s", filename)
        raise ValueError(
            f"Unsupported file type: {file_extension}. Please upload a PDF or common image format.")

    try:
        logger.info(
            "Starting payment receipt analysis for: %s (type: %s)", filename, file_extension)
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            messages=messages,
            temperature=0.1,
            max_tokens=2000,  # Limit response size for efficiency
            timeout=30.0,  # 30 second timeout to prevent blocking
            response_format={"type": "json_object"},
        )

        llm_response_content = response.choices[0].message.content
        if llm_response_content is None:
            error_msg = f"No content in LLM response for payment receipt: {filename}."
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug(
            "LLM raw response for receipt (%s): %s...", filename, llm_response_content[:200])

        # Trust the direct JSON parse first since we use response_format={"type": "json_object"}
        try:
            parsed_data = json.loads(llm_response_content)
            logger.debug("Successfully parsed LLM JSON response directly.")
        except json.JSONDecodeError:
            # Rare case: Azure returns markdown despite the contract
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

        # Basic validation and defaulting to ensure correct types
        parsed_data['payment_date'] = str(parsed_data.get('payment_date', ""))
        try:
            parsed_data['subtotal_amount'] = float(
                parsed_data.get('subtotal_amount', 0.0) or 0.0)
        except (ValueError, TypeError):
            logger.warning(
                "Could not parse subtotal_amount '%s' as float. Defaulting to 0.0.", parsed_data.get('subtotal_amount'))
            parsed_data['subtotal_amount'] = 0.0
        try:
            parsed_data['total_amount'] = float(
                parsed_data.get('total_amount', 0.0) or 0.0)
        except (ValueError, TypeError):
            logger.warning(
                "Could not parse total_amount '%s' as float. Defaulting to 0.0.", parsed_data.get('total_amount'))
            parsed_data['total_amount'] = 0.0
        parsed_data['currency'] = str(parsed_data.get('currency', ""))
        parsed_data['payment_method'] = str(
            parsed_data.get('payment_method', ""))
        parsed_data['description_notes'] = str(
            parsed_data.get('description_notes', ""))

    except json.JSONDecodeError as e:
        logger.exception(
            "Failed to parse LLM response as JSON for payment receipt %s: %s", filename, e)
        raise ValueError(
            f"Invalid JSON response from LLM for payment receipt {filename}: {e}") from e
    except ValueError as e:
        logger.exception(
            "ValueError during payment receipt analysis for %s: %s", filename, e)
        raise  # Re-raise the specific ValueError, it might be from a previous step
    except Exception as e:  # Catch any other unexpected exception
        logger.exception(
            "Unexpected error analyzing payment receipt %s: %s", filename, e)
        raise PaymentReceiptAnalysisError(
            f"Failed to analyze payment receipt {filename}: {e}") from e
    else:
        logger.info("Payment receipt analysis completed for: %s", filename)
        return parsed_data


def analyze_expense_receipt_content(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Analyzes an expense receipt file (PDF or image) and extracts structured data using Azure OpenAI GPT-4o with vision capabilities.
    
    For PDF files, extracts text content and analyzes it. For image files, encodes the image as base64 and submits it for analysis. Returns a dictionary containing extracted fields such as payment date, subtotal, total amount, currency, payment method, description notes, and a preview of the raw text or image processed.
    
    Raises:
        ValueError: If the file type is unsupported, text extraction fails, or the LLM response cannot be parsed as valid JSON.
        PaymentReceiptAnalysisError: If an unexpected error occurs during analysis.
    """
    client = get_client()  # Lazy load the client

    file_extension = os.path.splitext(filename)[1].lower()

    # Explicitly type the messages list
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT_EXPENSE_RECEIPT},
    ]
    raw_text_preview = ""

    if file_extension == '.pdf':
        try:
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            extracted_text = "".join(page.get_text("text")  # type: ignore[attr-defined]
                                     for page in pdf_document)
            pdf_document.close()
            logger.info("Extracted text from PDF for expense: %s", filename)
            if not extracted_text.strip():
                logger.warning(
                    "No text could be extracted from PDF: %s", filename)
                raise ValueError(
                    "No text could be extracted from PDF expense receipt. Please ensure the PDF contains selectable text.")
            messages.append({"role": "user", "content": extracted_text})
            raw_text_preview = extracted_text[:200].replace('\n', ' ')
        except Exception as e:
            logger.exception(
                "Failed to extract text from PDF %s: %s", filename, e)
            raise ValueError(
                f"Could not process PDF file {filename}: {e}") from e
    elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp']:
        logger.info("Processing image file for expense analysis: %s", filename)
        base64_image = base64.b64encode(file_content).decode('utf-8')
        image_url_content = f"data:image/{file_extension[1:]};base64,{base64_image}"

        # This user message structure conforms to ChatCompletionUserMessageParam (with list content)
        user_message_content: List[ChatCompletionContentPartTextParam | ChatCompletionContentPartImageParam] = [
            {"type": "text", "text": "Please extract the expense details from this receipt image according to the JSON schema provided in the system prompt."},
            {
                "type": "image_url",
                "image_url": {"url": image_url_content, "detail": "auto"},
            },
        ]
        messages.append({"role": "user", "content": user_message_content})
        raw_text_preview = f"Image file processed: {filename}"
    else:
        logger.warning(
            "Unsupported file type for expense LLM analysis: %s", filename)
        raise ValueError(
            f"Unsupported file type: {file_extension}. Please upload a PDF or common image format.")

    try:
        logger.info(
            "Starting expense receipt analysis for: %s (type: %s)", filename, file_extension)
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            messages=messages,
            temperature=0.1,
            max_tokens=2000,  # Limit response size for efficiency
            timeout=30.0,  # 30 second timeout to prevent blocking
            response_format={"type": "json_object"},
        )

        llm_response_content = response.choices[0].message.content
        if llm_response_content is None:
            error_msg = f"No content in LLM response for expense receipt: {filename}."
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug(
            "LLM raw response for expense receipt (%s): %s...", filename, llm_response_content[:200])

        # Trust the direct JSON parse first since we use response_format={"type": "json_object"}
        try:
            parsed_data = json.loads(llm_response_content)
            logger.debug("Successfully parsed LLM JSON response directly.")
        except json.JSONDecodeError:
            # Rare case: Azure returns markdown despite the contract
            logger.warning(
                "Failed to parse LLM response directly as JSON, trying markdown extraction.")
            try:
                json_str = _extract_json_from_markdown(llm_response_content)
                parsed_data = json.loads(json_str)
                logger.debug(
                    "Successfully parsed JSON after markdown extraction.")
            except (json.JSONDecodeError, ValueError) as json_err:
                error_msg = f"Failed to parse JSON from LLM response for expense {filename}: {json_err}"
                logger.exception(error_msg)
                logger.exception("LLM response content: %s",
                                 llm_response_content)
                raise ValueError(error_msg) from json_err

        parsed_data['raw_text_preview'] = raw_text_preview

        # Basic validation and defaulting to ensure correct types
        parsed_data['payment_date'] = str(parsed_data.get('payment_date', ""))
        try:
            parsed_data['subtotal_amount'] = float(
                parsed_data.get('subtotal_amount', 0.0) or 0.0)
        except (ValueError, TypeError):
            logger.warning(
                "Could not parse subtotal_amount '%s' as float. Defaulting to 0.0.", parsed_data.get('subtotal_amount'))
            parsed_data['subtotal_amount'] = 0.0
        try:
            parsed_data['total_amount'] = float(
                parsed_data.get('total_amount', 0.0) or 0.0)
        except (ValueError, TypeError):
            logger.warning(
                "Could not parse total_amount '%s' as float. Defaulting to 0.0.", parsed_data.get('total_amount'))
            parsed_data['total_amount'] = 0.0
        parsed_data['currency'] = str(parsed_data.get('currency', ""))
        parsed_data['payment_method'] = str(
            parsed_data.get('payment_method', ""))
        parsed_data['description_notes'] = str(
            parsed_data.get('description_notes', ""))

    except json.JSONDecodeError as e:
        logger.exception(
            "Failed to parse LLM response as JSON for expense receipt %s: %s", filename, e)
        raise ValueError(
            f"Invalid JSON response from LLM for expense receipt {filename}: {e}") from e
    except ValueError as e:
        logger.exception(
            "ValueError during expense receipt analysis for %s: %s", filename, e)
        raise  # Re-raise the specific ValueError, it might be from a previous step
    except Exception as e:  # Catch any other unexpected exception
        logger.exception(
            "Unexpected error analyzing expense receipt %s: %s", filename, e)
        raise PaymentReceiptAnalysisError(
            f"Failed to analyze expense receipt {filename}: {e}") from e
    else:
        logger.info("Expense receipt analysis completed for: %s", filename)
        return parsed_data


def analyze_lease_text(text: str) -> Dict[str, Any]:
    """
    Analyzes lease agreement text and extracts structured lease information using Azure OpenAI GPT-4o.
    
    Sends the provided lease text to the Azure OpenAI model with a strict schema prompt, parses the JSON response, and ensures required fields are present, applying default values where necessary. Returns a dictionary containing the extracted lease details. Raises an error if the model response is invalid, required fields are missing, or parsing fails.
    
    Args:
        text: The lease agreement text to analyze.
    
    Returns:
        A dictionary with structured lease fields extracted from the text.
    
    Raises:
        OSError: If the Azure OpenAI client is not initialized.
        ValueError: If the model response is missing required fields or contains invalid JSON.
        Exception: If analysis fails for any other reason.
    """
    client = get_client()  # Lazy load the client

    system_prompt = """
    You are a lease analysis assistant. Analyze the provided lease text and return a single valid JSON object. Do not return any markdown, commentary, or explanation. Your response must **only** contain the JSON, wrapped in triple backticks (```json ... ```).

    Use empty strings `""` for any missing fields. All dates must be in ISO format (YYYY-MM-DD). The output must match this structure exactly:

    ```json
    {
      "core_identifiers": {
        "tenant_name": "<string, full name of the primary tenant>",
        "landlord_name": "<string, full name of the landlord or management company>",
        "rental_address": "<string, full street address of the rental property>",
        "unit_number": "<string, unit or apartment number, if applicable, otherwise empty string>",
        "mailing_address": "<string, tenant mailing address if different from rental_address, otherwise empty string>",
        "lease_signed_date": "<string, YYYY-MM-DD format>",
        "jurisdiction": "<string, e.g., State, Province, or City where property is located>"
      },
      "term_details": {
        "lease_start_date": "<string, YYYY-MM-DD format, mandatory>",
        "lease_end_date": "<string, YYYY-MM-DD format, mandatory>",
        "lease_type": "<string, e.g., Fixed-term, Month-to-month>",
        "auto_renewal": "<string, e.g., Yes, No, or specific conditions>",
        "notice_period": "<string, e.g., 30 days, 60 days for termination or renewal>",
        "vacate_clause": "<string, conditions for early termination by tenant or landlord>",
        "renewal_terms": "<string, specific terms for lease renewal, if any>"
      },
      "rent_payment": {
        "monthly_rent": "<float, base monthly rent amount, e.g., 1500.00, mandatory>",
        "rent_frequency": "<string, e.g., Monthly, Weekly>",
        "due_date": "<string, e.g., 1st of the month, day of the month rent is due>",
        "payment_methods": "<string, accepted payment methods, e.g., Check, Online Portal, Bank Transfer>",
        "late_fee": "<string, details of late fee policy, e.g., $50 after 5 days>",
        "rent_increase_policy": "<string, terms for rent increases, if any>",
        "deposit_usage_policy": "<string, how security deposit can be used or applied to rent>"
      },
      "deposits": {
        "security_deposit": "<float, amount of security deposit, e.g., 1500.00, mandatory if mentioned, otherwise 0.0>",
        "pet_deposit": "<float, amount of pet deposit, if any, e.g., 250.00, otherwise empty string or 0.0>",
        "deposit_due_date": "<string, YYYY-MM-DD format, when deposits are due>",
        "interest_on_deposit": "<string, policy on interest paid on deposit, if any>",
        "return_terms": "<string, conditions for deposit return, e.g., within 30 days of move-out>",
        "trust_account_details": "<string, details if deposit is held in a trust account>",
        "additional_deposit": "<string, any other deposits required, e.g., key deposit>"
      },
      "inclusions_utilities": {
        "included_utilities": "",
        "appliances": "",
        "furniture_status": "",
        "parking": "",
        "storage": "",
        "laundry": ""
      },
      "rules_policies": {
        "pet_policy": "",
        "smoking_policy": "",
        "sublet_policy": "",
        "occupants": "",
        "quiet_enjoyment_clause": "",
        "guest_restrictions": "",
        "modification_rules": ""
      },
      "responsibilities": {
        "landlord_responsibilities": "",
        "tenant_responsibilities": "",
        "emergency_repairs": "",
        "regular_maintenance": ""
      },
      "entry_inspection": {
        "entry_conditions": "",
        "notice_for_entry": "",
        "inspection_reports": "",
        "inspection_frequency": ""
      },
      "dispute_resolution": {
        "jurisdiction_body": "",
        "dispute_process": "",
        "arbitration_right": ""
      },
      "signatures": {
        "tenant_signatures": "",
        "landlord_signatures": "",
        "witness_signature": "",
        "signature_dates": ""
      },
      "additional_terms": {
        "custom_clauses": "",
        "addendum_attached": "",
        "addendum_pages": "",
        "special_conditions": ""
      },
      "metadata": {
        "document_language": "",
        "currency": "",
        "lease_type_category": "",
        "governing_law": "",
        "form_version": ""
      }
    }

    Be strict. Never include trailing commas, extra markdown, or introductory text. Just the JSON block wrapped in triple backticks.
    """

    try:
        logger.info("Starting lease text analysis")
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=4000,  # Larger limit for lease analysis
            timeout=45.0,  # Longer timeout for complex lease analysis
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        if content is None:
            error_msg = "No content in LLM response"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Received response from LLM, extracting JSON")

        # Trust the direct JSON parse first since we use response_format={"type": "json_object"}
        try:
            parsed_data = json.loads(content)
            logger.debug("Successfully parsed LLM JSON response directly.")
        except json.JSONDecodeError:
            # Rare case: Azure returns markdown despite the contract
            logger.warning(
                "Failed to parse LLM response directly as JSON, trying markdown extraction.")
            try:
                json_str = _extract_json_from_markdown(content)
                parsed_data = json.loads(json_str)
                logger.debug(
                    "Successfully parsed JSON after markdown extraction.")
            except (json.JSONDecodeError, ValueError) as json_err:
                error_msg = f"Failed to parse JSON from LLM response: {json_err}"
                logger.exception(error_msg)
                logger.exception("LLM response content: %s", content)
                raise ValueError(error_msg) from json_err

        # Validate required fields in the nested structure
        # These fields are expected by LeaseAnalysisResponse but we will allow them to be missing
        # and default them if not found, rather than raising an error.
        fields_to_default = {
            # Default to 0.0 if not found
            'rent_payment': {'monthly_rent': 0.0},
            # Default to empty string
            'term_details': {'lease_start_date': '', 'lease_end_date': ''},
            # Default to empty string
            'core_identifiers': {'tenant_name': '', 'unit_number': ''},
            # Default to 0.0 if not found
            'deposits': {'security_deposit': 0.0}
        }

        for section, field_defaults in fields_to_default.items():
            if section not in parsed_data or not isinstance(parsed_data[section], dict):
                logger.warning(
                    "Section '%s' missing or not a dict in LLM response, creating with defaults.", section)
                parsed_data[section] = {}

            for field, default_value in field_defaults.items():
                if field not in parsed_data[section] or parsed_data[section].get(field) == '' or parsed_data[section].get(field) is None:
                    logger.warning(
                        "Field %s.%s missing or empty in LLM response, using default value: %s", section, field, default_value)
                    parsed_data[section][field] = default_value

        # Ensure core_identifiers.unit_number (aliased as 'unit' in LeaseAnalysisResponse) is present
        if 'core_identifiers' in parsed_data and 'unit_number' not in parsed_data['core_identifiers']:
            logger.warning(
                "Field core_identifiers.unit_number missing in LLM response, defaulting to empty string.")
            parsed_data['core_identifiers']['unit_number'] = ''

    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON: %s",
                     str(e), exc_info=True)
        raise ValueError(f"Invalid JSON response from LLM: {str(e)}") from e
    except ValueError as e:
        # Re-raise ValueError exceptions (like the ones we defined above)
        raise
    except Exception as e:
        logger.error("Failed to analyze lease text: %s", str(e), exc_info=True)
        raise Exception(f"Failed to analyze lease text: {str(e)}") from e
    else:
        logger.info(
            "Lease text analysis completed successfully, returning potentially defaulted data.")
        return parsed_data
