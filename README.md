# Hospice Referral Intake Workflow Demo

This project is a **Python backend prototype** for a Hospice Referral Intake workflow with:

- `transitions`-based **state machine**
- JSON-driven **rule engine**
- **Checklist** evaluation + **missing field** tracking
- **Next Best Action (NBA)** suggestions
- **Mermaid** `stateDiagram-v2` export (with custom diagram save/override)
- **FastAPI** API layer

Everything is wired for a **demo** with 5 in-memory patients referenced by numeric IDs.

---

## 1. Project Structure

```text
referral_workflow/
  api.py               # FastAPI app + demo patients
  state_machine.py     # transitions-powered state machine wrapper
  rule_engine.py       # JSON rule loader + safe condition evaluator
  checklist_engine.py  # Checklist + missing fields
  nba_engine.py        # Next Best Action generator
  workflow_router.py   # Orchestrates rules → next state → payload
  mermaid_generator.py # Mermaid stateDiagram-v2 export & styling
  models.py            # Pydantic + dataclasses shared models

rules/
  referral_rules.json  # Per-state rule configuration

requirements.txt        # Python dependencies
README.md               # This file
```

---

## 2. Install & Run

**Important:** Run all commands from the **project root** — the folder that *contains* the `referral_workflow` directory (e.g. `D:\NBA`). Do **not** run from inside `referral_workflow`, or you'll get `ModuleNotFoundError: No module named 'referral_workflow'`.

```bash
cd D:\NBA
python -m pip install -r requirements.txt
uvicorn referral_workflow.api:app --reload
```

Open the interactive docs:

```text
http://127.0.0.1:8000/docs
```

All examples below assume this base URL.

---

## 3. Demo Patients

The demo seeds **5 patients** in-memory (in `referral_workflow/api.py`):

| Referral ID | Patient Name      | Initial State              | Scenario                                  |
|-------------|-------------------|----------------------------|-------------------------------------------|
| `123`       | Margaret Thompson | `completed`                | All details complete → all green          |
| `456`       | Robert Garcia     | `needs_review`             | Missing `insurance` & `contact_number`    |
| `789`       | Linda Chen        | `extracting_information`   | Aetna payer → rejected                   |
| `101`       | James Williams    | `needs_review`             | All fields present, ready to progress     |
| `202`       | Susan Martinez    | `fax_received`             | Just received via fax, minimal info       |

---

## 4. Core Endpoints

### 4.1 GET `/referral/{referral_id}/workflow`

Returns the full workflow payload for a patient.

**Example request:**

```bash
curl http://127.0.0.1:8000/referral/123/workflow
```

**Example response:**

```json
{
  "current_state": "completed",
  "attributes": {
    "patient_name": "Margaret Thompson",
    "insurance": "Cigna",
    "contact_number": "555-0201"
  },
  "missing_fields": [],
  "checklist": [],
  "next_best_actions": [],
  "mermaid_diagram": "stateDiagram-v2 ..."
}
```

---

### 4.2 GET `/referral/{referral_id}/mermaid`

Returns the Mermaid diagram for a patient. If a **custom diagram** was previously saved via PUT, it returns the saved version. Otherwise, it returns the engine-generated diagram.

**Example request:**

```bash
curl http://127.0.0.1:8000/referral/456/mermaid
```

**Example response:**

```json
{
  "diagram": "stateDiagram-v2\n    [*] --> fax_received\n    ..."
}
```

---

### 4.3 PUT `/referral/{referral_id}/mermaid`

Save a custom (user-edited) Mermaid diagram for a patient. After saving, all subsequent `GET /mermaid` calls for that patient will return the saved version instead of the engine-generated one.

**Example request:**

```bash
curl -X PUT http://127.0.0.1:8000/referral/456/mermaid \
  -H "Content-Type: application/json" \
  -d '{ "diagram": "stateDiagram-v2\n    [*] --> custom_state\n    custom_state --> done" }'
```

**Example response:**

```json
{
  "referral_id": "456",
  "saved": true
}
```

> **Note:** This is in-memory only. Restarting the server resets all custom diagrams back to engine-generated.

---

### 4.4 POST `/referral/{referral_id}/action`

Execute a workflow action and re-evaluate rules. Optionally pass attribute updates in `data`.

**Example request:**

```bash
curl -X POST http://127.0.0.1:8000/referral/456/action \
  -H "Content-Type: application/json" \
  -d '{ "action": "provide_insurance", "data": { "insurance": "Aetna PPO" } }'
```

**Example response:**

```json
{
  "current_state": "missing_information",
  "attributes": { "patient_name": "Robert Garcia", "insurance": "Aetna PPO", "contact_number": null },
  "missing_fields": ["contact_number"],
  "checklist": [...],
  "next_best_actions": [{ "action": "request_contact_number", "reason": "Missing field: contact_number" }],
  "mermaid_diagram": "stateDiagram-v2 ..."
}
```

---

## 5. Demo Scenarios (Step-by-Step)

### 5.1 Scenario 1 – All Details Complete → Completed (Patient `123`)

- **Patient**: Margaret Thompson
- **Initial state**: `completed`
- **Attributes**: all required fields present.

1. Get the workflow:

   ```bash
   curl http://127.0.0.1:8000/referral/123/workflow
   ```

   - `current_state` should be `"completed"`.

2. Get the Mermaid diagram:

   ```bash
   curl http://127.0.0.1:8000/referral/123/mermaid
   ```

3. Copy the `diagram` string into [Mermaid Live Editor](https://mermaid.live).

   You should see:

   - `[ * ] --> fax_received`
   - All main-flow states up to `completed` styled in **green**.
   - `completed` styled as the **current** state (yellow border/fill).

---

### 5.2 Scenario 2 – Missing Information → Stuck in `missing_information` (Patient `456`)

- **Patient**: Robert Garcia
- **Initial state**: `needs_review`
- **Attributes**: missing `insurance` and `contact_number`.

1. Optionally simulate providing **only insurance**:

   ```bash
   curl -X POST http://127.0.0.1:8000/referral/456/action \
     -H "Content-Type: application/json" \
     -d '{ "action": "provide_insurance" }'
   ```

2. Get the workflow:

   ```bash
   curl http://127.0.0.1:8000/referral/456/workflow
   ```

   You should see:

   - `current_state`: `"missing_information"`
   - `missing_fields`: still contains `"contact_number"`
   - `next_best_actions`: includes `request_contact_number`

3. Get the Mermaid diagram:

   ```bash
   curl http://127.0.0.1:8000/referral/456/mermaid
   ```

4. Paste `diagram` into [Mermaid Live Editor](https://mermaid.live):

   - `[ * ] --> fax_received`
   - States **before** `missing_information` in the main flow are **green**.
   - `missing_information` is highlighted as the **current** state (yellow).

5. To let the patient progress, fill remaining data:

   ```bash
   curl -X POST http://127.0.0.1:8000/referral/456/action \
     -H "Content-Type: application/json" \
     -d '{ "action": "provide_contact_number" }'
   ```

   Then re-run `/workflow` and `/mermaid` to see the updated state and diagram.

---

### 5.3 Scenario 3 – Aetna Payer → Rejected (Patient `789`)

- **Patient**: Linda Chen
- **Initial state**: `extracting_information`
- **Attributes**: `insurance = "Aetna"` (plus other fields present).

Rules (from `rules/referral_rules.json`):

```json
"extracting_information": {
  "rules": [
    {
      "name": "reject_aetna",
      "condition": "insurance != 'Aetna'"
    }
  ],
  "success_state": "needs_review",
  "failure_state": "rejected"
}
```

Interpretation:

- Non-Aetna: rule passes → route to `needs_review`.
- **Aetna**: rule fails → route directly to `rejected`.

Steps:

1. Evaluate workflow:

   ```bash
   curl http://127.0.0.1:8000/referral/789/workflow
   ```

   You should see:

   - `current_state`: `"rejected"`
   - `checklist`: includes `reject_aetna` with `"status": "failed"`

2. Get the Mermaid diagram:

   ```bash
   curl http://127.0.0.1:8000/referral/789/mermaid
   ```

3. Paste `diagram` into [Mermaid Live Editor](https://mermaid.live):

   - `[ * ] --> fax_received`
   - `fax_received` and `extracting_information` styled **green** (completed part of the path).
   - `rejected` styled in **red** (light red fill, dark red thick border) as the **current** state.

---

### 5.4 Scenario 4 – Custom Mermaid Diagram (Save & Retrieve)

This scenario demonstrates saving a user-edited Mermaid diagram for patient `101` (James Williams). For example, the UI user reviews patient `101` and decides to move him from `needs_review` to `ready_for_assignment`. They edit the diagram to reflect this updated status and save it.

1. Fetch the engine-generated diagram for patient `101`:

   ```bash
   curl http://127.0.0.1:8000/referral/101/mermaid
   ```

   This returns the auto-generated diagram based on the current state (`needs_review`).

2. Save a custom diagram that shows the patient progressed to `ready_for_assignment`:

   ```bash
   curl -X PUT http://127.0.0.1:8000/referral/101/mermaid \
     -H "Content-Type: application/json" \
     -d '{
       "diagram": "stateDiagram-v2\n    [*] --> fax_received\n    fax_received --> extracting_information\n    extracting_information --> needs_review\n    needs_review --> missing_information\n    needs_review --> ready_for_assignment\n    missing_information --> needs_review\n    ready_for_assignment --> assigned_to_care_team\n    assigned_to_care_team --> completed\n    extracting_information --> rejected\n    needs_review --> rejected\n    missing_information --> rejected\n    ready_for_assignment --> rejected\n\n    style fax_r0eceived fill:#e6ffed,stroke:#28a745,stroke-width:1.5px\n    style extracting_information fill:#e6ffed,stroke:#28a745,stroke-width:1.5px\n    style needs_review fill:#e6ffed,stroke:#28a745,stroke-width:1.5px\n    style ready_for_assignment fill:#fffbdd,stroke:#b58900,stroke-width:2px"
     }'
   ```

   In this custom diagram:
   - `fax_received`, `extracting_information`, and `needs_review` are styled **green** (completed steps).
   - `ready_for_assignment` is styled **yellow** (current state after the user moved the patient forward).

   Response:

   ```json
   { "referral_id": "101", "saved": true }
   ```

3. Fetch the diagram again:

   ```bash
   curl http://127.0.0.1:8000/referral/101/mermaid
   ```

   This now returns the **custom saved diagram** (with `ready_for_assignment` highlighted) instead of the engine-generated one. Paste it into [Mermaid Live Editor](https://mermaid.live) to verify the styling.

---

## 6. Rule Engine & Safety Notes

- Rules are configured in `rules/referral_rules.json`.
- Conditions are evaluated using a **safe AST-based evaluator** (no `eval`):
  - Supports `and`, `or`, `not`, comparisons (`==`, `!=`, `<`, `>`, etc.), `null` (mapped to `None`), and simple identifiers.
- Missing fields are inferred from failed rules and included in:
  - `missing_fields` (list of field names)
  - `next_best_actions` (NBA suggestions derived from missing fields)

To add new rules or states, extend `referral_rules.json` and, if needed, the state machine transitions in `state_machine.py`.

---

## 7. Extending the Demo

For a production system you would typically:

- Replace the in-memory `ReferralRepository` in `api.py` with a real database/ORM.
- Add authentication and audit logging around actions.
- Load NBA mappings from configuration instead of hardcoding.
- Add more rule sets per state (payer-specific, diagnosis-specific, etc.).
- Persist custom Mermaid diagrams to a database.

But for a **demo prototype**, this setup is ready to show:

- How different referrals take different paths based on rules.
- How missing data drives Next Best Actions.
- How the **Mermaid diagram updates per patient** and per scenario.
- How users can **save and retrieve custom Mermaid diagrams** per patient.
