"""
app.py
------
Streamlit front end for the AI Project Manager Assistant.

Run with:
    streamlit run app.py

The UI is organized into three tabs for a clean, professional flow:
1. 📊 Dashboard : portfolio metrics — project count, open actions, high risks,
                  and project-health distribution (with charts).
2. 📝 Create   : enter inputs, validate, generate, save, and export.
3. 📚 Saved Projects : browse, review, edit, export, and delete saved projects.

The sidebar shows lightweight app info and stats. All persistence lives in
SQLite (src/db.py) and all generation in the pluggable engine (src/ai_engine.py).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.ai_engine import engine_status, get_engine
from src.analytics import (
    compute_health,
    dashboard_metrics,
    summarize_project,
)
from src.db import (
    delete_project,
    get_project,
    list_projects,
    save_project,
    update_project,
)
from src.exporters import build_csv, build_markdown, write_outputs_to_disk
from src.templates import ARTIFACT_LABELS, INPUT_FIELDS, SAMPLE_PROJECT
from src.utils import slugify, validate_inputs

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
DB_PATH = str(BASE_DIR / "data" / "projects.db")
OUTPUTS_DIR = str(BASE_DIR / "outputs")

# Fields shown as single-line text inputs; everything else is a text area.
SINGLE_LINE_FIELDS = {"project_name", "target_date"}

# Human-friendly labels for the input fields (used in the History view).
INPUT_LABELS = {key: label for key, label, _, _ in INPUT_FIELDS}

# AI Mode selector options: display label -> internal engine mode.
MODE_LABELS = {"🧪 Standard Mode": "mock", "🤖 LLM Mode": "llm"}
LABEL_BY_MODE = {mode: label for label, mode in MODE_LABELS.items()}

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Project Manager Assistant",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------
def _blank_inputs() -> dict[str, str]:
    """Return a fresh dict with an empty value for every input field."""
    return {key: "" for key, _, _, _ in INPUT_FIELDS}


def _init_state() -> None:
    """Ensure the keys we rely on exist in session state."""
    if "inputs" not in st.session_state:
        st.session_state.inputs = _blank_inputs()
    if "outputs" not in st.session_state:
        st.session_state.outputs = {}  # dict[str, str] of generated Markdown
    if "ai_mode" not in st.session_state:
        # Default to LLM only when a key is already configured; else mock.
        st.session_state.ai_mode = (
            "llm" if engine_status("auto")["mode"] == "llm" else "mock"
        )


def _load_example() -> None:
    """Populate the form with the generic sample project."""
    st.session_state.inputs = dict(SAMPLE_PROJECT)
    st.session_state.outputs = {}


def _clear_form() -> None:
    """Reset the form and any generated outputs."""
    st.session_state.inputs = _blank_inputs()
    st.session_state.outputs = {}


# ---------------------------------------------------------------------------
# Sidebar: app info + stats
# ---------------------------------------------------------------------------
def _render_sidebar() -> None:
    st.sidebar.title("📋 AI PM Assistant")
    st.sidebar.caption(
        "Turn a rough project idea into a full set of project-management "
        "artifacts — offline and API-key free."
    )

    st.sidebar.divider()
    saved = list_projects(DB_PATH)
    st.sidebar.metric("Saved Projects", len(saved))
    st.sidebar.metric("Artifacts per Project", len(ARTIFACT_LABELS))

    st.sidebar.divider()

    # --- AI Mode selector -------------------------------------------------
    st.sidebar.subheader("AI Mode")
    # Keep the two mode buttons on a single row (no wrapping) at any width.
    st.sidebar.markdown(
        """
        <style>
        section[data-testid="stSidebar"] div[data-testid="stButtonGroup"] {
            flex-wrap: nowrap;
        }
        section[data-testid="stSidebar"] div[data-testid="stButtonGroup"] > div {
            flex: 1 1 0;
        }
        section[data-testid="stSidebar"] div[data-testid="stButtonGroup"] button {
            width: 100%;
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    selected_label = st.sidebar.segmented_control(
        "AI Mode",
        options=list(MODE_LABELS.keys()),
        default=LABEL_BY_MODE[st.session_state.ai_mode],
        label_visibility="collapsed",
    )
    if selected_label is not None:
        st.session_state.ai_mode = MODE_LABELS[selected_label]

    status = engine_status(st.session_state.ai_mode)
    if status["mode"] == "llm":
        line = f"🤖 **LLM Mode** — {status['provider']}"
        if status.get("model"):
            line += f" (`{status['model']}`)"
        st.sidebar.success(line)
    elif status["mode"] == "error":
        st.sidebar.warning(
            "⚠️ LLM Mode needs an API key. Add `LLM_API_KEY` to your `.env` file "
            "(see `.env.example`), or switch to Standard Mode."
        )
    else:
        st.sidebar.info("🧪 **Standard Mode** — runs offline, no API key needed.")

    st.sidebar.divider()
    st.sidebar.markdown(
        "**How to use**\n"
        "1. Fill in the form (or *Load Example*).\n"
        "2. Click **Generate**.\n"
        "3. **Save** and **Export** your package.\n"
        "4. Open **📚 Saved Projects** to review or edit anytime."
    )


# ---------------------------------------------------------------------------
# Create tab: input form
# ---------------------------------------------------------------------------
def _render_input_form() -> None:
    st.subheader("1) Enter Project Information")
    st.caption("Fields marked with * are required.")

    # Helper buttons above the form.
    col_a, col_b, _ = st.columns([1, 1, 4])
    col_a.button(
        "✨ Load Example", on_click=_load_example, use_container_width=True,
        help="Fill the form with a generic sample project.",
    )
    col_b.button(
        "🧹 Clear", on_click=_clear_form, use_container_width=True,
        help="Reset all fields and outputs.",
    )

    inputs = st.session_state.inputs
    # Two-column layout for a compact, professional form.
    #
    # NOTE: We deliberately do NOT pass a widget `key` here. The field values
    # live in the single `st.session_state.inputs` dict, and the Load Example /
    # Clear callbacks mutate that dict. Binding via `value=` (without a key)
    # lets those callbacks refresh the form on the next rerun.
    left, right = st.columns(2)
    for i, (key, label, help_text, required) in enumerate(INPUT_FIELDS):
        target = left if i % 2 == 0 else right
        star = " *" if required else ""
        if key in SINGLE_LINE_FIELDS:
            inputs[key] = target.text_input(
                f"{label}{star}", value=inputs.get(key, ""), help=help_text,
            )
        else:
            inputs[key] = target.text_area(
                f"{label}{star}", value=inputs.get(key, ""), help=help_text,
                height=90,
            )


# ---------------------------------------------------------------------------
# Create tab: actions (generate / save / export)
# ---------------------------------------------------------------------------
def _render_actions() -> None:
    st.subheader("2) Generate & Export")

    c1, c2, c3, c4 = st.columns(4)

    # --- Generate ---------------------------------------------------------
    if c1.button("⚡ Generate", type="primary", use_container_width=True):
        errors, warnings = validate_inputs(st.session_state.inputs, INPUT_FIELDS)
        for warning in warnings:
            st.warning(warning)
        if errors:
            st.error(
                "Please fix the following before generating:\n\n"
                + "\n".join(f"- {e}" for e in errors)
            )
        else:
            with st.spinner("Generating your project package…"):
                try:
                    engine = get_engine(st.session_state.get("ai_mode", "mock"))
                    st.session_state.outputs = engine.generate_all(st.session_state.inputs)
                except Exception as exc:  # network/LLM/config errors
                    st.session_state.outputs = {}
                    st.error(
                        "Generation failed. If you're using LLM mode, check your "
                        "`LLM_API_KEY`, provider settings, and network.\n\n"
                        f"Details: {exc}"
                    )
            if st.session_state.outputs:
                st.success(
                    f"Generated all {len(st.session_state.outputs)} artifacts below. 🎉"
                )

    outputs = st.session_state.outputs
    has_outputs = bool(outputs)
    project_name = st.session_state.inputs.get("project_name") or "Untitled Project"
    slug = slugify(project_name)

    # --- Save -------------------------------------------------------------
    if c2.button("💾 Save Project", use_container_width=True, disabled=not has_outputs):
        try:
            new_id = save_project(DB_PATH, project_name, st.session_state.inputs, outputs)
            paths = write_outputs_to_disk(project_name, outputs, OUTPUTS_DIR)
            st.success(
                f"Saved as project #{new_id}. Files written to "
                f"`{paths['markdown']}` and `{paths['csv']}`."
            )
        except Exception as exc:  # surface DB/file errors instead of crashing
            st.error(f"Could not save project: {exc}")

    # --- Export Markdown --------------------------------------------------
    c3.download_button(
        "⬇️ Export Markdown",
        data=build_markdown(project_name, outputs) if has_outputs else "",
        file_name=f"{slug}.md",
        mime="text/markdown",
        use_container_width=True,
        disabled=not has_outputs,
    )

    # --- Export CSV -------------------------------------------------------
    c4.download_button(
        "⬇️ Export CSV",
        data=build_csv(outputs) if has_outputs else "",
        file_name=f"{slug}.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=not has_outputs,
    )

    if not has_outputs:
        st.info("💡 Save and export unlock after you generate a package.")


# ---------------------------------------------------------------------------
# Reusable: render a set of artifacts as expandable panels
# ---------------------------------------------------------------------------
def _render_artifacts(outputs: dict[str, str]) -> None:
    """Display each artifact in an expander (first one open by default)."""
    first_key = next(iter(outputs))
    for key, content in outputs.items():
        label = ARTIFACT_LABELS.get(key, key.title())
        with st.expander(f"📄 {label}", expanded=(key == first_key)):
            st.markdown(content)


def _render_outputs() -> None:
    outputs = st.session_state.outputs
    if not outputs:
        st.info("👆 Fill in the form and click **Generate** to see your project package.")
        return
    _render_health_banner(st.session_state.inputs)
    st.subheader("3) Generated Project Package")
    _render_artifacts(outputs)


def _render_health_banner(inputs: dict[str, str]) -> None:
    """Show the computed project-health indicator above the artifacts."""
    health = compute_health(inputs)
    status = health["status"]
    reasons = " · ".join(health["reasons"])
    message = f"**Project Health: {health['label']}** — {reasons}"
    if status == "Green":
        st.success(message)
    elif status == "Yellow":
        st.warning(message)
    else:
        st.error(message)


# ---------------------------------------------------------------------------
# History tab: browse / view / load / export / delete saved projects
# ---------------------------------------------------------------------------
def _render_history() -> None:
    st.subheader("📚 Saved Projects — Review & Edit")
    projects = list_projects(DB_PATH)

    if not projects:
        st.info(
            "No saved projects yet. Create one in the **📝 Create** tab and "
            "click **💾 Save Project** — it will then appear here to review and edit."
        )
        return

    st.caption(
        "Pick a project below to review its details, edit the documents, "
        "and save your changes."
    )

    # --- Step 1: choose a project ----------------------------------------
    st.markdown("#### Step 1 — Choose a project")
    label_to_id = {f"#{p['id']} — {p['name']}": p["id"] for p in projects}
    choice = st.selectbox(
        "Select a project to review or edit",
        list(label_to_id.keys()),
        help="Every project you save shows up in this list.",
    )
    selected_id = label_to_id[choice]

    # Optional overview of everything saved, tucked away to keep the focus clear.
    with st.expander(f"📋 See all {len(projects)} saved projects", expanded=False):
        table = [
            {
                "ID": p["id"],
                "Project": p["name"],
                "Saved": p["created_at"].replace("T", " "),
            }
            for p in projects
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)

    record = get_project(DB_PATH, selected_id)
    if not record:
        st.error("That project could not be loaded (it may have been deleted).")
        return

    name = record["name"]
    outputs = record["outputs"]
    slug = slugify(name)

    st.divider()
    st.markdown(f"#### Step 2 — Review **{name}**")
    _render_health_banner(record["inputs"])

    # Action row for the selected project.
    a1, a2, a3, a4 = st.columns(4)
    if a1.button("📂 Load into Create tab", use_container_width=True):
        st.session_state.inputs = {**_blank_inputs(), **record["inputs"]}
        st.session_state.outputs = outputs
        st.success(
            "Loaded into the **📝 Create** tab. Switch tabs to change the inputs "
            "or re-generate the whole package."
        )

    a2.download_button(
        "⬇️ Markdown", data=build_markdown(name, outputs),
        file_name=f"{slug}.md", mime="text/markdown", use_container_width=True,
    )
    a3.download_button(
        "⬇️ CSV", data=build_csv(outputs),
        file_name=f"{slug}.csv", mime="text/csv", use_container_width=True,
    )
    if a4.button("🗑️ Delete", use_container_width=True):
        delete_project(DB_PATH, selected_id)
        st.warning(f"Deleted project #{selected_id}.")
        st.rerun()

    # Show the saved inputs.
    with st.expander("📝 Saved inputs", expanded=False):
        for key in INPUT_LABELS:
            value = record["inputs"].get(key, "")
            if value:
                st.markdown(f"**{INPUT_LABELS[key]}**")
                st.write(value)

    # --- Step 3: edit the documents --------------------------------------
    st.divider()
    st.markdown("#### Step 3 — Edit the documents")
    edit_mode = st.toggle(
        "✏️ Edit mode",
        key=f"edit_mode_{selected_id}",
        help="Turn on to change any document text, then save your edits.",
    )

    if edit_mode:
        _render_editor(selected_id, record)
    else:
        st.caption(
            "Turn on **✏️ Edit mode** above to change the text of any document, "
            "or read the generated artifacts below."
        )
        _render_artifacts(outputs)


def _render_editor(selected_id: int, record: dict) -> None:
    """Render editable fields for a saved project's name and artifacts."""
    st.info(
        "Make your changes below, then click **💾 Save changes** at the bottom "
        "to update this saved project."
    )

    new_name = st.text_input(
        "Project name",
        value=record["name"],
        key=f"name_{selected_id}",
    )

    edited_outputs: dict[str, str] = {}
    for key, content in record["outputs"].items():
        label = ARTIFACT_LABELS.get(key, key.title())
        edited_outputs[key] = st.text_area(
            f"📄 {label}",
            value=content,
            key=f"art_{selected_id}_{key}",
            height=220,
        )

    if st.button("💾 Save changes", type="primary", key=f"save_{selected_id}"):
        try:
            updated = update_project(
                DB_PATH, selected_id, new_name, record["inputs"], edited_outputs
            )
        except Exception as exc:  # surface DB errors instead of crashing
            st.error(f"Could not save your changes: {exc}")
            return
        if updated:
            st.success("Your changes were saved. ✅")
            st.rerun()
        else:
            st.error("Could not find that project to update (it may have been deleted).")


# ---------------------------------------------------------------------------
# Dashboard tab: portfolio-level metrics and charts
# ---------------------------------------------------------------------------
def _load_summaries() -> list[dict]:
    """Fetch every saved project and compute its analytics summary."""
    summaries = []
    for p in list_projects(DB_PATH):
        record = get_project(DB_PATH, p["id"])
        if record:
            summaries.append(summarize_project(record))
    return summaries


def _render_dashboard() -> None:
    st.subheader("📊 Portfolio Dashboard")

    summaries = _load_summaries()
    if not summaries:
        st.info(
            "No data yet. Create and **Save** a project in the **Create** tab, "
            "then return here to see portfolio metrics."
        )
        return

    metrics = dashboard_metrics(summaries)

    # Top-line KPIs.
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Projects", metrics["project_count"])
    m2.metric("Open Action Items", metrics["open_action_items"])
    m3.metric("High / Critical Risks", metrics["high_risks"])
    green = metrics["health_distribution"].get("Green", 0)
    m4.metric("Healthy Projects", f"{green}/{metrics['project_count']}")

    st.divider()

    # Charts: health distribution + open actions per project.
    left, right = st.columns(2)

    with left:
        st.markdown("**Project Health Distribution**")
        dist = metrics["health_distribution"]
        health_df = pd.DataFrame(
            {"Projects": [dist.get("Green", 0), dist.get("Yellow", 0), dist.get("Red", 0)]},
            index=["🟢 Green", "🟡 Yellow", "🔴 Red"],
        )
        st.bar_chart(health_df)

    with right:
        st.markdown("**Open Action Items by Project**")
        actions_df = pd.DataFrame(
            {"Open Actions": [s["open_actions"] for s in summaries]},
            index=[s["name"] for s in summaries],
        )
        st.bar_chart(actions_df)

    st.divider()

    # Detail table.
    st.markdown("**Project Details**")
    table = [
        {
            "ID": s["id"],
            "Project": s["name"],
            "Health": s["health_label"],
            "Open Actions": s["open_actions"],
            "High Risks": s["high_risks"],
        }
        for s in summaries
    ]
    st.dataframe(table, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    _init_state()

    st.title("📋 AI Project Manager Assistant")
    st.caption(
        "Transform a rough project idea into a polished, structured "
        "project-management package."
    )

    _render_sidebar()

    tab_dashboard, tab_create, tab_history = st.tabs(
        ["📊 Dashboard", "📝 Create", "📚 Saved Projects"]
    )

    with tab_dashboard:
        _render_dashboard()

    with tab_create:
        _render_input_form()
        st.divider()
        _render_actions()
        st.divider()
        _render_outputs()

    with tab_history:
        _render_history()

    st.divider()
    st.caption(
        "Built with Python & Streamlit · Offline mock AI engine "
        "(ready to connect to a real LLM API) · Sample data is generic and portfolio-safe."
    )


if __name__ == "__main__":
    main()
