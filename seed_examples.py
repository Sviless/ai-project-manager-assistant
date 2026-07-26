"""
seed_examples.py
----------------
Populate the local SQLite database with **5 clearly-labeled example projects**
so you can immediately see the app in action — the Dashboard charts, the
History tab, saved artifacts, and exports — without filling in the form first.

Every example:
- Has a name prefixed with "[EXAMPLE]" so it is obvious in every view.
- Includes a note in its inputs stating it is sample/demonstration data.
- Uses 100% generic, fictional content (portfolio-safe).

The five projects are intentionally varied so the health model produces a mix
of 🟢 Green, 🟡 Yellow, and 🔴 Red statuses on the dashboard.

Run it from the project folder:

    python seed_examples.py            # add the examples (refreshes existing ones)
    python seed_examples.py --clear    # remove the examples and exit

Re-running is safe: existing "[EXAMPLE]" projects are removed first so you never
get duplicates.
"""

from __future__ import annotations

import sys
from pathlib import Path

from src.ai_engine import get_engine
from src.db import delete_project, list_projects, save_project

BASE_DIR = Path(__file__).parent
DB_PATH = str(BASE_DIR / "data" / "projects.db")

EXAMPLE_PREFIX = "[EXAMPLE]"

# A short note appended to each example's business problem so the sample nature
# is unmistakable wherever the inputs/artifacts are displayed.
_SAMPLE_NOTE = (
    "\n\nNote: This is a sample project included as an example to demonstrate "
    "how the app works. All details are generic and fictional."
)


# ---------------------------------------------------------------------------
# Example projects (varied risk profiles -> varied health statuses)
# ---------------------------------------------------------------------------
EXAMPLES: list[dict[str, str]] = [
    # 1) Healthy (🟢 Green): only minor risks, future date, complete info.
    {
        "project_name": f"{EXAMPLE_PREFIX} Customer Onboarding Portal Refresh",
        "objective": "Refresh the self-service onboarding portal to reduce support tickets and speed up new-customer setup.",
        "business_problem": "New customers struggle with a dated onboarding flow, creating avoidable support volume and slow time-to-value.",
        "expected_benefits": "Cut onboarding support tickets by 25% and reduce average setup time from 3 days to 1 day.",
        "stakeholders": (
            "Head of Customer Success — Sponsor\n"
            "Product Manager — Product Owner\n"
            "UX Designer — Contributor\n"
            "New Customers — End Users"
        ),
        "constraints": "10-week timeline; use the existing design system; no new vendor tooling.",
        "target_date": "2027-03-31",
        "known_risks": (
            "Minor cosmetic UI differences across browsers\n"
            "Low-priority copy and typo fixes needed before launch"
        ),
        "resources": "1 product manager, 1 designer, 2 front-end developers, existing design system.",
    },
    # 2) Watch (🟡 Yellow): a couple of elevated adoption/timeline risks.
    {
        "project_name": f"{EXAMPLE_PREFIX} Warehouse Barcode Scanning Rollout",
        "objective": "Roll out handheld barcode scanning to replace manual stock counts in the main warehouse.",
        "business_problem": "Manual counts are slow and error-prone, causing inventory discrepancies and shipping delays.",
        "expected_benefits": "Improve inventory accuracy to 99% and cut cycle-count time by 40%.",
        "stakeholders": (
            "Operations Director — Sponsor\n"
            "Warehouse Manager — Product Owner\n"
            "IT Support Lead — Reviewer\n"
            "Warehouse Staff — End Users"
        ),
        "constraints": "Must launch before peak season; fixed hardware budget; minimal downtime allowed.",
        "target_date": "2026-12-15",
        "known_risks": (
            "User adoption of the new scanners may be slow without training\n"
            "Tight timeline around the peak season could compress testing"
        ),
        "resources": "1 project lead, 2 warehouse supervisors, 50 handheld scanners, existing WMS.",
    },
    # 3) At risk (🔴 Red): multiple high/critical data + security risks.
    {
        "project_name": f"{EXAMPLE_PREFIX} Legacy CRM Data Migration",
        "objective": "Migrate customer records from the legacy CRM to the new cloud platform with zero data loss.",
        "business_problem": "The aging CRM is unsupported and blocks reporting; data must move to the new platform safely.",
        "expected_benefits": "Retire legacy licensing costs and enable unified reporting across teams.",
        "stakeholders": (
            "CIO — Sponsor\n"
            "Data Migration Lead — Product Owner\n"
            "Security Officer — Reviewer\n"
            "Sales & Support Teams — End Users"
        ),
        "constraints": "Hard cutover weekend; strict compliance requirements; limited migration window.",
        "target_date": "2026-11-30",
        "known_risks": (
            "Legacy data quality is poor and may require extensive cleaning\n"
            "Data migration cutover could cause system downtime\n"
            "Security and compliance review may surface gaps before go-live\n"
            "Limited resource availability during the cutover weekend"
        ),
        "resources": "1 migration lead, 2 data engineers, 1 security reviewer, cloud migration tooling.",
    },
    # 4) Watch (🟡 Yellow): only minor risks, but the target date is in the past.
    {
        "project_name": f"{EXAMPLE_PREFIX} Employee Wellness Program Launch",
        "objective": "Launch a company-wide wellness program with monthly activities and resources.",
        "business_problem": "Employee engagement survey scores dipped; a wellness program can improve morale and retention.",
        "expected_benefits": "Raise engagement scores by 10 points and increase program participation to 60%.",
        "stakeholders": (
            "HR Director — Sponsor\n"
            "People Programs Lead — Product Owner\n"
            "Facilities Coordinator — Contributor\n"
            "All Employees — Participants"
        ),
        "constraints": "Small budget; volunteer-run sessions; no dedicated headcount.",
        "target_date": "2026-05-15",
        "known_risks": (
            "Minor scheduling conflicts with facilitators\n"
            "Low turnout risk for optional sessions"
        ),
        "resources": "1 program lead, volunteer facilitators, existing meeting rooms, small activities budget.",
    },
    # 5) Healthy (🟢 Green): minor risks, future date, complete info.
    {
        "project_name": f"{EXAMPLE_PREFIX} Internal Analytics Dashboard",
        "objective": "Build a self-service analytics dashboard so managers can track key operational metrics.",
        "business_problem": "Managers wait on manual reports, delaying decisions and duplicating effort.",
        "expected_benefits": "Save ~5 hours/week of manual reporting and give managers real-time visibility.",
        "stakeholders": (
            "Operations VP — Sponsor\n"
            "Analytics Lead — Product Owner\n"
            "Data Analyst — Contributor\n"
            "Department Managers — End Users"
        ),
        "constraints": "8-week timeline; use existing BI tooling; read-only data access.",
        "target_date": "2027-01-31",
        "known_risks": (
            "Minor report formatting tweaks expected after review\n"
            "Low-impact edge cases in dashboard filters"
        ),
        "resources": "1 analytics lead, 1 data analyst, existing BI platform and data warehouse.",
    },
]


def clear_examples() -> int:
    """Delete any previously-seeded example projects. Returns count removed."""
    removed = 0
    for project in list_projects(DB_PATH):
        if project["name"].startswith(EXAMPLE_PREFIX):
            delete_project(DB_PATH, project["id"])
            removed += 1
    return removed


def seed_examples() -> int:
    """Generate and save the example projects. Returns count added."""
    engine = get_engine()
    added = 0
    for project in EXAMPLES:
        inputs = dict(project)
        inputs["business_problem"] = inputs["business_problem"] + _SAMPLE_NOTE
        outputs = engine.generate_all(inputs)
        save_project(DB_PATH, inputs["project_name"], inputs, outputs)
        added += 1
    return added


def main() -> None:
    if "--clear" in sys.argv:
        removed = clear_examples()
        print(f"Removed {removed} example project(s). Done.")
        return

    removed = clear_examples()
    if removed:
        print(f"Refreshing: removed {removed} existing example project(s).")

    added = seed_examples()
    print(f"Added {added} example projects to {DB_PATH}.")
    print("Open the app and check the 📊 Dashboard and 📚 History tabs.")


if __name__ == "__main__":
    main()
