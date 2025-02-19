from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class Document(BaseModel):
    """Pydantic model for document metadata and content."""
    id: str = Field(..., description="Unique identifier for the document.")
    file_name: str = Field(..., description="Original name of the file.")
    file_type: str = Field(..., description="File extension or type of the document.")
    file_size: int = Field(..., description="Size of the document in bytes.")
    upload_date: datetime = Field(..., description="Datetime when the document was uploaded or processed.")
    original_path: str = Field(..., description="File system path where the original document is stored.")
    markdown_path: str = Field(..., description="File system path where the markdown version is stored.")
    conversion_status: str = Field(..., description="Status of the document conversion process.")
    error_message: Optional[str] = Field(None, description="Error message during processing, if any.")
    entities: List[str] = Field(default_factory=list, description="List of entity names extracted from the document.")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding of the document content.")
    description: str = Field("", description="Short description derived from the document content.")
    content_type: str = Field("", description="Content type determined from the document.")
    summary: str = Field("", description="generate a Brief summary of the document content.")

    class Config:
        from_attributes = True  # For ORM compatibility 