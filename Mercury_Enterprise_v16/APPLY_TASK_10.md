# MERCURY ENTERPRISE V1.0

## MODULE 5 — AI DECISION ENGINE
### TASK 10

OBJECTIVE

Create a backend-only decision-support engine that consumes outputs from existing Mercury modules and produces ranked, explainable recommendations for human operators.

Do NOT modify the frontend.

Do NOT implement autonomous targeting, weapon control, firing, interception, or automatic execution of operational actions.

---

## CREATE

backend/app/decision/

Files:

__init__.py
models.py
scoring.py
decision_engine.py
explanations.py

Create tests:

backend/tests/test_decision_engine.py

---

## 1. DECISION INPUT MODEL

The engine may consume:

- mission_id
- track_id
- threat_score
- threat_level
- threat_confidence
- mission_status
- mission_priority
- active_alerts
- available_resources
- fused_confidence
- response_recommendations
- operator_constraints
- environmental_context
- metadata

Reuse existing outputs from:

- AI Threat Assessment
- Fusion Engine
- Mission Management
- Alert Management
- Response Orchestration

Do NOT duplicate their logic.

---

## 2. CANDIDATE ACTION MODEL

Each candidate recommendation must contain:

- action_id
- name
- category
- description
- source_module
- priority
- confidence
- feasibility_score
- risk_score
- mission_alignment_score
- resource_impact_score
- overall_score
- reasons
- constraints
- metadata

Candidate actions are recommendations only.

They must never automatically execute anything.

---

## 3. DECISION RESULT MODEL

Return:

- decision_id
- created_at
- mission_id
- track_id
- context_summary
- ranked_actions
- selected_recommendation
- confidence
- reasoning
- warnings
- requires_human_approval
- metadata

`requires_human_approval` must always be true.

---

## 4. SCORING ENGINE

Implement deterministic scoring.

Consider:

- threat severity
- mission priority
- response confidence
- fused track confidence
- resource availability
- feasibility
- risk
- mission alignment
- operator constraints

Normalize scores to 0–100.

No external AI API is required.

---

## 5. DECISION ENGINE

Implement:

evaluate()
rank_actions()
select_recommendation()
explain()
validate_context()

The engine must:

1. Accept normalized context.
2. Validate required data.
3. Collect existing response recommendations.
4. Score each recommendation.
5. Rank them.
6. Produce one recommended option.
7. Produce a human-readable explanation.
8. Mark the result as requiring human approval.
9. Publish decision events through the existing EventBus.

---

## 6. EVENT BUS INTEGRATION

Extend:

backend/app/core/events.py

Add:

decision.requested
decision.evaluated
decision.recommendation_selected
decision.warning
decision.error

Reuse the existing EventBus.

Do NOT create another event system.

---

## 7. TIMELINE INTEGRATION

Decision events must flow into the existing Timeline Engine through EventBus.

Do not duplicate timeline storage.

---

## 8. MISSION INTEGRATION

Read mission:

- status
- priority
- objectives
- constraints
- assigned resources

Do not modify mission state automatically.

---

## 9. FUSION INTEGRATION

Read fused track information:

- track confidence
- classification
- state
- linked observations

Do not modify tracks.

---

## 10. ALERT INTEGRATION

Consume active alert information.

Do not duplicate alert logic.

---

## 11. RESPONSE ORCHESTRATION INTEGRATION

Use existing response recommendations as candidate actions.

Do not duplicate response-generation logic.

---

## 12. APPLICATION STARTUP

Update:

backend/app/main.py

Create one shared DecisionEngine and store it in:

app.state.decision_engine

---

## 13. TESTS

Test:

- valid decision evaluation
- ranking order
- deterministic scoring
- invalid input handling
- missing mission context
- alert influence
- fusion confidence influence
- mission priority influence
- operator constraint handling
- EventBus publishing
- human approval always required
- no automatic action execution

All existing tests must continue to pass.

---

## QUALITY

Use:

- Python type hints
- dataclasses or Pydantic
- enums where appropriate
- UTC timestamps
- logging
- docstrings
- deterministic scoring
- thread-safe shared state if needed
- clean architecture

No frontend changes.

No external network calls.

No autonomous execution.

---

## VERIFICATION

From backend:

python -m compileall app
python -m pytest

Fix all failures before commit.

---

## COMMIT

git add .

git commit -m "Module 5 - AI Decision Engine"

git push