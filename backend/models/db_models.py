"""
SQLModel database models for Campaign persistence.
Separate from campaign.py which holds the AI extraction schemas.
"""
from __future__ import annotations

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


# ── DB Table ──────────────────────────────────────────────────────────────────

class Campaign(SQLModel, table=True):
    id:               Optional[int] = Field(default=None, primary_key=True)

    # Core identity
    name:             str
    campaign_type:    str     = Field(default="Custom")
    status:           str     = Field(default="active")   # active|scheduled|draft|ended|paused

    # AI-extracted copy
    tone:             Optional[str] = None
    headline:         Optional[str] = None
    body_copy:        Optional[str] = None

    # Goal
    objective:        str     = Field(default="Registrations")
    target_number:    int     = Field(default=0)

    # Schedule
    start_date:       Optional[str] = None   # YYYY-MM-DD
    end_date:         Optional[str] = None   # YYYY-MM-DD

    # Targeting (comma-separated for simplicity; no extra join table needed)
    audience_segments: str   = Field(default="")
    locations:         str   = Field(default="All India")
    channels:          str   = Field(default="")

    # Budget
    budget:           Optional[float] = None
    spent:            Optional[float] = None

    # Performance metrics (updated by analytics; seeded for demo campaigns)
    reach:            int    = Field(default=0)
    impressions:      int    = Field(default=0)
    clicks:           int    = Field(default=0)
    ctr:              str    = Field(default="0%")
    conversions:      int    = Field(default=0)
    progress_pct:     int    = Field(default=0)

    # Timestamps
    created_at:       datetime = Field(default_factory=datetime.utcnow)
    updated_at:       datetime = Field(default_factory=datetime.utcnow)


# ── Request / Response schemas ────────────────────────────────────────────────

class CampaignCreate(SQLModel):
    name:              str
    campaign_type:     str            = "Custom"
    status:            str            = "active"
    tone:              Optional[str]  = None
    headline:          Optional[str]  = None
    body_copy:         Optional[str]  = None
    objective:         str            = "Registrations"
    target_number:     int            = 0
    start_date:        Optional[str]  = None
    end_date:          Optional[str]  = None
    audience_segments: str            = ""
    locations:         str            = "All India"
    channels:          str            = ""
    budget:            Optional[float]= None


class CampaignUpdate(SQLModel):
    """All fields optional — send only what changed."""
    name:              Optional[str]   = None
    campaign_type:     Optional[str]   = None
    status:            Optional[str]   = None
    tone:              Optional[str]   = None
    headline:          Optional[str]   = None
    body_copy:         Optional[str]   = None
    objective:         Optional[str]   = None
    target_number:     Optional[int]   = None
    start_date:        Optional[str]   = None
    end_date:          Optional[str]   = None
    audience_segments: Optional[str]   = None
    locations:         Optional[str]   = None
    channels:          Optional[str]   = None
    budget:            Optional[float] = None
    spent:             Optional[float] = None
    reach:             Optional[int]   = None
    impressions:       Optional[int]   = None
    clicks:            Optional[int]   = None
    ctr:               Optional[str]   = None
    conversions:       Optional[int]   = None
    progress_pct:      Optional[int]   = None


class CampaignRead(SQLModel):
    id:                int
    name:              str
    campaign_type:     str
    status:            str
    tone:              Optional[str]
    headline:          Optional[str]
    body_copy:         Optional[str]
    objective:         str
    target_number:     int
    start_date:        Optional[str]
    end_date:          Optional[str]
    audience_segments: str
    locations:         str
    channels:          str
    budget:            Optional[float]
    spent:             Optional[float]
    reach:             int
    impressions:       int
    clicks:            int
    ctr:               str
    conversions:       int
    progress_pct:      int
    created_at:        datetime
    updated_at:        datetime
