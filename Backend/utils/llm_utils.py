import os
import json
import re
from typing import Dict, Any
from openai import AzureOpenAI
from dotenv import load_dotenv, find_dotenv
import logging
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
def load_env_vars() -> None:
    """Load environment variables from .env file with improved error handling."""
    try:
        # Try to find .env file in current directory and parent directories
        env_path = find_dotenv()
        if env_path:
            logger.info(f"Loading environment variables from: {env_path}")
            load_dotenv(env_path)
        else:
            logger.warning("No .env file found in current or parent directories")
    except Exception as e:
        logger.error(f"Error loading .env file: {str(e)}")
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
        raise EnvironmentError(error_msg)
    
    # Log that all required variables are present (without logging sensitive values)
    logger.info("All required environment variables are present")
    logger.info(f"Azure OpenAI Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    logger.info(f"Azure OpenAI Deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT')}")
    logger.info(f"Azure OpenAI API Version: {os.getenv('AZURE_OPENAI_API_VERSION')}")

def get_azure_client() -> AzureOpenAI:
    """Initialize and return an Azure OpenAI client with validated credentials."""
    try:
        # Load environment variables
        load_env_vars()
        
        # Validate required variables
        validate_env_vars()
        
        # Initialize client
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        logger.info("Azure OpenAI client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
        raise

# Initialize client
try:
    client = get_azure_client()
except Exception as e:
    logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
    client = None

def analyze_lease_text(text: str) -> Dict[str, Any]:
    """
    Analyze lease text using Azure GPT-4o and extract key fields.
    
    Args:
        text: The lease text to analyze
        
    Returns:
        Dict containing extracted lease fields
        
    Raises:
        EnvironmentError: If required environment variables are missing
        ValueError: If no valid JSON is found in the response
        Exception: If the LLM analysis fails
    """
    if not client:
        raise EnvironmentError("Azure OpenAI client not initialized")
    
    system_prompt = """
    You are a lease analysis assistant. Analyze the provided lease text and return a single valid JSON object. Do not return any markdown, commentary, or explanation. Your response must **only** contain the JSON, wrapped in triple backticks (```json ... ```).

    Use empty strings `""` for any missing fields. All dates must be in ISO format (YYYY-MM-DD). The output must match this structure exactly:

    ```json
    {
      "core_identifiers": {
        "tenant_name": "",
        "landlord_name": "",
        "rental_address": "",
        "unit_number": "",
        "mailing_address": "",
        "lease_signed_date": "",
        "jurisdiction": ""
      },
      "term_details": {
        "lease_start_date": "",
        "lease_end_date": "",
        "lease_type": "",
        "auto_renewal": "",
        "notice_period": "",
        "vacate_clause": "",
        "renewal_terms": ""
      },
      "rent_payment": {
        "monthly_rent": "",  # IMPORTANT: Provide only the Year 1 base rent as a single float (e.g., 4400.00). No currency, ranges, or extra text.
        "rent_frequency": "",
        "due_date": "",
        "payment_methods": "",
        "late_fee": "",
        "rent_increase_policy": "",
        "deposit_usage_policy": ""
      },
      "deposits": {
        "security_deposit": "", # IMPORTANT: Provide a single float value only (e.g., 7500.00). No currency or extra text.
        "pet_deposit": "",
        "deposit_due_date": "",
        "interest_on_deposit": "",
        "return_terms": "",
        "trust_account_details": "",
        "additional_deposit": ""
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
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
        )
        
        content = response.choices[0].message.content
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
                logger.error(f"LLM response content: {content}")
                raise ValueError(error_msg)
                
            json_str = json_match.group(1)
            logger.debug("Extracted JSON from direct format")
        
        logger.debug(f"Extracted JSON: {json_str[:100]}...")  # Log first 100 chars of extracted JSON
        
        try:
            parsed_data = json.loads(json_str)
        except json.JSONDecodeError as json_err:
            logger.error(f"Extracted text is not valid JSON: {str(json_err)}")
            logger.error(f"Extracted text: {json_str}")
            raise ValueError(f"Failed to parse extracted JSON: {str(json_err)}")
        
        # Validate required fields in the nested structure
        required_fields = {
            'rent_payment': ['monthly_rent'],
            'term_details': ['lease_start_date', 'lease_end_date'],
            'core_identifiers': ['tenant_name']
        }
        
        # Fields that should be present but will be defaulted if missing
        optional_fields = {
            'deposits': {'security_deposit': '0'}
        }
        
        missing_fields = []
        for section, fields in required_fields.items():
            if section not in parsed_data:
                missing_fields.append(section)
                continue
            for field in fields:
                if field not in parsed_data[section] or not parsed_data[section][field]:
                    missing_fields.append(f"{section}.{field}")
        
        # Check and set default values for optional fields
        for section, field_defaults in optional_fields.items():
            if section not in parsed_data:
                parsed_data[section] = {}
            
            for field, default_value in field_defaults.items():
                if field not in parsed_data[section] or not parsed_data[section][field]:
                    logger.warning(f"Field {section}.{field} missing in LLM response, using default value: {default_value}")
                    parsed_data[section][field] = default_value
        
        if missing_fields:
            error_msg = f"Missing required fields in LLM response: {', '.join(missing_fields)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("Lease text analysis completed successfully")
        return parsed_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
        raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
    except ValueError as e:
        # Re-raise ValueError exceptions (like the ones we defined above)
        raise
    except Exception as e:
        logger.error(f"Failed to analyze lease text: {str(e)}")
        raise Exception(f"Failed to analyze lease text: {str(e)}")
