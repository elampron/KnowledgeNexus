from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import uuid

# Import the core functions
from nexus.core import process_text_input_core, process_document_file_core, search_knowledge_core

app = FastAPI(title="KnowledgeNexus API")

class AddTextRequest(BaseModel):
    text: str
    instructions: Optional[str] = ""

class AddTextResponse(BaseModel):
    result: str

class SearchKnowledgeRequest(BaseModel):
    query_text: str
    node_type: Optional[str] = "ALL"
    k: Optional[int] = 10
    min_score: Optional[float] = 0.5

class SearchKnowledgeResponse(BaseModel):
    result: str

@app.post("/add_text", response_model=AddTextResponse)
def add_text(request: AddTextRequest):
    result = process_text_input_core(request.text, request.instructions)
    return AddTextResponse(result=result)

@app.post("/add_file", response_model=AddTextResponse)
def add_file(file: UploadFile = File(...)):
    temp_dir = os.path.join(os.getcwd(), "knowledge_nexus_files")
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(temp_dir, temp_filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    result = process_document_file_core(file_path)
    return AddTextResponse(result=result)

@app.post("/search_knowledge", response_model=SearchKnowledgeResponse)
def search_knowledge(request: SearchKnowledgeRequest):
    result = search_knowledge_core(
        request.query_text,
        request.node_type,
        request.k,
        request.min_score
    )
    return SearchKnowledgeResponse(result=result)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 