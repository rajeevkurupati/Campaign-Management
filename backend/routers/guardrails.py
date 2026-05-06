"""
Guardrail endpoints — both require authentication.

  POST /api/campaigns/validate      → AI content compliance check
  POST /api/campaigns/check-limits  → Plan limit validation
"""
from datetime import date
from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from auth.dependencies import get_current_user
from auth.models import User
from plans import PLANS, get_plan
from database import get_session
from models.db_models import Campaign
from models.guardrails import (
    LimitCheckRequest, LimitCheckResult, LimitViolation,
    ValidateRequest, ValidationResult,
)
from agents.content_validator import validate_content

router = APIRouter(prefix="/api/campaigns", tags=["guardrails"])


# ── Content Validation ────────────────────────────────────────────────────────

@router.post("/validate", response_model=ValidationResult)
def validate_campaign(
    req:          ValidateRequest,
    _:            User    = Depends(get_current_user),
):
    """
    AI compliance check.
    Runs the campaign brief (+ optional headline / body copy) through the
    content validator and returns score, gate (pass/block), and issues.
    """
    return validate_content(
        brief=req.brief,
        headline=req.headline,
        body_copy=req.body_copy,
        campaign_type=req.campaign_type,
    )


# ── Plan Limit Check ──────────────────────────────────────────────────────────

@router.post("/check-limits", response_model=LimitCheckResult)
def check_limits(
    req:          LimitCheckRequest,
    session:      Session = Depends(get_session),
    current_user: User    = Depends(get_current_user),
):
    """
    Validate proposed campaign fields against the user's plan limits.
    Returns a list of violations (empty = all clear).
    """
    plan      = get_plan(current_user.plan)
    violations: List[LimitViolation] = []

    # ── Active campaign count ─────────────────────────────────────────────────
    if plan["max_active_campaigns"] is not None:
        active_count = len(session.exec(
            select(Campaign).where(
                Campaign.user_id == current_user.id,
                Campaign.status.in_(["active", "scheduled", "paused"]),
            )
        ).all())
        if active_count >= plan["max_active_campaigns"]:
            violations.append(LimitViolation(
                field="active_campaigns",
                message=(
                    f"You already have {active_count} active/scheduled campaign(s). "
                    f"Your {plan['display_name']} plan allows a maximum of "
                    f"{plan['max_active_campaigns']}. End or pause an existing campaign first."
                ),
            ))

    # ── Budget cap ────────────────────────────────────────────────────────────
    if plan["max_budget"] is not None and req.budget and req.budget > plan["max_budget"]:
        violations.append(LimitViolation(
            field="budget",
            message=(
                f"Budget ₹{req.budget:,.0f} exceeds the {plan['display_name']} plan cap "
                f"of ₹{plan['max_budget']:,}. Reduce the budget or upgrade your plan."
            ),
        ))

    # ── Campaign type ─────────────────────────────────────────────────────────
    if (
        plan["allowed_campaign_types"] is not None
        and req.campaign_type
        and req.campaign_type not in plan["allowed_campaign_types"]
    ):
        violations.append(LimitViolation(
            field="campaign_type",
            message=(
                f"Campaign type '{req.campaign_type}' is not available on the "
                f"{plan['display_name']} plan. "
                f"Available types: {', '.join(plan['allowed_campaign_types'])}."
            ),
        ))

    # ── Audience segments ─────────────────────────────────────────────────────
    if plan["allowed_segments"] is not None and req.audience_segments:
        blocked = [s for s in req.audience_segments if s not in plan["allowed_segments"]]
        if blocked:
            violations.append(LimitViolation(
                field="audience_segments",
                message=(
                    f"Segment(s) not available on your {plan['display_name']} plan: "
                    f"{', '.join(blocked)}. Upgrade to access these segments."
                ),
            ))

    # ── Channels ──────────────────────────────────────────────────────────────
    if plan["allowed_channels"] is not None and req.channels:
        blocked = [c for c in req.channels if c not in plan["allowed_channels"]]
        if blocked:
            violations.append(LimitViolation(
                field="channels",
                message=(
                    f"Channel(s) not available on your {plan['display_name']} plan: "
                    f"{', '.join(blocked)}. Upgrade to access these channels."
                ),
            ))

    # ── Duration ──────────────────────────────────────────────────────────────
    if req.start_date and req.end_date:
        try:
            days = (date.fromisoformat(req.end_date) - date.fromisoformat(req.start_date)).days
            if days < plan["min_duration_days"]:
                violations.append(LimitViolation(
                    field="duration",
                    message=f"Campaign duration ({days} days) is below the minimum of {plan['min_duration_days']} days.",
                ))
            if plan["max_duration_days"] is not None and days > plan["max_duration_days"]:
                violations.append(LimitViolation(
                    field="duration",
                    message=(
                        f"Campaign duration ({days} days) exceeds the {plan['display_name']} plan "
                        f"maximum of {plan['max_duration_days']} days."
                    ),
                ))
        except ValueError:
            pass

    return LimitCheckResult(
        ok=len(violations) == 0,
        plan=plan["display_name"],
        violations=violations,
    )
