# 📋 AI Project Manager Assistant

Transform a rough project idea into a **complete, structured project-management package** — instantly, offline, and with no API key required.

Built with **Python + Streamlit**, this local web app takes nine simple inputs and generates **fourteen professional PM artifacts**, scores project risk, computes a **Green/Yellow/Red health indicator**, saves everything to a local **SQLite** database, and surfaces a **portfolio dashboard** with charts. Export any package to **Markdown or CSV**.

> ⚠️ **Portfolio-safe:** All sample data is generic and fictional. No confidential or company-specific information is included, making this project safe to share publicly with recruiters.

> 🚀 **New to this / running on another PC? Read [`SETUP.md`](SETUP.md) first.** This is a local Python app, so a little one-time prework (install Python, install dependencies) is required before it will run. Or just double-click **`run.bat`** to have it set up and launch automatically.

---

## ✨ Features

- **Nine simple inputs → fourteen polished outputs.**
- **Risk scoring model** — each risk is scored on **Probability × Impact (1–25)** and mapped to a **Low / Medium / High / Critical** level.
- **Project health indicator** — an explainable **🟢 Green / 🟡 Yellow / 🔴 Red** status derived from risk scores, dates, and completeness.
- **Portfolio dashboard** — project count, total open action items, high/critical risks, and a **health-distribution chart** (Streamlit `st.bar_chart`).
- **Executive one-page summary** and **RACI matrix** generator for stakeholder alignment.
- **Lessons-learned** retrospective template.
- **Two generation modes, one interface** — runs **offline in mock mode** by default, or in **LLM mode** with a real model when you set `LLM_API_KEY` (see [Generation modes](#-generation-modes-mock-vs-llm)).
- **Pluggable provider interface** — connect **OpenAI, Azure OpenAI, or Anthropic (Claude)** via environment variables; add your own provider in one small file.
- **Local persistence** — saved projects stored in SQLite (`data/projects.db`).
- **One-click export** — download a combined **Markdown** document or a **CSV** file.
- **Clean, modular structure** — separate modules for AI logic, analytics, database, exports, templates, and helpers.

### Generated artifacts

1. Project Charter
2. Scope Statement
3. Key Milestones
4. Work Breakdown Structure (WBS)
5. RAID Log (Risks, Assumptions, Issues, Dependencies)
6. **Risk Register** (scored: probability, impact, score, risk level, mitigation)
7. Action Item List (owner, due date, priority, status)
8. **RACI Matrix** (Responsible, Accountable, Consulted, Informed)
9. Stakeholder Communication Plan
10. Executive Status Summary
11. **Executive One-Page Summary** (health indicator + top risks)
12. Kickoff Meeting Agenda
13. **Lessons Learned**
14. Resume-Ready Achievement Summary

### Risk scoring & health model

- **Risk score** = Probability (1–5) × Impact (1–5) → **1–25**, mapped to 🟢 Low (1–3), 🟡 Medium (4–8), 🟠 High (9–14), 🔴 Critical (15–25).
- **Health indicator:** 3+ high/critical risks → **Red**; 1–2 elevated risks, a past target date, or missing key context → **Yellow**; otherwise **Green**. Every status ships with the reasons behind it.

---

## 🗂️ Project Structure

```
ai-project-manager-assistant/
├── app.py                # Streamlit UI (Dashboard / Create / History tabs)
├── requirements.txt      # Dependencies (Streamlit + pandas)
├── README.md             # This file
├── data/
│   └── projects.db       # SQLite DB (created automatically at runtime)
├── outputs/              # Exported .md / .csv files land here
└── src/
    ├── __init__.py
    ├── ai_engine.py      # Generates the 14 artifacts (mock + LLM engines)
    ├── analytics.py      # Risk scoring, health indicator, dashboard metrics
    ├── providers.py      # LLM provider interface (OpenAI/Azure/Anthropic)
    ├── db.py             # SQLite persistence layer
    ├── exporters.py      # Markdown & CSV builders
    ├── templates.py      # Artifact/field metadata + sample project
    └── utils.py          # Small reusable helpers
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+

### 1. (Optional) Create a virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies
```powershell
pip install -r requirements.txt
```

### 3. Run the app
```powershell
streamlit run app.py
```

Streamlit will open the app in your browser (typically at `http://localhost:8501`).

### 4. Use it
1. In the **📝 Create** tab, click **✨ Load Example** to populate the form (or enter your own).
2. Click **⚡ Generate** to produce all fourteen artifacts and see the **project health** banner.
3. Click **💾 Save Project** to store it in SQLite and write files to `outputs/`.
4. Use **⬇️ Export Markdown** / **⬇️ Export CSV** to download the package.
5. Open the **📊 Dashboard** tab for portfolio metrics and charts, and the **📚 History** tab to browse saved projects.

---

## 📝 Sample Project Example

The **Load Example** button fills the form with this generic, fictional project:

| Field | Value |
|---|---|
| **Project Name** | Lab Inventory Automation Initiative |
| **Objective** | Reduce manual inventory tracking effort and improve stock accuracy across the operations lab. |
| **Business Problem** | Inventory is tracked in spreadsheets, causing stockouts, duplicate purchases, and hours of manual reconciliation each week. |
| **Expected Benefits** | Save ~8 hours/week, cut duplicate purchases by 20%, and provide real-time inventory visibility. |
| **Stakeholders** | Operations Manager — Sponsor; Lab Supervisor — Product Owner; Procurement Lead — Reviewer; Lab Technicians — End Users |
| **Constraints** | Fixed 12-week timeline; no additional headcount; existing tooling budget only. |
| **Target Completion Date** | 2026-10-30 |
| **Known Risks** | Low user adoption; inaccurate legacy data; limited technician availability for training. |
| **Available Resources** | 1 process improvement lead, 2 part-time technicians, barcode scanners, cloud spreadsheet tools. |

Generating from these inputs produces a full charter, scope statement, milestone table, WBS, RAID log, **scored risk register**, action items, **RACI matrix**, communication plan, executive status summary, **executive one-page summary**, kickoff agenda, **lessons learned**, and resume bullets — plus a computed **health indicator** (🟡 Yellow for this sample, driven by two elevated risks).

---

## 🧩 What Each File Does

| File | Responsibility |
|---|---|
| `app.py` | Streamlit UI: Dashboard, Create, and History tabs (form, actions, charts, health banner). |
| `src/ai_engine.py` | Core generation logic. `MockAIEngine` builds all 14 artifacts from templates; `LLMEngine` builds them via a provider. `get_engine()` picks the mode; `engine_status()` reports it. |
| `src/providers.py` | Pluggable LLM provider interface + OpenAI / Azure OpenAI / Anthropic implementations and the env-based provider factory. |
| `src/analytics.py` | Risk scoring model (probability × impact), Green/Yellow/Red health indicator, and dashboard aggregation. |
| `src/db.py` | SQLite layer: `init_db`, `save_project`, `list_projects`, `get_project`, `delete_project`. |
| `src/exporters.py` | Builds combined Markdown and CSV outputs and writes them to `outputs/`. |
| `src/templates.py` | Single source of truth for artifact list, input fields, and the sample project. |
| `src/utils.py` | Small standard-library helpers (slugify, date/time, text cleaning). |

---

## 🔌 Generation Modes: Mock vs. LLM

The app supports **two modes** behind a single interface, so the UI, database, and exports never change:

| Mode | When it runs | Needs a key? | Needs internet? |
|---|---|---|---|
| 🧪 **Mock** | Default — whenever `LLM_API_KEY` is **not** set | No | No |
| 🤖 **LLM** | Automatically when `LLM_API_KEY` **is** set | Yes | Yes |

The active mode is shown in the sidebar. **LLM mode is never required** — with no key, the app runs fully offline in mock mode. **No API keys are ever hard-coded**; they are read from the environment at runtime.

### Mode 1 — Mock (default, zero config)

Just run the app. No environment variables, no extra packages:

```powershell
streamlit run app.py
```

Generation uses deterministic local Python templates and rules (`MockAIEngine`).

### Mode 2 — LLM (bring your own model)

1. **Install the SDK** for your chosen provider (only the one you use):

   ```powershell
   pip install openai       # for OpenAI or Azure OpenAI
   # or
   pip install anthropic    # for Anthropic (Claude)
   ```

2. **Set environment variables.** The only required one is `LLM_API_KEY`.

   | Variable | Required | Description | Default |
   |---|---|---|---|
   | `LLM_API_KEY` | ✅ | Your provider API key. Its presence enables LLM mode. | — |
   | `LLM_PROVIDER` | | `openai` \| `azure` \| `anthropic` | `openai` |
   | `LLM_MODEL` | | Model name (or **Azure deployment name**) | provider default |
   | `AZURE_OPENAI_ENDPOINT` | Azure only | `https://<resource>.openai.azure.com` | — |
   | `AZURE_OPENAI_API_VERSION` | Azure only | API version | `2024-06-01` |

3. **Provide the variables** either in your shell or via a local `.env` file (already git-ignored; loaded automatically, no extra dependency):

   **PowerShell (current session):**
   ```powershell
   $env:LLM_API_KEY = "your-key-here"
   $env:LLM_PROVIDER = "openai"
   $env:LLM_MODEL = "gpt-4o-mini"
   streamlit run app.py
   ```

   **`.env` file (recommended for local dev):**
   ```dotenv
   LLM_API_KEY=your-key-here
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4o-mini
   ```

   **Azure OpenAI example (`.env`):**
   ```dotenv
   LLM_API_KEY=your-azure-key
   LLM_PROVIDER=azure
   LLM_MODEL=my-gpt4o-deployment
   AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com
   AZURE_OPENAI_API_VERSION=2024-06-01
   ```

   **Anthropic (Claude) example (`.env`):**
   ```dotenv
   LLM_API_KEY=your-anthropic-key
   LLM_PROVIDER=anthropic
   LLM_MODEL=claude-3-5-sonnet-latest
   ```

If the key is missing, invalid, or a call fails, the app tells you in the UI; remove the key to fall straight back to mock mode.

### Adding another provider

Providers live in `src/providers.py` behind a tiny interface:

```python
class LLMProvider(Protocol):
    name: str
    model: str
    def complete(self, system: str, user: str) -> str: ...
```

To add one (e.g. a local model or another vendor):

1. Implement a class with a `complete(system, user) -> str` method (lazily import its SDK so it stays optional).
2. Register it in the `_PROVIDERS` map in `src/providers.py`.
3. Select it with `LLM_PROVIDER=<your-alias>`.

Every engine returns the same `dict[str, str]` shape (artifact key → Markdown), so saving, exporting, analytics, and display keep working unchanged.

---

## 💼 Resume Value

This project demonstrates AI application development, clean software architecture, and practical project-management and operations domain knowledge. Suggested resume bullet:

> **Designed and built an AI-powered Project Management Assistant (Python, Streamlit, SQLite)** that converts a brief project description into 14 structured PM artifacts — including a **scored risk register (probability × impact)**, **RACI matrix**, and **executive one-page summary** — and drives a **portfolio dashboard** with a **Green/Yellow/Red project-health model**, risk analytics, open-action tracking, Markdown/CSV export, and a pluggable engine architecture ready for LLM integration.

---

## 📄 License

Provided as-is for personal, educational, and portfolio use.
