"""
Plan tier configuration — controls guardrail limits per customer tier.
Edit the PLANS dict to change what each plan can do.

None values mean unlimited / unrestricted.
"""

PLANS: dict[str, dict] = {
    "starter": {
        "display_name":           "Starter",
        "max_active_campaigns":   2,
        "max_budget":             25_000,
        "min_duration_days":      7,
        "max_duration_days":      30,
        "allowed_campaign_types": ["Awareness", "Event Drive"],
        "allowed_channels":       ["Feed Posts", "Email", "Social Media"],
        "allowed_segments":       ["Job Seekers", "Freshers", "Career Break"],
    },
    "growth": {
        "display_name":           "Growth",
        "max_active_campaigns":   10,
        "max_budget":             200_000,
        "min_duration_days":      7,
        "max_duration_days":      60,
        "allowed_campaign_types": ["Awareness", "Event Drive", "Hiring Drive", "Mentorship"],
        "allowed_channels":       [
            "Feed Posts", "Email", "Social Media",
            "Push Notifications", "Groups", "In-App",
        ],
        "allowed_segments":       [
            "Job Seekers", "Freshers", "Career Break",
            "Women in Tech", "Mid-Senior", "Returnees",
        ],
    },
    "enterprise": {
        "display_name":           "Enterprise",
        "max_active_campaigns":   None,
        "max_budget":             None,
        "min_duration_days":      7,
        "max_duration_days":      None,
        "allowed_campaign_types": None,
        "allowed_channels":       None,
        "allowed_segments":       None,
    },
}


def get_plan(plan_name: str) -> dict:
    """Return plan config; falls back to 'starter' for unknown plan names."""
    return PLANS.get(plan_name, PLANS["starter"])
