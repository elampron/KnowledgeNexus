# cognitive/entity_extraction.py
import json
import logging
from openai import OpenAI
from models.entities import ExtractedEntities, EntitySchema
from models.topic import TopicSchema

logger = logging.getLogger(__name__)

client = OpenAI()

def extract_entities_from_text(text: str, instructions: str = "") -> ExtractedEntities:
    """Extract entities and topics from the provided text using an LLM call.
    The LLM should return JSON with two keys: 'entities' and 'topics'.
    Each entity should have at least 'name' and 'entity_type', and optionally 'aliases'.
    Each topic should have at least 'name', and optionally 'aliases' and 'notes'.
    """
    system_prompt = (
        "You are an expert text analysis assistant. Extract all relevant entities and topics from the text. "
        "For entities, identify their 'name', 'entity_type', and optionally 'aliases'. "
        "For topics, identify the main subjects discussed, and provide a 'name', and optionally 'aliases' and 'notes'. "
        "Return the result as JSON with two keys: 'entities' and 'topics'."
    )
    user_prompt = f"Text: {text}\nInstructions: {instructions}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=500
        )
        output_text = response.choices[0].message.content
        logger.debug("Raw LLM output: %s", output_text)
        try:
            import re
            match = re.search(r'\{.*\}', output_text, re.DOTALL)
            if match:
                candidate = match.group(0)
                # Remove any trailing commas before } or ] that may cause JSONDecodeError
                candidate = re.sub(r',\s*([\]}])', r'\1', candidate)
                data = json.loads(candidate)
            else:
                logger.error("Failed to parse JSON from LLM output: %s", output_text)
                raise json.JSONDecodeError("No JSON found in the output")
        except json.JSONDecodeError as json_err:
            logger.error("Failed to parse JSON from LLM output: %s", json_err)
            raise json_err
        entities = [EntitySchema(**ent) for ent in data.get("entities", [])]
        topics = [TopicSchema(**top) for top in data.get("topics", [])]
        return ExtractedEntities(entities=entities, topics=topics)
    except Exception as e:
        logger.error("Failed to extract entities and topics: %s", e)
        return ExtractedEntities(entities=[], topics=[]) 