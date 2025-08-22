"""Lease document parsing functionality."""
import json
import logging
import os
from typing import Any, Dict

from .client import get_client
from .prompts import SYSTEM_PROMPT_LEASE_ANALYSIS
from .utils import _extract_json_from_markdown

# Configure logging
logger = logging.getLogger(__name__)


async def analyze_lease_text(text: str) -> Dict[str, Any]:
    """
    Analyzes lease agreement text and extracts structured lease information using Azure OpenAI GPT-4o.

    Sends the provided lease text to the Azure OpenAI model with a strict schema prompt, parses 
    the JSON response, and ensures required fields are present, applying default values where 
    necessary. Returns a dictionary containing the extracted lease details. Raises an error if 
    the model response is invalid, required fields are missing, or parsing fails.

    Args:
        text: The lease agreement text to analyze.

    Returns:
        A dictionary with structured lease fields extracted from the text.

    Raises:
        OSError: If the Azure OpenAI client is not initialized.
        ValueError: If the model response is missing required fields or contains invalid JSON.
        Exception: If analysis fails for any other reason.
    """
    azure_client = get_client()  # Use a different name for the local client

    try:
        # Validate that we have a valid text input
        if not text or not text.strip():
            error_msg = "Input text is empty or None"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("Starting lease text analysis for %d characters", len(text))
        logger.debug("Text preview: %s...", text[:300])
        
        # Validate Azure OpenAI configuration
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "Lease-Parser-GPT-4o")
        if not deployment_name:
            logger.error("AZURE_OPENAI_DEPLOYMENT environment variable not set")
            raise ValueError("Azure OpenAI deployment name not configured")
        
        logger.info("Using Azure OpenAI deployment: %s", deployment_name)
        
        response = azure_client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_LEASE_ANALYSIS},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=4000,  # Larger limit for lease analysis
            timeout=45.0,  # Longer timeout for complex lease analysis
            response_format={"type": "json_object"}
        )
        
        logger.info("Azure OpenAI response received successfully")

        content = response.choices[0].message.content
        if content is None:
            error_msg = "LLM returned None response"
            logger.error(error_msg)
            logger.error("Full response object: %s", response)
            raise ValueError(error_msg)

        logger.info("Received response from LLM: %s characters", len(content))
        logger.debug("LLM response preview: %s...", content[:200])

        # Trust the direct JSON parse first since we use response_format={"type": "json_object"}
        try:
            parsed_data = json.loads(content)
            logger.debug("Successfully parsed LLM JSON response directly.")
        except json.JSONDecodeError as direct_json_err:
            # Rare case: Azure returns markdown despite the contract
            logger.warning(
                "Failed to parse LLM response directly as JSON (error: %s), trying markdown extraction.", 
                direct_json_err)
            json_str = ""
            try:
                json_str = _extract_json_from_markdown(content)
                
                parsed_data = json.loads(json_str)
                logger.debug("Successfully parsed JSON after markdown extraction.")
            except (json.JSONDecodeError, ValueError) as json_err:
                error_msg = f"Failed to parse JSON from LLM response: {json_err}"
                logger.exception(error_msg)
                logger.error("LLM response content: %s", content)
                logger.error("Extracted JSON string: %s", json_str)                
                # Provide a more user-friendly error message
                user_friendly_msg = (
                    "The lease document could not be processed. This may be due to:\n"
                    "The document format is not supported\n"
                    "The document content is unclear or corrupted\n"
                    "Temporary service issues\n\n"
                    "Please try uploading a different document or try again later."
                )
                raise ValueError(user_friendly_msg) from json_err

        # Validate required fields in the nested structure
        # These fields are expected by LeaseAnalysisResponse but we will allow them to be missing
        # and default them if not found, rather than raising an error.
        fields_to_default: dict[str, dict[str, Any]] = {
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
                if not parsed_data[section].get(field) and parsed_data[section].get(field) != 0:
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
        # Preserve original exception context for debugging
        raise RuntimeError(f"Failed to analyze lease text: {str(e)}") from e
    else:
        logger.info(
            "Lease text analysis completed successfully, returning potentially defaulted data.")
        return parsed_data
