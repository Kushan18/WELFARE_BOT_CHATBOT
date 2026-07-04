import json
import os
import re
import logging
from groq import Groq

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def enrich_scheme_via_nlp(scheme: dict) -> dict:
    """
    Use Groq LLM to enrich the scheme with missing details.
    """
    if not groq_client:
        logger.warning("GROQ_API_KEY not set. Skipping NLP enrichment.")
        scheme['nlp_processed'] = True
        return scheme
        
    description = scheme.get('description', '')
    if not description or len(description.strip()) < 20:
        scheme['nlp_processed'] = True
        return scheme
        
    prompt = f"""
You are an expert welfare scheme analyzer. Based on the following scheme description, extract the missing details.
If a detail is not explicitly mentioned but can be reasonably inferred, provide it. If it cannot be inferred, return null.
Only return a JSON object with the requested keys. Do not include markdown codeblocks or extra text.

Scheme Name: {scheme.get('name', 'N/A')}
Scheme Description: {description}

Required fields to extract (if missing or null in original):
- eligibility: Detailed eligibility criteria (e.g. income limit, age limit, occupation)
- benefits: What the scheme provides
- age: Target age group (e.g. "18-60" or "60+")
- income_bracket: Income requirements if any
- deadline: Application deadline if any

Return JSON format:
{{
  "eligibility": "string or null",
  "benefits": "string or null",
  "age": "string or null",
  "income_bracket": "string or null",
  "deadline": "string or null"
}}
"""
    try:
        resp = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )
        content = resp.choices[0].message.content.strip()
        # Clean up any potential markdown
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        data = json.loads(content)
        
        # Merge back into scheme if original is missing/empty
        for key in ["eligibility", "benefits", "age", "income_bracket", "deadline"]:
            if not scheme.get(key) and data.get(key):
                scheme[key] = data[key]
                
    except Exception as e:
        logger.error(f"NLP enrichment failed: {e}")
        
    scheme['nlp_processed'] = True
    return scheme
