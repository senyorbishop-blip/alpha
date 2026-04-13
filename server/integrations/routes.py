from fastapi import APIRouter, File, UploadFile

from server.integrations.service import (
    fetch_ddb_character_response,
    integrations_status_response,
    parse_character_pdf_response,
)

router = APIRouter()


@router.get("/api/ddb/character/{char_id}")
async def fetch_ddb_character(char_id: str):
    return await fetch_ddb_character_response(char_id)


@router.post("/api/parse-character-pdf")
async def parse_character_pdf(file: UploadFile = File(...)):
    return parse_character_pdf_response(await file.read())


@router.get("/api/integrations/status")
async def api_integrations_status():
    return integrations_status_response()
