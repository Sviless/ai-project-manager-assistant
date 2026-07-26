"""
utils.py
--------
Small, reusable helper functions used across the application.

Kept dependency-free (standard library only) so it can be imported
anywhere without side effects.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


def now_iso() -> str:
    """Return the current timestamp as an ISO-8601 string (seconds precision)."""
    return datetime.now().isoformat(timespec="seconds")


def today_iso() -> str:
    """Return today's date as a YYYY-MM-DD string."""
    return date.today().isoformat()


def slugify(text: str) -> str:
    """
    Convert an arbitrary string into a filesystem-safe slug.

    Example: "My Cool Project!" -> "my-cool-project"
    """
    text = (text or "untitled").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "untitled"


def clean_lines(raw: str) -> list[str]:
    """
    Split a multi-line / comma-separated text block into a clean list.

    Accepts input separated by newlines, commas, or semicolons and strips
    empty entries and surrounding whitespace.
    """
    if not raw:
        return []
    # Normalize separators to newlines, then split.
    normalized = re.sub(r"[;,]", "\n", raw)
    items = [line.strip(" \t-•*") for line in normalized.splitlines()]
    return [item for item in items if item]


def safe_get(data: dict[str, Any], key: str, default: str = "") -> str:
    """Return a stripped string value from a dict, falling back to a default."""
    value = data.get(key, default)
    if value is None:
        return default
    return str(value).strip()


def truncate(text: str, max_len: int = 120) -> str:
    """Truncate text with an ellipsis for compact display."""
    text = (text or "").strip()
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


def parse_date(value: str) -> date | None:
    """
    Best-effort parse of a date string in several common formats.

    Returns a `date` on success or `None` if the value is empty / unparseable.
    Accepts, e.g., 2026-10-30, 10/30/2026, 30-10-2026.
    """
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def validate_inputs(
    inputs: dict[str, Any],
    input_fields: list[tuple[str, str, str, bool]],
) -> tuple[list[str], list[str]]:
    """
    Validate user inputs before generation.

    Returns a tuple of (errors, warnings):
    - errors   : must be fixed before generating (e.g. missing required fields).
    - warnings : allowed, but worth flagging (e.g. a past target date).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1) Required fields must be present.
    for key, label, _, required in input_fields:
        if required and not str(inputs.get(key, "")).strip():
            errors.append(f"“{label}” is required.")

    # 2) Project name should be a sensible length.
    name = str(inputs.get("project_name", "")).strip()
    if name and len(name) < 3:
        errors.append("“Project Name” should be at least 3 characters long.")

    # 3) Target date, if provided, should be valid and not in the past.
    target_raw = str(inputs.get("target_date", "")).strip()
    if target_raw:
        parsed = parse_date(target_raw)
        if parsed is None:
            errors.append(
                "“Target Completion Date” should be a valid date, e.g. 2026-10-30."
            )
        elif parsed < date.today():
            warnings.append(
                "“Target Completion Date” is in the past — milestones will use a default 12-week timeline."
            )

    return errors, warnings
