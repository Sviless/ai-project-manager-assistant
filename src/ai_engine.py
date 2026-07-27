"""
ai_engine.py
------------
The "brains" of the app. Turns a small set of user inputs into a full set of
project-management artifacts.

Two modes, one interface
========================
Every engine implements the same tiny interface so the UI and database never
need to change:

    engine = get_engine()                    # picks the mode automatically
    outputs = engine.generate_all(project)   # dict[str, str] of Markdown

- **Mock mode** (`MockAIEngine`) — deterministic local templates + rules.
  No API key, no network, always available. This is the default.
- **LLM mode** (`LLMEngine`) — calls a real model through a pluggable
  `LLMProvider` (see `src/providers.py`). Enabled automatically **only** when
  the `LLM_API_KEY` environment variable is set.

`get_engine()` reads the environment and returns the LLM engine when a key is
configured, otherwise the mock engine. No keys are ever hard-coded, and LLM
mode is never required to run the app.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Protocol

from .analytics import compute_health, risks_from_inputs
from .providers import LLMProvider, get_provider
from .templates import ARTIFACTS, ARTIFACT_KEYS, INPUT_FIELDS
from .utils import clean_lines, parse_date, safe_get, today_iso


# ---------------------------------------------------------------------------
# Engine interface
# ---------------------------------------------------------------------------
class AIEngine(Protocol):
    """Any generation backend must implement this interface."""

    def generate_all(self, project: dict[str, str]) -> dict[str, str]:
        """Return a dict mapping artifact keys -> Markdown strings."""
        ...


# ---------------------------------------------------------------------------
# Mock (offline) engine
# ---------------------------------------------------------------------------
class MockAIEngine:
    """
    Deterministic, offline generator.

    Produces realistic, useful project-management content from the user's
    inputs using string templates and light heuristics.
    """

    def generate_all(self, project: dict[str, str]) -> dict[str, str]:
        """Generate every artifact and return them keyed by artifact key."""
        generators = {
            "charter": self._charter,
            "scope": self._scope,
            "milestones": self._milestones,
            "wbs": self._wbs,
            "raid": self._raid,
            "risk_register": self._risk_register,
            "actions": self._actions,
            "raci": self._raci,
            "comms": self._comms,
            "status": self._status,
            "exec_summary": self._exec_summary,
            "agenda": self._agenda,
            "lessons": self._lessons,
            "resume": self._resume,
        }
        # Preserve the canonical order defined in templates.ARTIFACT_KEYS.
        return {key: generators[key](project) for key in ARTIFACT_KEYS}

    # -- Individual artifact generators -------------------------------------

    def _charter(self, p: dict[str, str]) -> str:
        name = safe_get(p, "project_name", "Untitled Project")
        objective = safe_get(p, "objective", "TBD")
        problem = safe_get(p, "business_problem", "TBD")
        benefits = safe_get(p, "expected_benefits", "TBD")
        target = safe_get(p, "target_date", "TBD")
        sponsor = _first_stakeholder(p) or "TBD"
        return (
            f"# Project Charter — {name}\n\n"
            f"**Date:** {today_iso()}  \n"
            f"**Sponsor:** {sponsor}  \n"
            f"**Target Completion:** {target}\n\n"
            f"## Purpose\n{objective}\n\n"
            f"## Business Problem\n{problem}\n\n"
            f"## Objectives\n"
            f"- Deliver a solution that directly addresses the stated business problem.\n"
            f"- Achieve measurable outcomes by the target completion date.\n"
            f"- Maintain alignment with stakeholder expectations throughout delivery.\n\n"
            f"## Expected Benefits\n{benefits}\n\n"
            f"## High-Level Approach\n"
            f"1. Confirm requirements and success criteria with stakeholders.\n"
            f"2. Design and validate the solution in small increments.\n"
            f"3. Pilot, gather feedback, and iterate.\n"
            f"4. Roll out, measure impact, and hand off to operations.\n\n"
            f"## Authorization\nThis charter authorizes the project team to begin planning and "
            f"execution within the defined constraints."
        )

    def _scope(self, p: dict[str, str]) -> str:
        objective = safe_get(p, "objective", "the stated objective")
        constraints = safe_get(p, "constraints", "None specified")
        return (
            "# Scope Statement\n\n"
            "## In Scope\n"
            f"- Activities required to achieve: {objective}.\n"
            "- Requirements gathering, solution design, and stakeholder review.\n"
            "- Implementation, testing, and validation of the agreed solution.\n"
            "- Training and documentation for end users.\n\n"
            "## Out of Scope\n"
            "- Work not directly tied to the stated objective.\n"
            "- Long-term maintenance beyond the initial handoff period.\n"
            "- Unbudgeted tooling or additional headcount.\n\n"
            "## Constraints\n"
            f"{constraints}\n\n"
            "## Acceptance Criteria\n"
            "- Deliverables meet the agreed success criteria.\n"
            "- Stakeholders formally sign off on the final output.\n"
        )

    def _milestones(self, p: dict[str, str]) -> str:
        target = parse_date(safe_get(p, "target_date"))
        start = date.today()
        # Distribute milestones across the timeline between now and target.
        if target and target > start:
            span = (target - start).days
        else:
            span = 84  # default ~12 weeks
        points = [
            ("Project Kickoff", 0.0, "Charter approved and team aligned."),
            ("Requirements Baseline", 0.15, "Requirements and success criteria confirmed."),
            ("Design Complete", 0.35, "Solution design reviewed and approved."),
            ("Build / Pilot", 0.60, "Initial solution built and piloted."),
            ("Validation & UAT", 0.80, "Testing complete and feedback incorporated."),
            ("Go-Live / Handoff", 1.0, "Solution rolled out and transitioned to operations."),
        ]
        rows = ["| Milestone | Target Date | Description |", "|---|---|---|"]
        for label, frac, desc in points:
            due = start + timedelta(days=int(span * frac))
            rows.append(f"| {label} | {due.isoformat()} | {desc} |")
        return "# Key Milestones\n\n" + "\n".join(rows)

    def _wbs(self, p: dict[str, str]) -> str:
        name = safe_get(p, "project_name", "Project")
        objective = safe_get(p, "objective")

        # Turn the user's expected benefits into concrete deliverable work
        # packages under Execution. Fall back to a generic build when none
        # are provided so the WBS is always complete.
        benefits = clean_lines(safe_get(p, "expected_benefits"))
        if benefits:
            execution_items = [
                f"  - 1.3.{i} Deliver: {benefit}"
                for i, benefit in enumerate(benefits, start=1)
            ]
        else:
            execution_items = [
                "  - 1.3.1 Design solution",
                "  - 1.3.2 Build / configure solution",
                "  - 1.3.3 Develop training and documentation",
            ]

        header = f"**1. {name}**"
        if objective:
            header += f"\n\n*Goal: {objective}*"

        lines = [
            "# Work Breakdown Structure (WBS)",
            "",
            header,
            "",
            "- **1.1 Initiation**",
            "  - 1.1.1 Develop project charter",
            "  - 1.1.2 Identify stakeholders",
            "  - 1.1.3 Secure sponsor approval",
            "- **1.2 Planning**",
            "  - 1.2.1 Gather requirements",
            "  - 1.2.2 Define scope and success criteria",
            "  - 1.2.3 Build schedule and resource plan",
            "- **1.3 Execution**",
            *execution_items,
            "- **1.4 Monitoring & Control**",
            "  - 1.4.1 Track progress and risks",
            "  - 1.4.2 Manage stakeholder communication",
            "  - 1.4.3 Validate quality and acceptance",
            "- **1.5 Closure**",
            "  - 1.5.1 Pilot and go-live",
            "  - 1.5.2 Hand off to operations",
            "  - 1.5.3 Capture lessons learned",
        ]
        return "\n".join(lines) + "\n"

    def _raid(self, p: dict[str, str]) -> str:
        # Reuse the shared risk scoring model so RAID and the Risk Register
        # stay consistent. Map the 1–5 probability/impact to short labels.
        scored = risks_from_inputs(p)

        def label(value: int) -> str:
            return "High" if value >= 4 else ("Medium" if value == 3 else "Low")

        risk_rows = ["| Risk | Likelihood | Impact | Mitigation |", "|---|---|---|---|"]
        for r in scored:
            risk_rows.append(
                f"| {r['risk']} | {label(r['probability'])} | "
                f"{label(r['impact'])} | {r['mitigation']} |"
            )

        assumptions = [
            "Stakeholders are available for reviews and decisions.",
            "Existing tools and resources remain available for the duration.",
            "Requirements will remain reasonably stable after baseline.",
        ]
        issues = ["No open issues at project start."]
        dependencies = clean_lines(safe_get(p, "resources")) or [
            "Availability of key resources and tooling."
        ]

        out = ["# RAID Log\n", "## Risks", "\n".join(risk_rows), "\n## Assumptions"]
        out += [f"- {a}" for a in assumptions]
        out += ["\n## Issues"] + [f"- {i}" for i in issues]
        out += ["\n## Dependencies"] + [f"- {d}" for d in dependencies]
        return "\n".join(out)

    def _risk_register(self, p: dict[str, str]) -> str:
        """Scored risk register: probability × impact → score → risk level."""
        scored = risks_from_inputs(p)
        rows = [
            "| # | Risk | Probability (1–5) | Impact (1–5) | Score | Risk Level | Mitigation |",
            "|---|---|---|---|---|---|---|",
        ]
        for i, r in enumerate(scored, start=1):
            rows.append(
                f"| {i} | {r['risk']} | {r['probability']} | {r['impact']} | "
                f"{r['score']} | {r['level_label']} | {r['mitigation']} |"
            )

        critical = [r for r in scored if r["level"] == "Critical"]
        high = [r for r in scored if r["level"] == "High"]
        top = scored[0] if scored else None

        summary = (
            "## Scoring Model\n"
            "Risk **Score = Probability × Impact** (each rated 1–5, so 1–25). "
            "Levels: 🟢 Low (1–3), 🟡 Medium (4–8), 🟠 High (9–14), 🔴 Critical (15–25).\n\n"
            "## Summary\n"
            f"- Total risks scored: **{len(scored)}**\n"
            f"- Critical: **{len(critical)}**, High: **{len(high)}**\n"
        )
        if top:
            summary += f"- Highest-scoring risk: **{top['risk']}** (score {top['score']}, {top['level']}).\n"

        return "# Risk Register\n\n" + summary + "\n## Scored Risks\n\n" + "\n".join(rows)


    def _actions(self, p: dict[str, str]) -> str:
        owner = _first_stakeholder(p) or "Project Lead"
        start = date.today()

        def due(days: int) -> str:
            return (start + timedelta(days=days)).isoformat()

        rows = [
            "| # | Action Item | Owner | Due Date | Priority | Status |",
            "|---|---|---|---|---|---|",
            f"| 1 | Finalize and approve project charter | {owner} | {due(3)} | High | Open |",
            f"| 2 | Confirm requirements with stakeholders | {owner} | {due(10)} | High | Open |",
            f"| 3 | Draft solution design | Project Team | {due(21)} | Medium | Open |",
            f"| 4 | Set up communication cadence | {owner} | {due(5)} | Medium | Open |",
            f"| 5 | Build project schedule | {owner} | {due(14)} | Medium | Open |",
            f"| 6 | Identify and log key risks | Project Team | {due(7)} | High | Open |",
        ]
        return "# Action Item List\n\n" + "\n".join(rows)

    def _raci(self, p: dict[str, str]) -> str:
        """Build a RACI matrix: activities (rows) × roles (columns)."""
        roles = _raci_roles(p)
        n = len(roles)
        activities = [
            "Project Charter & Approval",
            "Requirements Gathering",
            "Solution Design",
            "Build / Configuration",
            "Testing & Validation",
            "Training & Documentation",
            "Go-Live / Deployment",
            "Lessons Learned & Closure",
        ]

        header = "| Activity | " + " | ".join(roles) + " |"
        separator = "|---|" + "---|" * n
        rows = [header, separator]
        for i, activity in enumerate(activities):
            # Role 0 (sponsor/lead) is Accountable; one other role is
            # Responsible (rotating); the rest are Consulted / Informed.
            responsible = 1 + (i % (n - 1)) if n > 1 else 0
            cells = []
            for j in range(n):
                if n == 1:
                    cells.append("A/R")
                elif j == 0:
                    cells.append("A")
                elif j == responsible:
                    cells.append("R")
                else:
                    cells.append("C" if (i + j) % 2 == 0 else "I")
            rows.append(f"| {activity} | " + " | ".join(cells) + " |")

        legend = (
            "**Legend:** **R** = Responsible (does the work) · "
            "**A** = Accountable (owns the outcome) · "
            "**C** = Consulted (provides input) · "
            "**I** = Informed (kept up to date)."
        )
        return "# RACI Matrix\n\n" + legend + "\n\n" + "\n".join(rows)


    def _comms(self, p: dict[str, str]) -> str:
        stakeholders = clean_lines(safe_get(p, "stakeholders"))
        if not stakeholders:
            stakeholders = ["Sponsor", "Project Team", "End Users"]
        rows = [
            "| Audience | Message | Channel | Frequency | Owner |",
            "|---|---|---|---|---|",
        ]
        cadence = [
            ("Executive summary of status & risks", "Email / Dashboard", "Bi-weekly"),
            ("Progress, blockers, next steps", "Standup / Chat", "Weekly"),
            ("Change announcements & training", "Email / Meeting", "As needed"),
        ]
        for i, sh in enumerate(stakeholders):
            msg, channel, freq = cadence[i % len(cadence)]
            rows.append(f"| {sh} | {msg} | {channel} | {freq} | Project Lead |")
        return "# Stakeholder Communication Plan\n\n" + "\n".join(rows)

    def _status(self, p: dict[str, str]) -> str:
        name = safe_get(p, "project_name", "Project")
        objective = safe_get(p, "objective", "TBD")
        target = safe_get(p, "target_date", "TBD")
        return (
            f"# Executive Status Summary — {name}\n\n"
            f"**Reporting Date:** {today_iso()}  \n"
            f"**Overall Status:** 🟢 On Track  \n"
            f"**Target Completion:** {target}\n\n"
            f"## Objective\n{objective}\n\n"
            "## Highlights\n"
            "- Project initiated and charter drafted.\n"
            "- Stakeholders identified and engaged.\n"
            "- Planning underway; schedule being finalized.\n\n"
            "## Key Risks\n"
            "- Being actively tracked in the RAID log; no critical blockers at this time.\n\n"
            "## Next Steps\n"
            "- Confirm requirements baseline.\n"
            "- Finalize schedule and resource plan.\n"
        )

    def _exec_summary(self, p: dict[str, str]) -> str:
        """A single-page executive briefing with health and top risks."""
        name = safe_get(p, "project_name", "Project")
        objective = safe_get(p, "objective", "TBD")
        problem = safe_get(p, "business_problem", "TBD")
        benefits = safe_get(p, "expected_benefits", "TBD")
        target = safe_get(p, "target_date", "TBD")
        sponsor = _first_stakeholder(p) or "TBD"

        health = compute_health(p)
        scored = risks_from_inputs(p)
        top = scored[:3]

        risk_lines = ["| Top Risk | Score | Level |", "|---|---|---|"]
        for r in top:
            risk_lines.append(f"| {r['risk']} | {r['score']} | {r['level_label']} |")

        reasons = "; ".join(health["reasons"])

        return (
            f"# Executive One-Page Summary — {name}\n\n"
            f"**Date:** {today_iso()}  |  **Sponsor:** {sponsor}  |  "
            f"**Target:** {target}\n\n"
            f"## Project Health: {health['label']}\n"
            f"_{reasons}_\n\n"
            f"## Objective\n{objective}\n\n"
            f"## Business Problem\n{problem}\n\n"
            f"## Expected Benefits\n{benefits}\n\n"
            f"## Top Risks\n" + "\n".join(risk_lines) + "\n\n"
            "## Recommendation / Ask\n"
            "- Confirm sponsor support and resource commitments.\n"
            "- Approve the plan to proceed into execution.\n"
        )


    def _agenda(self, p: dict[str, str]) -> str:
        name = safe_get(p, "project_name", "Project")
        return (
            f"# Kickoff Meeting Agenda — {name}\n\n"
            f"**Date:** {today_iso()}  |  **Duration:** 60 minutes\n\n"
            "| Time | Topic | Lead |\n"
            "|---|---|---|\n"
            "| 0:00–0:05 | Welcome & introductions | Project Lead |\n"
            "| 0:05–0:15 | Project purpose & objectives | Sponsor |\n"
            "| 0:15–0:25 | Scope & success criteria | Project Lead |\n"
            "| 0:25–0:35 | Roles, responsibilities & RACI | Project Lead |\n"
            "| 0:35–0:45 | Timeline & key milestones | Project Lead |\n"
            "| 0:45–0:55 | Risks, dependencies & open questions | Team |\n"
            "| 0:55–1:00 | Next steps & action items | Project Lead |\n\n"
            "## Desired Outcomes\n"
            "- Shared understanding of goals and scope.\n"
            "- Agreement on roles and communication cadence.\n"
            "- Clear owners for immediate next actions.\n"
        )

    def _lessons(self, p: dict[str, str]) -> str:
        """A lessons-learned template, lightly tailored to the project."""
        name = safe_get(p, "project_name", "the project")
        benefits = safe_get(p, "expected_benefits", "the intended benefits")
        return (
            "# Lessons Learned\n\n"
            f"Retrospective notes for **{name}**. Capture these during and after "
            "delivery to improve future projects.\n\n"
            "## What Went Well\n"
            "- Clear objective and business problem defined up front.\n"
            "- Stakeholders engaged early with a shared communication cadence.\n"
            "- Risks were scored and tracked, enabling proactive mitigation.\n\n"
            "## What Could Be Improved\n"
            "- Tighten estimates for scope that carried schedule risk.\n"
            "- Increase user involvement earlier to smooth adoption.\n"
            "- Validate legacy/source data sooner to reduce rework.\n\n"
            "## Recommendations for Future Projects\n"
            f"- Reuse this artifact package as a starting template to reach {benefits.lower() if benefits else 'target outcomes'} faster.\n"
            "- Keep the risk register and RACI matrix current as the plan evolves.\n"
            "- Hold a short retrospective at each milestone, not only at closure.\n\n"
            "## Categorized Notes\n"
            "| Category | Observation | Action for Next Time |\n"
            "|---|---|---|\n"
            "| Process | Structured artifacts sped up planning | Standardize the template |\n"
            "| People | Early stakeholder buy-in helped | Formalize a RACI at kickoff |\n"
            "| Technology | Existing tooling was sufficient | Confirm integrations earlier |\n"
            "| Communication | Regular cadence reduced surprises | Keep executive summaries concise |\n"
        )


    def _resume(self, p: dict[str, str]) -> str:
        name = safe_get(p, "project_name", "a cross-functional initiative")
        benefits = safe_get(p, "expected_benefits", "measurable operational improvements")
        return (
            "# Resume Achievement Summary\n\n"
            "Use or adapt these bullets for your resume / LinkedIn:\n\n"
            f"- Led **{name}** from concept to delivery, translating an ambiguous business "
            f"problem into a structured project plan (charter, scope, WBS, and RAID log).\n"
            f"- Delivered {benefits.lower() if benefits else 'measurable improvements'}, "
            "improving operational efficiency and stakeholder visibility.\n"
            "- Built and maintained a stakeholder communication plan and executive status "
            "reporting cadence, keeping leadership aligned throughout delivery.\n"
            "- Managed risks, dependencies, and action items to keep the initiative on track "
            "against a fixed timeline and constraints.\n"
        )


# ---------------------------------------------------------------------------
# LLM (online) engine — used only when LLM_API_KEY is configured
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = (
    "You are an expert project manager and PMO consultant. You write clear, "
    "concise, professional project-management artifacts in GitHub-flavored "
    "Markdown. Use headings, bullet points, and tables where they improve "
    "readability. Do not invent confidential details; when information is "
    "missing, use reasonable, generic placeholders."
)

# Extra, artifact-specific guidance so LLM output matches the app's structure.
_ARTIFACT_HINTS: dict[str, str] = {
    "milestones": "Present milestones as a Markdown table: Milestone | Target Date | Description.",
    "risk_register": (
        "Score each risk with Probability (1-5) and Impact (1-5); compute "
        "Score = Probability × Impact and a Risk Level (Low 1-3, Medium 4-8, "
        "High 9-14, Critical 15-25). Use a Markdown table and add a short summary."
    ),
    "raci": (
        "Produce a RACI matrix as a Markdown table with project activities as "
        "rows and stakeholder roles as columns; each cell is R, A, C, or I. "
        "Include a one-line legend."
    ),
    "actions": "Use a Markdown table: # | Action Item | Owner | Due Date | Priority | Status.",
    "comms": "Use a Markdown table: Audience | Message | Channel | Frequency | Owner.",
    "exec_summary": "Keep it to a single page with a Green/Yellow/Red health call-out and top risks.",
    "resume": "Provide 3-5 achievement-oriented resume bullets.",
}


class LLMEngine:
    """
    Generation engine backed by a real model via an `LLMProvider`.

    It builds one prompt per artifact (using the shared templates metadata) so
    the output set matches mock mode exactly: the same keys, in the same order.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.model = getattr(provider, "model", "")

    def generate_all(self, project: dict[str, str]) -> dict[str, str]:
        inputs_block = _format_inputs(project)
        outputs: dict[str, str] = {}
        for key, label, description in ARTIFACTS:
            prompt = _artifact_prompt(inputs_block, key, label, description)
            content = self.provider.complete(_SYSTEM_PROMPT, prompt).strip()
            outputs[key] = content or f"# {label}\n\n_(No content was returned by the model.)_"
        return outputs


# ---------------------------------------------------------------------------
# Factory + status
# ---------------------------------------------------------------------------
def get_engine(mode: str = "auto") -> AIEngine:
    """
    Return the active generation engine.

    ``mode`` controls which engine is used:
    - ``"mock"`` : always returns the offline ``MockAIEngine``.
    - ``"llm"``  : returns an ``LLMEngine`` if an API key/provider is
      configured; otherwise raises ``RuntimeError`` explaining what to do.
    - ``"auto"`` (default): uses the LLM when a provider is configured,
      falling back to the offline ``MockAIEngine`` when no key is set.

    LLM mode is never required; with no key, the app runs fully in mock mode.
    """
    if mode == "mock":
        return MockAIEngine()

    provider = get_provider()
    if provider is not None:
        return LLMEngine(provider)

    if mode == "llm":
        raise RuntimeError(
            "LLM Mode is selected but no API key is configured. Add LLM_API_KEY "
            "to your .env file (see .env.example), or switch to Local Mock Mode."
        )
    return MockAIEngine()


def engine_status(mode: str = "auto") -> dict[str, str | None]:
    """
    Describe the engine that ``mode`` would produce, for display in the UI.

    Returns a dict: {"mode": "mock"|"llm"|"error", "provider": str|None,
    "model": str|None}. Never raises — misconfiguration or a missing key while
    LLM Mode is selected is reported as an "error" mode instead.
    """
    if mode == "mock":
        return {"mode": "mock", "provider": None, "model": None}

    try:
        provider = get_provider()
    except ValueError as exc:
        return {"mode": "error", "provider": None, "model": None, "error": str(exc)}

    if provider is None:
        if mode == "llm":
            return {
                "mode": "error",
                "provider": None,
                "model": None,
                "error": "No API key configured (set LLM_API_KEY).",
            }
        return {"mode": "mock", "provider": None, "model": None}

    return {
        "mode": "llm",
        "provider": provider.name,
        "model": getattr(provider, "model", None),
    }



# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _format_inputs(project: dict[str, str]) -> str:
    """Render the user's inputs as a readable block for LLM prompts."""
    lines: list[str] = []
    for key, label, _help, _required in INPUT_FIELDS:
        value = safe_get(project, key)
        if value:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines) if lines else "- (No details provided.)"


def _artifact_prompt(inputs_block: str, key: str, label: str, description: str) -> str:
    """Build the per-artifact user prompt for LLM mode."""
    hint = _ARTIFACT_HINTS.get(key, "")
    hint_line = f"\nFormatting guidance: {hint}" if hint else ""
    return (
        f"Project details:\n{inputs_block}\n\n"
        f"Produce the **{label}** ({description}).{hint_line}\n\n"
        f"Return only the Markdown for this single artifact, starting with a "
        f"level-1 heading (# {label})."
    )


def _first_stakeholder(p: dict[str, str]) -> str:
    """Return the first listed stakeholder (name portion), if any."""
    items = clean_lines(safe_get(p, "stakeholders"))
    if not items:
        return ""
    # Support "Name — Role" or "Name - Role" formats; keep the name part.
    first = items[0]
    for sep in ("—", " - ", "–", ":"):
        if sep in first:
            return first.split(sep)[0].strip()
    return first


def _raci_roles(p: dict[str, str]) -> list[str]:
    """
    Derive short RACI column labels from the stakeholders list.

    Uses the role part of "Name — Role" entries when present, otherwise the
    name. Falls back to a sensible default set and caps the number of columns
    so the matrix stays readable.
    """
    items = clean_lines(safe_get(p, "stakeholders"))
    roles: list[str] = []
    for entry in items:
        role = entry
        for sep in ("—", " - ", "–", ":"):
            if sep in entry:
                role = entry.split(sep)[-1].strip()
                break
        if role and role not in roles:
            roles.append(role)
    if not roles:
        roles = ["Sponsor", "Project Lead", "Project Team", "End Users"]
    return roles[:5]
