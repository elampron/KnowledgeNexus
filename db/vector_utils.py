import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()


def get_embedding(text: str, model: str = "text-embedding-3-large") -> list:
    """
    Generate the vector embedding for given text using the specified OpenAI embedding model.
    
    Args:
        text (str): The input text.
        model (str): The embedding model to use.
    
    Returns:
        list: A list of floating point numbers representing the vector embedding.
    """
    # Clean and prepare the text
    cleaned_text = text.replace("\n", " ").strip()
    if not cleaned_text:
        logger.warning("Empty text provided for embedding generation")
        return None
        
    try:
        # The OpenAI API expects the input parameter to be a string
        response = client.embeddings.create(
            model=model,
            input=cleaned_text,
            encoding_format="float"
        )
        embedding = response.data[0].embedding
        logger.info("Generated embedding for text: %s...", cleaned_text[:50])
        return embedding
    except Exception as e:
        logger.error("Failed to generate embedding: %s", str(e))
        raise 