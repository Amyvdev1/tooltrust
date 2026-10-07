# ToolTrust

**AI Agent Tool Reliability Lab.** ToolTrust reviews tool definitions before an AI agent is allowed to use them. It focuses on schema clarity, risk, permissions, side effects, confirmation, idempotency, structured errors, and execution replay.

## Included in v1
- deterministic risk classification: read-only, reversible write, irreversible write, external side effect
- JSON Schema quality checks for names, types, required fields, descriptions, enums, and argument ambiguity
- explicit permission and side-effect checks
- mandatory human confirmation policy for high-impact tools
- idempotency and structured-error checks
- five category scores + overall reliability score
- confirmation preview
- replay viewer with schema validation → permission check → confirmation → simulated execution
- polished dashboard, FastAPI API, tests, Docker, read-only CI

## Quick start
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Why it matters
An agent can only be as safe and predictable as the tools it is allowed to call. ToolTrust treats the tool interface itself as a reliability boundary.

## Interview story
> “ToolTrust is about Agent Experience, not just prompts. I evaluate whether a tool is understandable, permissioned, recoverable, and safe to execute, then replay the decision path so a reviewer can see exactly where confirmation or validation stopped the action.”

## Evidence boundary
All execution is simulated. ToolTrust never calls external systems. A production system would add signed tool registries, policy-as-code, identity-aware permissions, durable audit logs, sandbox execution, secret handling, versioned schemas, and model-specific evaluation suites.

## CI setup status
The automated GitHub Actions workflow is pending upload authorization. The tests are included and can be run locally with python -m pytest. No passing GitHub CI run is claimed.

