"""
Campaign CRUD router.
Mounted at /api/campaigns in main.py.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models.db_models import Campaign, CampaignCreate, CampaignUpdate, CampaignRead

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("", response_model=List[CampaignRead])
def list_campaigns(session: Session = Depends(get_session)):
    """Return all campaigns ordered newest-first."""
    return session.exec(
        select(Campaign).order_by(Campaign.created_at.desc())
    ).all()


@router.post("", response_model=CampaignRead, status_code=201)
def create_campaign(payload: CampaignCreate, session: Session = Depends(get_session)):
    """Persist a new campaign (called from the wizard Publish button)."""
    campaign = Campaign.model_validate(payload)
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignRead)
def get_campaign(campaign_id: int, session: Session = Depends(get_session)):
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    session: Session = Depends(get_session),
):
    """Partial update — send only the fields you want to change."""
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(campaign, key, value)
    campaign.updated_at = datetime.utcnow()

    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, session: Session = Depends(get_session)):
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    session.delete(campaign)
    session.commit()
