# Setup Guide — Read This First

This app is a **local Python + Streamlit application**. It is NOT a double-click
program. Before it will run on any PC, a little one-time prework is required.

Follow the steps for your situation below.

---

## Prework checklist (required before first run)

- [ ] **1. Install Python 3.10 or newer**
  - Download: https://www.python.org/downloads/
  - During install on Windows, **check the box "Add Python to PATH"**.
  - Verify it worked — open a terminal (PowerShell) and run:
    ```powershell
    python --version
    ```
    You should see something like `Python 3.14.0`.

- [ ] **2. Copy the whole project folder** to the new PC
  - Copy the entire `ai-project-manager-assistant` folder (with `app.py`,
    the `src/` folder, `requirements.txt`, and `seed_examples.py`).
  - Optional: copy `data/projects.db` too if you want the 5 example
    projects to already be there. If you skip it, the database is created
    automatically and you can load the examples in step 5.

- [ ] **3. Install the app's dependencies** (only `streamlit` + `pandas`)
  - Open PowerShell **inside the project folder** and run:
    ```powershell
    pip install -r requirements.txt
    ```
  - On a corporate/proxy network this may fail. If so, add a proxy flag, e.g.:
    ```powershell
    pip install -r requirements.txt --proxy http://proxy-dmz.intel.com:912
    ```

- [ ] **4. Run the app**
  - From inside the project folder:
    ```powershell
    streamlit run app.py
    ```
  - Your browser opens at **http://localhost:8501**. Leave the terminal open
    while you use the app; press `Ctrl + C` in the terminal to stop it.

- [ ] **5. (Optional) Load the 5 example projects**
  - Only needed if you did NOT copy `data/projects.db`. Run once:
    ```powershell
    python seed_examples.py
    ```
  - Then reload the browser and open the **Dashboard** / **History** tabs.

---

## Easiest option: use the one-click launcher

If you don't want to type commands, just **double-click `run.bat`**
(in this folder). It will:

1. Check that Python is installed.
2. Install the dependencies if needed.
3. Start the app and open it in your browser.

You still need **step 1 (install Python)** done first — that is the only
thing `run.bat` cannot do for you.

---

## Good to know

- **No internet or API key needed.** The app runs fully offline in "mock mode"
  by default, so it works out of the box.
- **Data is stored locally** in `data/projects.db` (a SQLite file). Nothing is
  sent to the cloud.
- **LLM mode is optional.** Only if you want to connect a real AI model
  (OpenAI / Azure OpenAI / Claude) do you set an `LLM_API_KEY` environment
  variable — see `README.md` for details. It is never required.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python is not recognized` | Python isn't installed or "Add to PATH" was unchecked. Reinstall Python and check that box. |
| `streamlit is not recognized` | Dependencies aren't installed. Run `pip install -r requirements.txt` from the project folder. |
| `pip` fails on a corporate network | Add the proxy flag shown in step 3. |
| App opens in the wrong folder / can't find `src` | Make sure your terminal is **inside** the `ai-project-manager-assistant` folder before running commands. |
| Port 8501 already in use | Run `streamlit run app.py --server.port 8502` and open that port instead. |
