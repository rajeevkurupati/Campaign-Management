"""
Campaign CRUD router — all endpoints require authentication.
Mounted at /api/campaigns in main.py.

Scoping rules:
  - Campaigns with user_id == current_user.id  → owned by this user
  - Campaigns with user_id IS NULL             → seeded demo campaigns, visible to everyone
"""
from datetime import datetime, date
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, or_

from auth.dependencies import get_current_user
from auth.models import User
from plans import PLANS, get_plan
from database import get_session
from models.campaign import ExtractRequest, ExtractResponse
from models.db_models import Campaign, CampaignCreate, CampaignUpdate, CampaignRead
from agents.extractor import extract_campaign as ai_extract

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _owned_or_demo(session: Session, user: User):
    """Base query: campaigns owned by user + demo campaigns (user_id IS NULL)."""
    return select(Campaign).where(
        or_(Campaign.user_id == user.id, Campaign.user_id == None)  # noqa: E711
    )


def _assert_owner(campaign: Campaign, user: User):
    """Raise 403 if the user does not own the campaign (demo campaigns block modification)."""
    if campaign.user_id is None:
        raise HTTPException(status_code=403, detail="Demo campaigns cannot be modified")
    if campaign.user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to modify this campaign")


# ── Extraction (auth-gated) ───────────────────────────────────────────────────

@router.post("/extract", response_model=ExtractResponse)
def extract(
    req: ExtractRequest,
    _: User = Depends(get_current_user),          # auth check only — user not used here
):
    """AI brief → structured campaign fields. Requires authentication."""
    result = ai_extract(req.brief)
    if not result.ok:
        raise HTTPException(status_code=422, detail=result.error)
    return result


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[CampaignRead])
def list_campaigns(
    session:      Session = Depends(get_session),
    current_user: User    = Depends(get_current_user),
):
    """Return all campaigns visible to the current user (own + demo), newest first."""
    return session.exec(
        _owned_or_demo(session, current_user).order_by(Campaign.created_at.desc())
    ).all()


@router.post("", response_model=CampaignRead, status_code=201)
def create_campaign(
    payload:      CampaignCreate,
    session:      Session = Depends(get_session),
    current_user: User    = Depends(get_current_user),
):
    """Persist a new campaign. Enforces plan limits server-side."""
    plan = get_plan(current_user.plan)

    # ── Count user's active/scheduled campaigns ───────────────────────────────
    if plan["max_active_campaigns"] is not None:
        active_count = len(session.exec(
            select(Campaign).where(
                Campaign.user_id == current_user.id,
                Campaign.status.in_(["active", "scheduled", "paused"]),
            )
        ).all())
        if active_count >= plan["max_active_campaigns"]:
            raise HTTPException(
                status_code=403,
                detail=f"Your {plan['display_name']} plan allows a maximum of "
                       f"{plan['max_active_campaigns']} active campaigns. "
                       f"Please end or pause an existing campaign first.",
            )

    # ── Budget cap ────────────────────────────────────────────────────────────
    if plan["max_budget"] is not None and payload.budget and payload.budget > plan["max_budget"]:
        raise HTTPException(
            status_code=403,
            detail=f"Your {plan['display_name']} plan has a budget cap of "
                   f"₹{plan['max_budget']:,} per campaign.",
        )

    # ── Campaign type ─────────────────────────────────────────────────────────
    if (
        plan["allowed_campaign_types"] is not None
        and payload.campaign_type not in plan["allowed_campaign_types"]
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Campaign type '{payload.campaign_type}' is not available on your "
                   f"{plan['display_name']} plan. Allowed: {', '.join(plan['allowed_campaign_types'])}.",
        )

    # ── Duration ──────────────────────────────────────────────────────────────
    if payload.start_date and payload.end_date:
        try:
            start = date.fromisoformat(payload.start_date)
            end   = date.fromisoformat(payload.end_date)
            days  = (end - start).days
            if days < plan["min_duration_days"]:
                raise HTTPException(
                    status_code=403,
                    detail=f"Campaign duration must be at least {plan['min_duration_days']} days.",
                )
            if plan["max_duration_days"] is not None and days > plan["max_duration_days"]:
                raise HTTPException(
                    status_code=403,
                    detail=f"Your {plan['display_name']} plan allows campaigns of up to "
                           f"{plan['max_duration_days']} days.",
                )
        except ValueError:
            pass  # invalid date format — Pydantic will catch it separately

    # ── Bind to current user ──────────────────────────────────────────────────
    payload.user_id = current_user.id
    campaign = Campaign.model_validate(payload)
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignRead)
def get_campaign(
    campaign_id:  int,
    session:      Session = Depends(get_session),
    current_user: User    = Depends(get_current_user),
):
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    # Ensure user can see this campaign (own or demo)
    if campaign.user_id is not None and campaign.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id:  int,
    payload:      CampaignUpdate,
    session:      Session = Depends(get_session),
    current_user: User    = Depends(get_current_user),
):
    """Partial update — send only the fields you want to change."""
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _assert_owner(campaign, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(campaign, key, value)
    campaign.updated_at = datetime.utcnow()

    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(
    campaign_id:  int,
    session:      Session = Depends(get_session),
    current_user: User    = Depends(get_current_user),
):
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _assert_owner(campaign, current_user)
    session.delete(campaign)
    session.commit()
