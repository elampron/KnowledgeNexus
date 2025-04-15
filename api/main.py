from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import uvicorn

# Import the process_text_input function from gradio_app.py
from gradio_app import process_text_input

app = FastAPI(title="KnowledgeNexus API")

class AddTextRequest(BaseModel):
    text: str
    instructions: Optional[str] = ""

class AddTextResponse(BaseModel):
    result: str

@app.post("/add_text", response_model=AddTextResponse)
def add_text(request: AddTextRequest):
    result = process_text_input(request.text, request.instructions)
    return AddTextResponse(result=result)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 