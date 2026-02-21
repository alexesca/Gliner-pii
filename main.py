from fastapi import FastAPI
from pydantic import BaseModel
from gliner import GLiNER
from typing import List

app = FastAPI(title="GLiNER-PII API")

model = GLiNER.from_pretrained("knowledgator/gliner-pii-base-v1.0")

class PIIRequest(BaseModel):
    text: str
    labels: List[str] = ["person", "email", "phone number", "location"]
    threshold: float = 0.3

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
async def predict(request: PIIRequest):
    entities = model.predict_entities(
        request.text, request.labels, threshold=request.threshold
    )
    return {"entities": entities}
