"""Shared utilities for LLM operations."""
import re


def _extract_json_from_markdown(content: str) -> str:
    """
    Extracts a JSON string from content that may be wrapped in markdown code blocks.

    Attempts to find and return JSON enclosed in triple backticks (optionally labeled as `json`) 
    or as a direct JSON object within the content. If no such pattern is found, returns the 
    stripped original content.
    """
    # Try to extract from markdown code blocks first
    json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    json_match = re.search(json_pattern, content)

    if json_match:
        return json_match.group(1).strip()

    # Fallback: try to extract JSON object directly using a simpler pattern
    # Note: This is a simplified pattern that works with Python's re module
    json_pattern_direct = r'(\{[^{}]*\})'
    json_match_direct = re.search(json_pattern_direct, content)

    if json_match_direct:
        return json_match_direct.group(1).strip()

    # If no patterns match, return the content as-is for final attempt
    return content.strip()
