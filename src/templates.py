"""
templates.py
------------
Central place for artifact metadata and reusable text scaffolding.

Keeping the list of artifacts here (instead of hard-coding it in the UI or
engine) means you can add / reorder / rename outputs in ONE place and every
other module picks up the change automatically.
"""

from __future__ import annotations

# Canonical, ordered list of the 10 artifacts the app produces.
# Each entry: (key, human-friendly label, short description).
ARTIFACTS: list[tuple[str, str, str]] = [
    ("charter", "Project Charter", "High-level authorization and overview of the project."),
    ("scope", "Scope Statement", "What is in scope and explicitly out of scope."),
    ("milestones", "Key Milestones", "Major checkpoints with target dates."),
    ("wbs", "Work Breakdown Structure (WBS)", "Deliverables broken into work packages."),
    ("raid", "RAID Log", "Risks, Assumptions, Issues, and Dependencies."),
    ("risk_register", "Risk Register", "Scored risks with probability, impact, and risk level."),
    ("actions", "Action Item List", "Tasks with owner, due date, priority, and status."),
    ("raci", "RACI Matrix", "Responsible, Accountable, Consulted, Informed by activity."),
    ("comms", "Stakeholder Communication Plan", "Who is informed, how, and how often."),
    ("status", "Executive Status Summary", "Detailed status update for leadership."),
    ("exec_summary", "Executive One-Page Summary", "Single-page briefing with health and top risks."),
    ("agenda", "Kickoff Meeting Agenda", "Structured agenda for the project kickoff."),
    ("lessons", "Lessons Learned", "What went well, what to improve, and recommendations."),
    ("resume", "Resume Achievement Summary", "Resume-ready bullets describing the impact."),
]

# Convenience lookups derived from ARTIFACTS.
ARTIFACT_KEYS: list[str] = [key for key, _, _ in ARTIFACTS]
ARTIFACT_LABELS: dict[str, str] = {key: label for key, label, _ in ARTIFACTS}
ARTIFACT_DESCRIPTIONS: dict[str, str] = {key: desc for key, _, desc in ARTIFACTS}


# The input fields expected from the user. Used to render the form and to
# validate / normalize incoming data.
# Each entry: (key, label, help_text, is_required).
INPUT_FIELDS: list[tuple[str, str, str, bool]] = [
    ("project_name", "Project Name", "A short, descriptive title for the project.", True),
    ("objective", "Project Objective", "The primary goal you want to achieve.", True),
    ("business_problem", "Business Problem", "The pain point or opportunity being addressed.", True),
    ("expected_benefits", "Expected Benefits", "Value delivered (cost savings, time, quality, etc.).", False),
    ("stakeholders", "Stakeholders", "One per line or comma-separated (name — role).", False),
    ("constraints", "Constraints", "Budget, time, scope, or resource limits.", False),
    ("target_date", "Target Completion Date", "When the project should be complete.", False),
    ("known_risks", "Known Risks", "One per line or comma-separated.", False),
    ("resources", "Available Resources", "People, tools, or budget available.", False),
]

INPUT_KEYS: list[str] = [key for key, _, _, _ in INPUT_FIELDS]
REQUIRED_KEYS: list[str] = [key for key, _, _, required in INPUT_FIELDS if required]


# Sample project used for the "Load Example" button and README documentation.
# 100% generic / fictional data — safe for a public portfolio.
SAMPLE_PROJECT: dict[str, str] = {
    "project_name": "Lab Inventory Automation Initiative",
    "objective": "Reduce manual inventory tracking effort and improve stock accuracy across the operations lab.",
    "business_problem": (
        "The lab currently tracks consumables and equipment in spreadsheets, "
        "causing stockouts, duplicate purchases, and hours of manual reconciliation each week."
    ),
    "expected_benefits": (
        "Save ~8 hours/week of manual effort, cut duplicate purchases by 20%, "
        "and provide real-time inventory visibility to stakeholders."
    ),
    "stakeholders": (
        "Operations Manager — Sponsor\n"
        "Lab Supervisor — Product Owner\n"
        "Procurement Lead — Reviewer\n"
        "Lab Technicians — End Users"
    ),
    "constraints": "Fixed 12-week timeline; no additional headcount; must use existing tooling budget.",
    "target_date": "2026-10-30",
    "known_risks": (
        "Low user adoption of the new tool\n"
        "Inaccurate legacy data during migration\n"
        "Limited technician availability for training"
    ),
    "resources": "1 process improvement lead, 2 part-time technicians, existing barcode scanners, cloud spreadsheet tools.",
}
