from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class Document(BaseModel):
    """Pydantic model for document metadata and content."""
    id: str
    file_name: str
    file_type: str
    file_size: int
    upload_date: datetime
    original_path: str
    markdown_path: str
    conversion_status: str
    error_message: Optional[str] = None
    entities: List[str] = []

    class Config:
        from_attributes = True  # For ORM compatibility 