# cognitive/entity_extraction.py
import logging
from openai import OpenAI
from pydantic import ValidationError
from models.entities import ExtractedEntities

logger = logging.getLogger(__name__)

client = OpenAI()

def extract_entities_from_text(text: str, instructions: str = "") -> ExtractedEntities:
    """
    Extract entities from text using OpenAI's GPT model.
    Returns structured output using Pydantic models.
    """
    logger.info("Starting entity extraction.")
    
    system_prompt = """
    You are an entity extraction assistant. Extract named entities from the provided text.
    Focus on people, organizations, locations, and other significant entities.
    """
    
    user_content = text + "\n\n" + instructions if instructions else text
    
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format=ExtractedEntities,
            temperature=0.0
        )
        
        result = completion.choices[0].message.parsed
        logger.info("Entity extraction completed successfully.")
        return result
        
    except Exception as e:
        logger.error("OpenAI API error: %s", str(e))
        raise RuntimeError(f"OpenAI API error: {str(e)}") 