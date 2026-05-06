"""
Pydantic schemas for guardrail endpoints:
  - /api/campaigns/validate   (AI content compliance check)
  - /api/campaigns/check-limits (plan limit validation)
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


# ── Content Validation ────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    brief:         str            = Field(..., min_length=10, description="Original campaign brief text")
    headline:      Optional[str] = None
    body_copy:     Optional[str] = None
    campaign_type: Optional[str] = None


class ValidationIssue(BaseModel):
    field:    str   # brief | headline | body_copy | audience | tone | objective | overall
    severity: str   # error | warning
    message:  str   # human-readable description + suggested fix


class ValidationResult(BaseModel):
    ok:      bool
    score:   int                     # 0–100
    gate:    str                     # pass | block
    summary: str                     # one-sentence verdict
    issues:  List[ValidationIssue]
    usage:   Optional[dict] = None   # token usage (for transparency)


# ── Plan Limit Check ──────────────────────────────────────────────────────────

class LimitCheckRequest(BaseModel):
    campaign_type:     Optional[str]        = None
    budget:            Optional[float]      = None
    start_date:        Optional[str]        = None   # YYYY-MM-DD
    end_date:          Optional[str]        = None   # YYYY-MM-DD
    audience_segments: Optional[List[str]] = None
    channels:          Optional[List[str]] = None


class LimitViolation(BaseModel):
    field:   str
    message: str


class LimitCheckResult(BaseModel):
    ok:         bool
    plan:       str
    violations: List[LimitViolation]
