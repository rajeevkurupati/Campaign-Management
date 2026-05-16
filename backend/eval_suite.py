#!/usr/bin/env python3
"""
eval_suite.py — AI Agent Evaluation Suite
==========================================
Evaluates both AI agents against a labelled golden dataset.

  Agent 1 — Extractor:  plain-English brief → structured campaign fields
  Agent 2 — Validator:  campaign content → compliance score / gate (pass|block)

Usage:
    python eval_suite.py                       # run both agents
    python eval_suite.py --agent extractor     # extractor only
    python eval_suite.py --agent validator     # validator only
    python eval_suite.py --consistency 3       # re-run borderline cases N times

Metrics reported:
    Extractor  → field accuracy, enum compliance, completeness, date validity,
                 location/segment recall, consistency across runs
    Validator  → gate accuracy, false-negative rate, false-positive rate,
                 score range accuracy, issue presence, consistency across runs
"""
import sys, argparse, time, statistics
sys.path.insert(0, '.')

# Force UTF-8 output on Windows (box-drawing chars, block chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Terminal colours ──────────────────────────────────────────────────────────
G  = "\033[92m"   # green
R  = "\033[91m"   # red
Y  = "\033[93m"   # yellow
B  = "\033[94m"   # blue/cyan
W  = "\033[97m"   # white bold
DIM= "\033[2m"
RST= "\033[0m"
OK  = f"{G}PASS{RST}"
FAIL= f"{R}FAIL{RST}"
WARN= f"{Y}WARN{RST}"

def _hdr(title):
    bar = "─" * 60
    print(f"\n{W}{bar}{RST}")
    print(f"{W}  {title}{RST}")
    print(f"{W}{bar}{RST}")

def _sub(title):
    print(f"\n{B}  ▸ {title}{RST}")

# ── Valid enum sets (mirrors models/campaign.py) ──────────────────────────────
VALID_TYPES      = {"Awareness","Event Drive","Hiring Drive","Learning","Mentorship","Custom"}
VALID_TONES      = {"Professional & Aspirational","Warm & Inclusive","Bold & Celebratory","Tech-Forward"}
VALID_OBJECTIVES = {"Job Applications","Registrations","Session Attendance","Community Growth","Profile Views"}
VALID_SEGMENTS   = {"Job Seekers","Career Break","Women in Tech","Mid-Senior","Freshers","Returnees","Entrepreneurs"}
VALID_LOCATIONS  = {"Bengaluru","Mumbai","Delhi NCR","Hyderabad","Pune","All India"}


# ══════════════════════════════════════════════════════════════════════════════
# GOLDEN DATASET — EXTRACTOR
# Each case: brief + the fields we can reliably assert.
# Fields omitted from 'expected' are not checked (e.g. AI-generated copy).
# ══════════════════════════════════════════════════════════════════════════════
EXTRACTOR_CASES = [
    {
        "id": "EX-01",
        "label": "Tech hiring drive — all fields explicit",
        "brief": (
            "Run a Hiring Drive for women in tech across Bengaluru, Mumbai and Delhi NCR. "
            "Partner with 25 top employers. Target 1,000 job applications by end of July 2026."
        ),
        "expected": {
            "campaign_type":     "Hiring Drive",
            "objective":         "Job Applications",
            "target_number_min": 800,
            "target_number_max": 1200,
            "locations":         ["Bengaluru", "Mumbai", "Delhi NCR"],
            "audience_segments_contains": ["Women in Tech", "Job Seekers"],
        },
    },
    {
        "id": "EX-02",
        "label": "Returnee awareness campaign",
        "brief": (
            "An awareness campaign for women returning from career breaks. "
            "We want to reach 5,000 women across All India. "
            "Run it for the whole of June 2026."
        ),
        "expected": {
            "campaign_type":     "Awareness",
            "objective":         "Registrations",
            "target_number_min": 3000,
            "target_number_max": 7000,
            "locations":         ["All India"],
            "audience_segments_contains": ["Career Break", "Returnees"],
        },
    },
    {
        "id": "EX-03",
        "label": "Mentorship programme for mid-senior professionals",
        "brief": (
            "Launch a mentorship programme targeting mid-senior women professionals in Hyderabad and Pune. "
            "Goal is 200 mentor-mentee registrations. Programme runs August through September 2026."
        ),
        "expected": {
            "campaign_type":     "Mentorship",
            "objective":         "Registrations",
            "target_number_min": 150,
            "target_number_max": 250,
            "locations":         ["Hyderabad", "Pune"],
            "audience_segments_contains": ["Mid-Senior"],
        },
    },
    {
        "id": "EX-04",
        "label": "Fresher upskilling event",
        "brief": (
            "Organise an event drive to promote our free Python bootcamp for women freshers. "
            "Target 500 registrations across Bengaluru and Hyderabad. Event is in September 2026."
        ),
        "expected": {
            "campaign_type":     "Event Drive",
            "objective":         "Registrations",
            "target_number_min": 400,
            "target_number_max": 600,
            "locations":         ["Bengaluru", "Hyderabad"],
            "audience_segments_contains": ["Freshers"],
        },
    },
    {
        "id": "EX-05",
        "label": "Learning campaign — All India, large target",
        "brief": (
            "Run a learning campaign promoting our leadership curriculum for women professionals across India. "
            "We want 10,000 women to start the course by December 2026."
        ),
        "expected": {
            "campaign_type":     "Learning",
            "objective":         "Registrations",
            "target_number_min": 8000,
            "target_number_max": 12000,
            "locations":         ["All India"],
        },
    },
    {
        "id": "EX-06",
        "label": "Entrepreneur community drive",
        "brief": (
            "Build our community of women entrepreneurs. "
            "We want 300 new entrepreneur profiles in Mumbai and Delhi NCR by end of Q3 2026."
        ),
        "expected": {
            "campaign_type":     "Awareness",
            "objective":         "Community Growth",
            "target_number_min": 200,
            "target_number_max": 400,
            "locations":         ["Mumbai", "Delhi NCR"],
            "audience_segments_contains": ["Entrepreneurs"],
        },
    },
    {
        "id": "EX-07",
        "label": "Multi-city hiring with exact date range",
        "brief": (
            "Hiring campaign from 1 June 2026 to 31 August 2026. "
            "Target women job seekers in Bengaluru, Mumbai, Delhi NCR, Hyderabad and Pune. "
            "Aim for 2,000 job applications."
        ),
        "expected": {
            "campaign_type":     "Hiring Drive",
            "objective":         "Job Applications",
            "target_number_min": 1800,
            "target_number_max": 2200,
            "start_date_month":  "2026-06",
            "end_date_month":    "2026-08",
            "locations":         ["Bengaluru", "Mumbai", "Delhi NCR", "Hyderabad", "Pune"],
            "audience_segments_contains": ["Job Seekers"],
        },
    },
    {
        "id": "EX-08",
        "label": "Vague brief — minimal info (completeness test)",
        "brief": "Run a campaign for women professionals.",
        "expected": {
            # No specific fields expected — just check completeness (all fields non-null)
            "completeness_only": True,
        },
    },
    {
        "id": "EX-09",
        "label": "Professional tone signal in brief",
        "brief": (
            "A corporate employer branding campaign targeting senior women leaders in Bengaluru. "
            "Showcase our inclusive leadership culture. Target 1,000 profile views."
        ),
        "expected": {
            "campaign_type":     "Awareness",
            "objective":         "Profile Views",
            "tone_in":           ["Professional & Aspirational"],
            "audience_segments_contains": ["Mid-Senior"],
            "locations":         ["Bengaluru"],
        },
    },
    {
        "id": "EX-10",
        "label": "Celebratory tone signal",
        "brief": (
            "Celebrate International Women's Day with a bold awareness campaign. "
            "Target 50,000 women across All India on 8 March 2026. "
            "We want big engagement — community growth is the goal."
        ),
        "expected": {
            "campaign_type":              "Awareness",
            "objective":                  "Community Growth",
            "target_number_min":          30000,
            "target_number_max":          70000,
            "locations":                  ["All India"],
            "tone_in":                    ["Bold & Celebratory"],
        },
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# GOLDEN DATASET — VALIDATOR
# category: clear_pass | clear_block | borderline
# expected_score_min / max: acceptable score range
# expected_issues_keywords: strings that must appear in at least one issue message
#   (only checked for BLOCK cases)
# ══════════════════════════════════════════════════════════════════════════════
VALIDATOR_CASES = [
    # ── CLEAR PASS ────────────────────────────────────────────────────────────
    {
        "id": "VAL-01",
        "label": "Tech hiring drive — fully compliant",
        "category": "clear_pass",
        "brief": "Hiring drive for women engineers and data scientists in Bengaluru and Mumbai. Partner with 20 top tech companies. Target 500 job applications by end of June 2026.",
        "headline": "500 Opportunities. 20 Top Employers. Your Next Role Starts Here.",
        "body_copy": "India's leading companies are looking for talented women in tech. Browse open roles, connect directly with hiring teams, and take the next step in your career.",
        "campaign_type": "Hiring Drive",
        "expected_gate": "pass",
        "expected_score_min": 80,
        "expected_score_max": 100,
    },
    {
        "id": "VAL-02",
        "label": "Career returnee bootcamp — empowering language",
        "category": "clear_pass",
        "brief": "Six-week bootcamp with mentorship and placement support for women returning from a career break.",
        "headline": "Your Comeback Starts Now — 6 Weeks to Your Next Role",
        "body_copy": "Designed by women, for women. Refresh your skills, rebuild your confidence, and step back into the workforce with real support from mentors and hiring partners.",
        "campaign_type": "Awareness",
        "expected_gate": "pass",
        "expected_score_min": 82,
        "expected_score_max": 100,
    },
    {
        "id": "VAL-03",
        "label": "Leadership mentorship programme",
        "category": "clear_pass",
        "brief": "Mentorship programme connecting mid-senior women professionals with C-suite mentors. Registrations open for Q3 2026 cohort.",
        "headline": "Lead With Intention — Join the Mentorship Cohort",
        "body_copy": "12 weeks. 1 dedicated mentor. Unlimited potential. Open to women with 5+ years of experience across any industry.",
        "campaign_type": "Mentorship",
        "expected_gate": "pass",
        "expected_score_min": 83,
        "expected_score_max": 100,
    },
    {
        "id": "VAL-04",
        "label": "Fresher Python bootcamp event",
        "category": "clear_pass",
        "brief": "Free Python bootcamp event for women freshers and early-career professionals. Learn, code, and connect.",
        "headline": "Learn Python for Free — Seats Limited",
        "body_copy": "Hands-on Python training designed for women starting their tech career. Industry mentors, live projects, and a certificate on completion.",
        "campaign_type": "Event Drive",
        "expected_gate": "pass",
        "expected_score_min": 80,
        "expected_score_max": 100,
    },
    {
        "id": "VAL-05",
        "label": "Women's Day awareness — celebratory, career-relevant",
        "category": "clear_pass",
        "brief": "International Women's Day awareness campaign celebrating women professionals across India.",
        "headline": "Every Day Is a Step Forward — Happy Women's Day",
        "body_copy": "We celebrate the ambitions, achievements, and resilience of women professionals. This Women's Day, explore new career tools, opportunities, and community connections on HerKey.",
        "campaign_type": "Awareness",
        "expected_gate": "pass",
        "expected_score_min": 80,
        "expected_score_max": 100,
    },

    # ── CLEAR BLOCK ───────────────────────────────────────────────────────────
    {
        "id": "VAL-06",
        "label": "Beauty product — no career angle [irrelevant]",
        "category": "clear_block",
        "brief": "Promote our new skincare range for working women. Buy 2 get 1 free this month.",
        "headline": "Glow All Day — New Skincare for Busy Women",
        "body_copy": "Our lightweight moisturiser is perfect for the office. Order now and get free shipping.",
        "campaign_type": "Awareness",
        "expected_gate": "block",
        "expected_score_min": 0,
        "expected_score_max": 45,
        "expected_issues_keywords": ["relevance", "career", "platform"],
    },
    {
        "id": "VAL-07",
        "label": "Home loan ad — financially off-topic [irrelevant]",
        "category": "clear_block",
        "brief": "Promote affordable home loans for working women. Low interest rates, easy approval.",
        "headline": "Own Your Home — Special Rates for Working Women",
        "body_copy": "Apply today for a home loan with rates starting at 7.5% p.a. Quick approval, minimal documentation.",
        "campaign_type": "Awareness",
        "expected_gate": "block",
        "expected_score_min": 0,
        "expected_score_max": 50,
        "expected_issues_keywords": ["relevance", "career"],
    },
    {
        "id": "VAL-08",
        "label": "Condescending language — stereotyping [empowerment fail]",
        "category": "clear_block",
        "brief": "Career opportunities for housewives looking to get back to work. Even if you haven't worked in years, we have simple jobs for you.",
        "headline": "Simple Jobs for Homemakers — No Experience Needed",
        "body_copy": "Even women who've been at home for years can start earning. Easy part-time roles available now.",
        "campaign_type": "Awareness",
        "expected_gate": "block",
        "expected_score_min": 0,
        "expected_score_max": 55,
        "expected_issues_keywords": ["condescending", "stereotype", "patronising", "housewife", "tone"],
    },
    {
        "id": "VAL-09",
        "label": "False claim — guaranteed placement [truthfulness fail]",
        "category": "clear_block",
        "brief": "Join our placement programme. 100% guaranteed job placement within 30 days. All candidates placed.",
        "headline": "100% Job Guaranteed — Or Your Money Back",
        "body_copy": "We guarantee every registered candidate a job offer within 30 days. Government-approved programme. No exceptions.",
        "campaign_type": "Hiring Drive",
        "expected_gate": "block",
        "expected_score_min": 0,
        "expected_score_max": 60,
        "expected_issues_keywords": ["guarantee", "misleading", "truthful", "false"],
    },
    {
        "id": "VAL-10",
        "label": "Age discrimination — restricted targeting",
        "category": "clear_block",
        "brief": "Exclusive hiring event for women aged 22–28 only. Senior or older candidates not suitable.",
        "headline": "Young Talent Drive — Women 22–28 Only",
        "body_copy": "This event is strictly for women between 22 and 28 years old. Applications from older candidates will not be considered.",
        "campaign_type": "Hiring Drive",
        "expected_gate": "block",
        "expected_score_min": 0,
        "expected_score_max": 50,
        "expected_issues_keywords": ["age", "discriminat", "restrict"],
    },
    {
        "id": "VAL-11",
        "label": "Pure consumer ad — no professional context",
        "category": "clear_block",
        "brief": "Flash sale on women's apparel this weekend. Up to 70% off on all items.",
        "headline": "70% Off — Weekend Sale Ends Sunday",
        "body_copy": "Shop our latest collection of women's clothing at unbeatable prices. Limited stock. Free delivery on orders above ₹999.",
        "campaign_type": "Awareness",
        "expected_gate": "block",
        "expected_score_min": 0,
        "expected_score_max": 20,
        "expected_issues_keywords": ["relevance", "career", "platform"],
    },

    # ── BORDERLINE (score expected near 80 threshold) ─────────────────────────
    {
        "id": "VAL-12",
        "label": "Returnee campaign — vague objective [borderline]",
        "category": "borderline",
        "brief": "Campaign for women coming back to work after a break. We want to help them find opportunities.",
        "headline": "Back to Work — We're Here to Help",
        "body_copy": "Whether you've been away for 6 months or 6 years, there are opportunities waiting for you.",
        "campaign_type": "Awareness",
        "expected_gate": "block",    # vague objective should trigger block
        "expected_score_min": 65,
        "expected_score_max": 82,
        "expected_issues_keywords": ["objective", "measurable", "clarity", "vague"],
    },
    {
        "id": "VAL-13",
        "label": "Hiring drive — mildly ambiguous claim [borderline]",
        "category": "borderline",
        "brief": "Hiring campaign for women in tech. Partner with leading companies. Best salaries in the industry.",
        "headline": "The Best Roles. The Best Pay. Apply Now.",
        "body_copy": "Top tech companies are hiring women engineers at the best industry salaries. Join thousands who've found their dream role through us.",
        "campaign_type": "Hiring Drive",
        "expected_gate": "block",    # 'best salaries' is an unsubstantiated superlative
        "expected_score_min": 68,
        "expected_score_max": 82,
        "expected_issues_keywords": ["claim", "superlative", "mislead", "substantiat", "truthful"],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACTOR EVAL
# ══════════════════════════════════════════════════════════════════════════════

def _eval_extractor_case(case: dict, run_num: int = 1) -> dict:
    """Run a single extractor case and return per-field results."""
    from agents.extractor import extract_campaign

    t0  = time.time()
    res = extract_campaign(case["brief"])
    elapsed = time.time() - t0

    result = {
        "id":       case["id"],
        "label":    case["label"],
        "ok":       res.ok,
        "elapsed":  round(elapsed, 2),
        "run":      run_num,
        "checks":   {},
        "usage":    res.usage or {},
    }

    if not res.ok:
        result["error"] = res.error
        return result

    d = res.data

    # ── Completeness: all required fields populated ───────────────────────────
    required = ["campaign_type","tone","headline","body_copy","objective",
                "target_number","start_date","end_date","audience_segments","locations"]
    missing = [f for f in required if not getattr(d, f, None)]
    result["checks"]["completeness"] = {
        "pass": len(missing) == 0,
        "detail": f"missing: {missing}" if missing else "all fields present",
    }

    # ── Enum compliance ───────────────────────────────────────────────────────
    enum_issues = []
    if d.campaign_type not in VALID_TYPES:
        enum_issues.append(f"campaign_type='{d.campaign_type}'")
    if d.tone not in VALID_TONES:
        enum_issues.append(f"tone='{d.tone}'")
    if d.objective not in VALID_OBJECTIVES:
        enum_issues.append(f"objective='{d.objective}'")
    for seg in (d.audience_segments or []):
        if seg not in VALID_SEGMENTS:
            enum_issues.append(f"segment='{seg}'")
    for loc in (d.locations or []):
        if loc not in VALID_LOCATIONS:
            enum_issues.append(f"location='{loc}'")
    result["checks"]["enum_compliance"] = {
        "pass": len(enum_issues) == 0,
        "detail": ", ".join(enum_issues) if enum_issues else "all valid",
    }

    # ── Date validity ─────────────────────────────────────────────────────────
    try:
        from datetime import date
        sd = date.fromisoformat(d.start_date)
        ed = date.fromisoformat(d.end_date)
        date_ok = sd < ed
        result["checks"]["date_validity"] = {
            "pass": date_ok,
            "detail": f"{d.start_date} → {d.end_date}" + ("" if date_ok else "  ⚠ start >= end"),
        }
    except Exception as e:
        result["checks"]["date_validity"] = {"pass": False, "detail": str(e)}

    # ── Only completeness for vague briefs ────────────────────────────────────
    exp = case.get("expected", {})
    if exp.get("completeness_only"):
        return result

    # ── Campaign type match ───────────────────────────────────────────────────
    if "campaign_type" in exp:
        match = d.campaign_type == exp["campaign_type"]
        result["checks"]["campaign_type"] = {
            "pass": match,
            "detail": f"got '{d.campaign_type}', expected '{exp['campaign_type']}'",
        }

    # ── Objective match ───────────────────────────────────────────────────────
    if "objective" in exp:
        match = d.objective == exp["objective"]
        result["checks"]["objective"] = {
            "pass": match,
            "detail": f"got '{d.objective}', expected '{exp['objective']}'",
        }

    # ── Target number in range ────────────────────────────────────────────────
    if "target_number_min" in exp:
        lo, hi = exp["target_number_min"], exp["target_number_max"]
        match = lo <= (d.target_number or 0) <= hi
        result["checks"]["target_number"] = {
            "pass": match,
            "detail": f"got {d.target_number}, expected {lo}–{hi}",
        }

    # ── Locations recall ──────────────────────────────────────────────────────
    if "locations" in exp:
        got    = set(d.locations or [])
        wanted = set(exp["locations"])
        found  = wanted & got
        recall = len(found) / len(wanted) if wanted else 1.0
        result["checks"]["locations_recall"] = {
            "pass":   recall >= 0.8,
            "detail": f"{recall:.0%} — found {sorted(found)}, missed {sorted(wanted-got)}",
        }

    # ── Audience segment recall ───────────────────────────────────────────────
    if "audience_segments_contains" in exp:
        got    = set(d.audience_segments or [])
        wanted = set(exp["audience_segments_contains"])
        found  = wanted & got
        recall = len(found) / len(wanted) if wanted else 1.0
        result["checks"]["segments_recall"] = {
            "pass":   recall >= 0.5,
            "detail": f"{recall:.0%} — found {sorted(found)}, missed {sorted(wanted-got)}",
        }

    # ── Tone match ────────────────────────────────────────────────────────────
    if "tone_in" in exp:
        match = d.tone in exp["tone_in"]
        result["checks"]["tone"] = {
            "pass": match,
            "detail": f"got '{d.tone}', expected one of {exp['tone_in']}",
        }

    # ── Date month match ─────────────────────────────────────────────────────
    if "start_date_month" in exp:
        match = (d.start_date or "").startswith(exp["start_date_month"])
        result["checks"]["start_date"] = {
            "pass": match,
            "detail": f"got '{d.start_date}', expected month '{exp['start_date_month']}'",
        }
    if "end_date_month" in exp:
        match = (d.end_date or "").startswith(exp["end_date_month"])
        result["checks"]["end_date"] = {
            "pass": match,
            "detail": f"got '{d.end_date}', expected month '{exp['end_date_month']}'",
        }

    return result


def run_extractor_eval(consistency_runs: int = 1):
    _hdr("EXTRACTOR AGENT EVALUATION")

    all_results   = []
    check_totals  = {}   # check_name → [True/False, ...]
    token_costs   = []

    for case in EXTRACTOR_CASES:
        _sub(f"{case['id']} — {case['label']}")
        runs = []
        for r in range(consistency_runs):
            res = _eval_extractor_case(case, run_num=r+1)
            runs.append(res)
            if consistency_runs > 1:
                status_parts = []
                for ck, cv in res["checks"].items():
                    icon = G+"✓"+RST if cv["pass"] else R+"✗"+RST
                    status_parts.append(f"{icon} {ck}")
                print(f"    run {r+1}: {' | '.join(status_parts)}  ({res['elapsed']}s)")

        # Use first run for primary reporting; use all runs for consistency
        res = runs[0]
        all_results.append(res)

        if not res["ok"]:
            print(f"    {R}ERROR{RST}: {res.get('error','unknown error')}")
            continue

        # Print per-check results
        for ck, cv in res["checks"].items():
            icon = f"{G}✓{RST}" if cv["pass"] else f"{R}✗{RST}"
            print(f"    {icon}  {ck:<25} {DIM}{cv['detail']}{RST}")
            check_totals.setdefault(ck, []).append(cv["pass"])

        # Tokens
        usage = res.get("usage", {})
        if usage:
            inp, out = usage.get("input_tokens",0), usage.get("output_tokens",0)
            print(f"    {DIM}tokens: {inp} in / {out} out  ({res['elapsed']}s){RST}")
            token_costs.append({"in": inp, "out": out})

        # Consistency check (only meaningful if consistency_runs > 1)
        if consistency_runs > 1 and len(runs) > 1:
            type_vals = [r["checks"].get("campaign_type",{}).get("detail","") for r in runs]
            all_same  = len(set(type_vals)) == 1
            icon = f"{G}✓{RST}" if all_same else f"{Y}~{RST}"
            print(f"    {icon}  consistency ({consistency_runs} runs)  "
                  f"{DIM}type: {set(type_vals)}{RST}")

    # ── Aggregate summary ─────────────────────────────────────────────────────
    _hdr("EXTRACTOR — AGGREGATE METRICS")
    total_checks = sum(len(v) for v in check_totals.values())
    pass_checks  = sum(sum(v) for v in check_totals.values())
    overall_pct  = 100 * pass_checks / total_checks if total_checks else 0

    print(f"\n  {'Check':<30} {'Pass':<6} {'Total':<6} {'Rate':>6}")
    print(f"  {'─'*30} {'─'*6} {'─'*6} {'─'*6}")
    for ck in sorted(check_totals):
        passes = sum(check_totals[ck])
        total  = len(check_totals[ck])
        pct    = 100 * passes / total
        colour = G if pct >= 90 else (Y if pct >= 70 else R)
        print(f"  {ck:<30} {passes:<6} {total:<6} {colour}{pct:5.0f}%{RST}")

    colour = G if overall_pct >= 90 else (Y if overall_pct >= 70 else R)
    print(f"\n  {'OVERALL':<30} {pass_checks:<6} {total_checks:<6} {colour}{overall_pct:5.0f}%{RST}")

    if token_costs:
        avg_in  = statistics.mean(c["in"]  for c in token_costs)
        avg_out = statistics.mean(c["out"] for c in token_costs)
        print(f"\n  Avg tokens per call: {avg_in:.0f} in / {avg_out:.0f} out")

    return overall_pct


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATOR EVAL
# ══════════════════════════════════════════════════════════════════════════════

def _eval_validator_case(case: dict, run_num: int = 1) -> dict:
    """Run a single validator case and return scored result."""
    from agents.content_validator import validate_content

    t0  = time.time()
    res = validate_content(
        brief         = case["brief"],
        headline      = case.get("headline"),
        body_copy     = case.get("body_copy"),
        campaign_type = case.get("campaign_type"),
    )
    elapsed = time.time() - t0

    exp_gate  = case["expected_gate"]
    exp_s_min = case["expected_score_min"]
    exp_s_max = case["expected_score_max"]
    exp_kw    = case.get("expected_issues_keywords", [])

    gate_match      = res.gate == exp_gate
    score_in_range  = exp_s_min <= res.score <= exp_s_max
    false_negative  = exp_gate == "block" and res.gate == "pass"
    false_positive  = exp_gate == "pass"  and res.gate == "block"

    # Issue keyword check (for BLOCK cases only)
    all_issue_text = " ".join(
        (i.message + " " + i.field).lower() for i in res.issues
    ) + " " + res.summary.lower()
    kw_found = {kw: kw.lower() in all_issue_text for kw in exp_kw}

    return {
        "id":            case["id"],
        "label":         case["label"],
        "category":      case["category"],
        "run":           run_num,
        "gate":          res.gate,
        "score":         res.score,
        "summary":       res.summary,
        "issues":        res.issues,
        "elapsed":       round(elapsed, 2),
        "usage":         res.usage or {},
        "gate_match":    gate_match,
        "score_in_range":score_in_range,
        "false_negative":false_negative,
        "false_positive":false_positive,
        "kw_found":      kw_found,
        "exp_gate":      exp_gate,
        "exp_score":     f"{exp_s_min}–{exp_s_max}",
    }


def run_validator_eval(consistency_runs: int = 1):
    _hdr("CONTENT VALIDATOR EVALUATION")

    all_results    = []
    token_costs    = []
    false_negatives = []
    false_positives = []
    borderline_scores = {}   # case_id → [score, ...]

    for case in VALIDATOR_CASES:
        is_borderline = case["category"] == "borderline"
        runs_n = consistency_runs if is_borderline else 1

        _sub(f"{case['id']} [{case['category'].upper()}] — {case['label']}")

        runs = []
        for r in range(runs_n):
            res = _eval_validator_case(case, run_num=r+1)
            runs.append(res)
            if runs_n > 1:
                g_icon = G+"✓"+RST if res["gate_match"] else R+"✗"+RST
                s_icon = G+"✓"+RST if res["score_in_range"] else Y+"~"+RST
                print(f"    run {r+1}: gate={res['gate']} ({g_icon})  "
                      f"score={res['score']} [{res['exp_score']}] ({s_icon})")
            if is_borderline:
                borderline_scores.setdefault(case["id"], []).append(res["score"])

        res = runs[0]
        all_results.append(res)

        # ── Gate result ───────────────────────────────────────────────────────
        g_icon = f"{G}✓{RST}" if res["gate_match"] else f"{R}✗{RST}"
        print(f"    {g_icon}  gate:         got={res['gate']:5}  expected={res['exp_gate']}")

        # ── Score result ──────────────────────────────────────────────────────
        s_icon = f"{G}✓{RST}" if res["score_in_range"] else f"{Y}~{RST}"
        print(f"    {s_icon}  score:        got={res['score']:3}   expected={res['exp_score']}")

        # ── False negative warning (most critical) ────────────────────────────
        if res["false_negative"]:
            false_negatives.append(res)
            print(f"    {R}⚠  FALSE NEGATIVE — violating content passed compliance gate!{RST}")

        if res["false_positive"]:
            false_positives.append(res)
            print(f"    {Y}⚠  FALSE POSITIVE — compliant content was blocked{RST}")

        # ── Issue keyword checks (BLOCK cases) ───────────────────────────────
        if res["kw_found"]:
            kw_ok  = [kw for kw, found in res["kw_found"].items() if found]
            kw_bad = [kw for kw, found in res["kw_found"].items() if not found]
            if kw_ok:
                print(f"    {G}✓{RST}  issues mention: {', '.join(kw_ok)}")
            if kw_bad:
                print(f"    {Y}~{RST}  issues missing keywords: {', '.join(kw_bad)}")

        # ── Issues detail (BLOCK cases) ───────────────────────────────────────
        if res["issues"]:
            for iss in res["issues"]:
                sev_colour = R if iss.severity == "error" else Y
                print(f"         {sev_colour}[{iss.severity}]{RST} {iss.field}: {DIM}{iss.message[:90]}{RST}")

        # ── Tokens ────────────────────────────────────────────────────────────
        usage = res.get("usage", {})
        if usage:
            inp, out = usage.get("input_tokens",0), usage.get("output_tokens",0)
            print(f"    {DIM}tokens: {inp} in / {out} out  ({res['elapsed']}s){RST}")
            token_costs.append({"in": inp, "out": out})

        # ── Borderline consistency ────────────────────────────────────────────
        if is_borderline and runs_n > 1:
            scores = borderline_scores.get(case["id"], [])
            gates  = [r["gate"] for r in runs]
            gate_stable = len(set(gates)) == 1
            score_stdev = statistics.stdev(scores) if len(scores) > 1 else 0
            g_icon = f"{G}✓{RST}" if gate_stable else f"{R}✗{RST}"
            s_icon = f"{G}✓{RST}" if score_stdev <= 5 else f"{Y}~{RST}"
            print(f"    {g_icon}  gate stability: {set(gates)}  "
                  f"{s_icon}  score σ={score_stdev:.1f}")

    # ── Aggregate summary ─────────────────────────────────────────────────────
    _hdr("VALIDATOR — AGGREGATE METRICS")

    cats = {"clear_pass": [], "clear_block": [], "borderline": []}
    for r in all_results:
        cats[r["category"]].append(r)

    print(f"\n  {'Category':<16} {'Cases':<7} {'Gate Acc':<10} {'Score Acc':<10} {'FN':<5} {'FP':<5}")
    print(f"  {'─'*16} {'─'*7} {'─'*10} {'─'*10} {'─'*5} {'─'*5}")

    total_gm, total_sm, total_n = 0, 0, 0
    for cat, results in cats.items():
        if not results:
            continue
        n      = len(results)
        gm     = sum(r["gate_match"]     for r in results)
        sm     = sum(r["score_in_range"] for r in results)
        fn     = sum(r["false_negative"] for r in results)
        fp     = sum(r["false_positive"] for r in results)
        gm_pct = 100 * gm / n
        sm_pct = 100 * sm / n
        gc     = G if gm_pct >= 90 else (Y if gm_pct >= 70 else R)
        sc     = G if sm_pct >= 90 else (Y if sm_pct >= 70 else R)
        fn_c   = (R if fn > 0 else G)
        fp_c   = (Y if fp > 0 else G)
        print(f"  {cat:<16} {n:<7} {gc}{gm_pct:6.0f}%{RST}    {sc}{sm_pct:6.0f}%{RST}    "
              f"{fn_c}{fn}{RST}    {fp_c}{fp}{RST}")
        total_gm += gm; total_sm += sm; total_n += n

    overall_gate_pct  = 100 * total_gm / total_n if total_n else 0
    overall_score_pct = 100 * total_sm / total_n if total_n else 0
    gc = G if overall_gate_pct  >= 90 else (Y if overall_gate_pct  >= 70 else R)
    sc = G if overall_score_pct >= 90 else (Y if overall_score_pct >= 70 else R)
    print(f"  {'OVERALL':<16} {total_n:<7} {gc}{overall_gate_pct:6.0f}%{RST}    "
          f"{sc}{overall_score_pct:6.0f}%{RST}")

    # ── False negative highlight ──────────────────────────────────────────────
    if false_negatives:
        print(f"\n  {R}⚠  FALSE NEGATIVES ({len(false_negatives)}) — review immediately:{RST}")
        for r in false_negatives:
            print(f"     {r['id']}: {r['label']}")
            print(f"            score={r['score']}  summary: {r['summary'][:80]}")
    else:
        print(f"\n  {G}✓  No false negatives — all violating content correctly blocked{RST}")

    if false_positives:
        print(f"\n  {Y}~  FALSE POSITIVES ({len(false_positives)}) — good content being blocked:{RST}")
        for r in false_positives:
            print(f"     {r['id']}: {r['label']}  score={r['score']}")
    else:
        print(f"  {G}✓  No false positives{RST}")

    # ── Borderline score variance ─────────────────────────────────────────────
    if borderline_scores and consistency_runs > 1:
        print(f"\n  Borderline score variance (target σ ≤ 5):")
        for cid, scores in borderline_scores.items():
            stdev = statistics.stdev(scores) if len(scores) > 1 else 0
            icon  = G+"✓"+RST if stdev <= 5 else Y+"~"+RST
            print(f"    {icon}  {cid}: scores={scores}  σ={stdev:.1f}")

    if token_costs:
        avg_in  = statistics.mean(c["in"]  for c in token_costs)
        avg_out = statistics.mean(c["out"] for c in token_costs)
        print(f"\n  Avg tokens per validation: {avg_in:.0f} in / {avg_out:.0f} out")

    return overall_gate_pct


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="HerKey AI Agent Eval Suite")
    parser.add_argument("--agent", choices=["extractor","validator","both"], default="both")
    parser.add_argument("--consistency", type=int, default=1,
                        help="Re-run each borderline/all case N times (default 1)")
    args = parser.parse_args()

    print(f"\n{W}HerKey AI Agent Eval Suite{RST}")
    print(f"{DIM}Cases: {len(EXTRACTOR_CASES)} extractor | {len(VALIDATOR_CASES)} validator{RST}")
    if args.consistency > 1:
        print(f"{DIM}Consistency runs: {args.consistency} (borderline validator cases){RST}")

    scores = {}
    t_start = time.time()

    if args.agent in ("extractor","both"):
        scores["extractor"] = run_extractor_eval(consistency_runs=args.consistency)

    if args.agent in ("validator","both"):
        scores["validator"] = run_validator_eval(consistency_runs=args.consistency)

    # ── Final scorecard ───────────────────────────────────────────────────────
    _hdr("FINAL SCORECARD")
    elapsed_total = time.time() - t_start
    for agent, score in scores.items():
        colour = G if score >= 90 else (Y if score >= 70 else R)
        bar_len = int(score / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"\n  {agent.upper():<12}  {colour}{bar}  {score:5.1f}%{RST}")

    print(f"\n  Total eval time: {elapsed_total:.1f}s")

    # Exit non-zero if any critical metric below threshold
    if any(s < 70 for s in scores.values()):
        print(f"\n{R}  EVAL FAILED — one or more agents below 70% threshold{RST}\n")
        sys.exit(1)
    else:
        print(f"\n{G}  EVAL PASSED{RST}\n")


if __name__ == "__main__":
    main()
