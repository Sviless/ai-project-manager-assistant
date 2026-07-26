"""
exporters.py
------------
Turn generated project outputs into downloadable files.

Two formats are supported:
- Markdown : a single, nicely formatted document with all artifacts.
- CSV      : one row per artifact (artifact, content) for spreadsheet import.

These functions return strings/bytes so the Streamlit UI can offer them via
`st.download_button` without writing to disk. A `write_outputs_to_disk` helper
is also provided for the local `outputs/` folder.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from .templates import ARTIFACT_LABELS
from .utils import slugify, today_iso


def build_markdown(project_name: str, outputs: dict[str, str]) -> str:
    """
    Combine all artifacts into a single Markdown document with a header and
    table of contents.
    """
    lines: list[str] = [
        f"# {project_name} — Project Management Package",
        "",
        f"_Generated on {today_iso()} by AI Project Manager Assistant._",
        "",
        "## Contents",
    ]
    # Table of contents.
    for key, content in outputs.items():
        label = ARTIFACT_LABELS.get(key, key.title())
        lines.append(f"- {label}")
    lines.append("\n---\n")

    # Body: each artifact separated by a rule.
    for key, content in outputs.items():
        lines.append(content.strip())
        lines.append("\n---\n")

    return "\n".join(lines).strip() + "\n"


def build_csv(outputs: dict[str, str]) -> str:
    """
    Produce a CSV string with columns: artifact_key, artifact_label, content.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL)
    writer.writerow(["artifact_key", "artifact_label", "content"])
    for key, content in outputs.items():
        label = ARTIFACT_LABELS.get(key, key.title())
        writer.writerow([key, label, content])
    return buffer.getvalue()


def write_outputs_to_disk(
    project_name: str,
    outputs: dict[str, str],
    outputs_dir: str = "outputs",
) -> dict[str, str]:
    """
    Write Markdown and CSV files to the local outputs/ folder.

    Returns a dict with the paths written: {"markdown": ..., "csv": ...}.
    """
    folder = Path(outputs_dir)
    folder.mkdir(parents=True, exist_ok=True)
    slug = slugify(project_name)

    md_path = folder / f"{slug}.md"
    csv_path = folder / f"{slug}.csv"

    md_path.write_text(build_markdown(project_name, outputs), encoding="utf-8")
    csv_path.write_text(build_csv(outputs), encoding="utf-8")

    return {"markdown": str(md_path), "csv": str(csv_path)}
