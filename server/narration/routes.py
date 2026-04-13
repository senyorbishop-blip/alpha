from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from server.narration.service import narrate_response

router = APIRouter()


@router.post("/api/narrate")
async def api_narrate(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    return await narrate_response(body)
