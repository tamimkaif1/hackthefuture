# Supply Chain Agent – 6-Layer Resilience Pipeline

A full **mock-data** supply chain resilience agent that runs without any real API or live data. It implements a 6-layer pipeline with human review gates, merging perception (Mohid), risk/planning/action/transparency (Tamim), and memory (Mohid).

## Architecture

| Layer | Owner | Components |
|-------|--------|------------|
| **1. Perception** | Mohid | News ingestion (mock), ERP signal monitoring (mock), supply risk classification, **supplier health scoring** |
| **2. Risk Intelligence** | Tamim | Disruption probability, operational impact, revenue-at-risk, multi-variable trade-offs |
| **3. Planning & Decision** | Mohid + Tamim | Scenario simulation (cost vs service), supplier reallocation, buffer stock, decision tree (Mohid plan with Layer 2 data); Tamim options for comparison |
| **4. Autonomous Action** | Tamim | Auto supplier emails, PO adjustment suggestions, **escalation triggers**, **workflow integration log** (mock) |
| **5. Memory & Reflection** | Mohid | Logs past disruptions, reflection summary, **small chunks** saved to `memory_chunks.json` |
| **6. Decision Transparency** | Tamim | Reasoning trace, human override thresholds, assumptions, **bias and constraint validation** |

All data is **mock**: news feed, ERP, classifier, planning, and reflection run in mock mode by default (`USE_MOCK_DATA=1`). No API key is required.

## Quick start (mock only)

```bash
# Install
pip install -r requirements.txt

# Run 2 cycles, non-interactive (auto-approve all steps)
python run_agent.py --no-input

# Run 2 cycles with interactive human review
python run_agent.py

# Run 5 cycles, no input (demo/CI)
python run_agent.py --iterations 5 --no-input
```

## CLI options

- `--mock` (default): Use mock data only; no Gemini or external API.
- `--no-mock`: Allow live Gemini when `GOOGLE_API_KEY` is set in `.env`.
- `--iterations N`: Number of news cycles (default: 2).
- `--no-input`: Non-interactive; auto-approve every human review (for CI/demos).

## Project layout

```
├── run_agent.py          # Main 6-layer pipeline (CLI)
├── config.py             # USE_MOCK_DATA and config
├── config.json           # Manufacturer profile (revenue, SLA, inventory_days, critical_parts)
├── perception/           # Layer 1
│   ├── news_parser.py    # Mock news feed
│   ├── erp_mock.py       # Mock ERP inventory
│   ├── classifier.py     # Risk classification (mock or Gemini)
│   └── supplier_health.py # Supplier health scoring (mock, from past_disruptions)
├── risk_intelligence/    # Layer 2 + adapter
│   ├── risk_engine.py    # Disruption probability, revenue-at-risk, etc.
│   ├── planning_engine.py # Tamim scenario options
│   └── adapter.py        # Layer 1 → Tamim schemas + manufacturer profile
├── planning/             # Layer 3 (Mohid)
│   └── decision_engine.py # Mitigation plan from Layer 1 + Layer 2 (mock or Gemini)
├── action/               # Layer 4
│   └── action_generator.py # Emails, alerts, PO text, escalation, workflow log
├── memory/               # Layer 5
│   └── reflection.py     # Reflection + memory chunks
├── transparency/         # Layer 6
│   └── transparency.py   # Reasoning trace, bias/constraint validation
├── schemas/
│   └── tamim_schema.py   # Pydantic models for Tamim layers
├── past_disruptions.json # Disruption log (and supplier health input)
├── memory_chunks.json    # Condensed AI memory chunks
├── pending_actions.json  # Executed actions log (mock workflow)
└── app_fastapi.py        # Optional FastAPI server for risk/plan/actions/transparency
```

## Optional: run with live Gemini

1. Copy `.env.example` to `.env`.
2. Set `USE_MOCK_DATA=0` and add your `GOOGLE_API_KEY`.
3. Run: `python run_agent.py --no-mock`.

## Run everything (API + frontend)

One server serves both the **web UI** and the **API**:

```bash
# Install (if not already)
pip install -r requirements.txt

# Start the app (frontend at http://localhost:8000)
uvicorn app_fastapi:app --reload
```

Then open **http://localhost:8000** in your browser. Use “Start workflow” to run the 6-layer pipeline step-by-step in the UI. The same mock data is used; no API key required.

The same server also exposes:
- **Wizard API** (used by the UI): `GET /api/step1_perception`, `POST /api/step2_risk`, `POST /api/step3_plan`, etc.
- **Programmatic API**: `POST /risk-assessment`, `POST /plan`, `POST /actions`, `POST /transparency` (request bodies use `schemas.tamim_schema` models).

## Data flow (mock)

1. **Perception**: Mock news → mock ERP context → classifier (mock) → summary + **supplier health**. Human review 1.
2. **Adapter**: Summary + ERP → Tamim `PerceptionOutput` + `ManufacturerProfile` (from `config.json`).
3. **Risk**: `assess_risk()` → downtime, revenue-at-risk, risk level. Human review 2.
4. **Planning**: Mohid `DecisionEngine.formulate_plan(assessment, risk_result)` → `MitigationPlan`. Tamim `simulate_plan_options(risk)` for comparison. Human review 3.
5. **Action**: `generate_actions()` → email, alert, PO text, **escalation trigger**, **workflow log**. Human review 4 → execute (write to `pending_actions.json`).
6. **Memory**: `reflect_and_store()` → reflection (mock) → save to `past_disruptions.json` and **memory_chunks.json**. Human review 5 (or auto-save with `--no-input`).
7. **Transparency**: `build_transparency()` → reasoning trace, override threshold, assumptions, **bias and constraint validation**.

## Features included

- **Mock-only by default**: No API key; all components use deterministic mock data.
- **Supplier health scoring**: From `past_disruptions.json` + ERP (mock).
- **Mohid planning with Layer 2 data**: Real risk numbers fed into `DecisionEngine`.
- **Escalation triggers**: Critical/high risk → VP or Manager escalation message.
- **Workflow integration log**: Mock “queued for ERP / dashboard / change log”.
- **Bias and constraint validation**: Exposure cap, “Do nothing” when high risk, supplier change documentation.
- **CLI**: `--mock`, `--no-mock`, `--iterations`, `--no-input` for demos and CI.
