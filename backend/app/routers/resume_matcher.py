"""
FastAPI router that proxies résumé upload to the resume‑matcher micro‑service.
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from starlette.responses import JSONResponse
import httpx

# Re‑use existing JWT dependency from the project
from backend.app.dependencies import get_current_user_id

router = APIRouter(prefix="/api/resume", tags=["resume"])

RESUME_AGENT_URL = "http://careerpilot-resume-agent:8002"

@router.post("/match")
async def match_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    """Forward the uploaded résumé to the resume‑matcher service.

    The proxy adds the JWT (user_id) as a Bearer token so the downstream
    service can perform auth‑aware personalization if needed.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Forward the file as multipart/form‑data
            files = {"file": (file.filename, await file.read(), file.content_type)}
            headers = {"Authorization": f"Bearer {user_id}"}
            resp = await client.post(f"{RESUME_AGENT_URL}/match", files=files, headers=headers)
            resp.raise_for_status()
            return JSONResponse(content=resp.json())
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
