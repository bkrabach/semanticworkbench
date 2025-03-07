# api_server.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cortex_core import CortexCore

app = FastAPI(title="Cortex Core API", description="A minimal RESTful API for the Cortex Core", version="0.1")

# Initialize our Cortex Core instance.
core = CortexCore()

# Request model for input processing.
class ProcessInputRequest(BaseModel):
    user_id: str
    token: str
    input_text: str

@app.post("/process", summary="Process user input through the Cortex Core")
def process_input(request_data: ProcessInputRequest):
    response = core.process_input(request_data.user_id, request_data.input_text, request_data.token)
    if response == "Authentication failed":
        raise HTTPException(status_code=401, detail="Authentication failed")
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
