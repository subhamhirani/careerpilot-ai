"""
Lightweight résumé‑matcher microservice.
Accepts a PDF or TXT résumé upload and returns a static list of job matches
and a few improvement suggestions. Designed for quick demo / verification.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/match")
async def match_resume(file: UploadFile = File(...)):
    # In a real implementation we would parse the résumé and run embeddings.
    # Here we return a deterministic mock response for verification.
    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    # Read the file (discard contents) to simulate processing time.
    _ = await file.read()
    mock_response = {
        "matches": [
            {"job_id": "123", "title": "Software Engineer", "company": "Acme Corp", "score": 0.95},
            {"job_id": "456", "title": "Backend Developer", "company": "Beta Ltd", "score": 0.92},
            {"job_id": "789", "title": "Data Engineer", "company": "Gamma Inc", "score": 0.89},
        ],
        "suggestions": [
            "Add concrete metrics (e.g., ' improved performance by 20%').",
            "Include a separate section for cloud technologies (AWS, GCP).",
            "Tailor the résumé headline to the target role (e.g., 'Full‑stack Engineer with 3 yrs experience')."
        ]
    }
    return JSONResponse(content=mock_response)
