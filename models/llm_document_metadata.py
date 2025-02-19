from pydantic import BaseModel, Field

class DocumentLLMMetadata(BaseModel):
    content_type: str = Field(..., description="Classification category of the document, e.g., Email, Note, Documentation, Post, Image, or Other.")
    description: str = Field(..., description="Short description for the document, maximum 150 characters.")
    summary: str = Field(..., description="Brief summary of the document, maximum 300 characters.") 