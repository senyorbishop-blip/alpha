from fastapi import APIRouter, Request

from server.campaigns.service import (
    delete_campaign_response,
    list_campaigns_response,
    resume_campaign_response,
    save_campaign_response,
)

router = APIRouter()


@router.get("/api/campaigns")
async def api_list_campaigns():
    return list_campaigns_response()


@router.post("/api/campaigns/{campaign_id}/save")
async def api_save_campaign(campaign_id: str, request: Request):
    return await save_campaign_response(campaign_id, await request.json())


@router.post("/api/campaigns/{campaign_id}/resume")
async def api_resume_campaign(campaign_id: str):
    return await resume_campaign_response(campaign_id)


@router.delete("/api/campaigns/{campaign_id}")
async def api_delete_campaign(campaign_id: str, request: Request):
    return delete_campaign_response(campaign_id, await request.json())
