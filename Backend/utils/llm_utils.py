import openai
from typing import Dict, Any
import json

async def analyze_lease_text(text: str) -> Dict[str, Any]:
    """
    Analyze lease text using GPT-4 and extract key fields.
    
    Args:
        text (str): The extracted text from the lease PDF
        
    Returns:
        Dict[str, Any]: Extracted lease fields
    """
    system_prompt = """Extract key lease fields from the provided text. Return the data in JSON format with the following fields:
    - monthly_rent (float)
    - start_date (YYYY-MM-DD)
    - end_date (YYYY-MM-DD)
    - security_deposit (float)
    - tenant_name (string)
    - unit (string, optional)
    
    Only return the JSON object, no additional text."""
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1
        )
        
        # Extract the JSON response
        content = response.choices[0].message.content
        parsed_data = json.loads(content)
        
        return parsed_data
        
    except Exception as e:
        raise Exception(f"Failed to analyze lease text: {str(e)}")
