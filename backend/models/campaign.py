from pydantic import BaseModel, Field
from typing import Literal, List, Optional


CampaignType = Literal[
    "Awareness", "Event Drive", "Hiring Drive", "Learning", "Mentorship", "Custom"
]

CampaignTone = Literal[
    "Professional & Aspirational",
    "Warm & Inclusive",
    "Bold & Celebratory",
    "Tech-Forward",
]

CampaignObjective = Literal[
    "Job Applications",
    "Registrations",
    "Session Attendance",
    "Community Growth",
    "Profile Views",
]

AudienceSegment = Literal[
    "Job Seekers",
    "Career Break",
    "Women in Tech",
    "Mid-Senior",
    "Freshers",
    "Returnees",
    "Entrepreneurs",
]

Location = Literal[
    "Bengaluru", "Mumbai", "Delhi NCR", "Hyderabad", "Pune", "All India"
]


class ExtractRequest(BaseModel):
    brief: str = Field(..., min_length=10, description="Plain-English campaign brief")


class ExtractedCampaign(BaseModel):
    campaign_type: CampaignType
    tone: CampaignTone
    headline: str
    body_copy: str
    objective: CampaignObjective
    target_number: int
    start_date: str = Field(..., description="ISO date YYYY-MM-DD")
    end_date: str   = Field(..., description="ISO date YYYY-MM-DD")
    audience_segments: List[AudienceSegment]
    locations: List[Location]


class ExtractResponse(BaseModel):
    ok: bool
    data: Optional[ExtractedCampaign] = None
    error: Optional[str] = None
    usage: Optional[dict] = None
