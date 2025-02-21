# cognitive/entity_extraction.py
import logging
from openai import OpenAI
from models.entities import ExtractedEntities

logger = logging.getLogger(__name__)

client = OpenAI()

def extract_entities_from_text(text: str, instructions: str = "") -> ExtractedEntities:
    """Extract entities, topics, and memories from the provided text using an LLM call.
    The LLM should return JSON with keys: 'entities', 'topics', and optionally 'memories'.
    Each entity should have at least 'name' and 'entity_type', and optionally 'aliases'.
    Each topic should have at least 'name', and optionally 'aliases' and 'notes'.
    """
    system_prompt = (
        "You are an expert text analysis assistant. Extract all relevant entities, topics, and memories from the text. "
        "For entities, identify their 'name', 'entity_type', and optionally 'aliases'. "
        "For topics, identify the main subjects discussed, and provide a 'name', and optionally 'aliases' and 'notes'. "
        "For memories, extract key snippets of knowledge as 'content' with a 'confidence' score. "
        
    )
    user_prompt = f"Text: {text}\nInstructions: {instructions}"
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            response_format=ExtractedEntities,
        )
        data = response.choices[0].message.parsed
        
        return data
    except Exception as e:
        logger.error("Failed to extract entities, topics, and memories: %s", e)
        return ExtractedEntities(entities=[], topics=[], memories=[]) 