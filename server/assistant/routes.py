from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from server.assistant.service import assistant_action_response, assistant_status_response

router = APIRouter()


@router.get('/api/assistant/status')
async def api_assistant_status():
    return assistant_status_response()


@router.post('/api/assistant/action')
async def api_assistant_action(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({'error': 'Invalid JSON'}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({'error': 'Invalid JSON body'}, status_code=400)
    return await assistant_action_response(body)
