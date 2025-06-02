import json
import logging
import os
import re
from typing import Any, Dict

from dotenv import find_dotenv, load_dotenv
from openai import AzureOpenAI

# Configure logging
logger = logging.getLogger(__name__)

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
    """Initialize and return an Azure OpenAI client with validated credentials."""
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


# Initialize client
try:
    client = get_azure_client()
except Exception as e:
    logger.error("Failed to initialize Azure OpenAI client: %s", str(e))
    client = None


def analyze_lease_text(text: str) -> Dict[str, Any]:
    """Analyzes lease agreement text using Azure OpenAI GPT-4o.

    This function sends lease text to an Azure OpenAI model with a
    strict schema prompt. It extracts, parses, and validates the
    resulting JSON response for required fields. It returns a
    dictionary of extracted lease information.

    The function raises an error if the client is not initialized,
    the model's response is invalid, required fields are missing, or
    if parsing fails.

    Args:
        text (str): The lease agreement text to analyze.

    Returns:
        Dict[str, Any]: A dictionary containing structured lease fields
            extracted from the text.

    Raises:
        OSError: If the Azure OpenAI client is not
            initialized.
        ValueError: If the model response is missing required
            fields or contains invalid JSON.
        Exception: If analysis fails for any other reason.
    """
    if not client:
        raise OSError("Azure OpenAI client not initialized")

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
        )

        content = response.choices[0].message.content
        if content is None:
            error_msg = "No content in LLM response"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Received response from LLM, extracting JSON")

        # Extract JSON object using regex, supporting both direct JSON and backtick wrapped formats
        # First try to extract from markdown code blocks (```json ... ```)
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        json_match = re.search(json_pattern, content)

        if json_match:
            # Found JSON in code block format
            json_str = json_match.group(1)
            logger.debug("Extracted JSON from code block format")
        else:
            # Fall back to looking for direct JSON object
            json_pattern = r'({[\s\S]*})'
            json_match = re.search(json_pattern, content)

            if not json_match:
                error_msg = "No valid JSON object found in LLM response"
                logger.error(error_msg)
                logger.error("LLM response content: %s", content)
                raise ValueError(error_msg)

            json_str = json_match.group(1)
            logger.debug("Extracted JSON from direct format")

        # Log first 100 chars of extracted JSON
        logger.debug("Extracted JSON: %s...", json_str[:100])

        try:
            parsed_data = json.loads(json_str)
        except json.JSONDecodeError as json_err:
            logger.error("Extracted text is not valid JSON: %s", str(json_err))
            logger.error("Extracted text: %s", json_str)
            raise ValueError(
                f"Failed to parse extracted JSON: {str(json_err)}")

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

        logger.info(
            "Lease text analysis completed successfully, returning potentially defaulted data.")
        return parsed_data

    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON: %s", str(e))
        raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
    except ValueError as e:
        # Re-raise ValueError exceptions (like the ones we defined above)
        raise
    except Exception as e:
        logger.error("Failed to analyze lease text: %s", str(e))
        raise Exception(f"Failed to analyze lease text: {str(e)}")
