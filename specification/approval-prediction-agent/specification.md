# Specification: approval-prediction-agent

> **Guidelines**: Read all applicable guidelines before executing ANY tasks below:
> - [guidelines.md](../guidelines.md) — Universal execution rules
> - [guidelines-agent.md](../guidelines-agent.md) — Universal agent patterns
> - [guidelines-agent-python.md](../guidelines-agent-python.md) — Python implementation details
> - [guidelines-agent-skills.md](../guidelines-agent-skills.md) — Runtime skills patterns
> - [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) — MCP integration patterns

---

## Data Dependencies

_No Data Product ORD IDs. All data is accessed via SAP APIs (see API Integrations below)._

---

## Basic Setup

- [x] Read `product-requirements-document.md` and `intent.md` for full context on agent behaviour, milestones, and requirements.
- [x] Bootstrap agent code in `assets/approval-prediction-agent/` using instructions from the `sap-agent-bootstrap` section in the agent skill. Run bootstrap commands from inside `assets/approval-prediction-agent/` using copy commands — do NOT create files manually.
- [x] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`.

---

## Runtime Skills

> Read [guidelines-agent-skills.md](../guidelines-agent-skills.md) before deciding.

The agent requires a runtime skill for SAP product regulatory rules and approval assessment logic — this complexity warrants a dedicated skill rather than bloating the system prompt.

- [x] Create `assets/approval-prediction-agent/app/skills/regulatory-assessment/SKILL.md` with:
  - YAML frontmatter: `name: regulatory-assessment`, `description: Step-by-step instructions for assessing a business request against SAP product regulations and historical approval data`, `allowed-tools: [regulatory_data_check, historical_approval_lookup]`
  - Body: Instructions for how to evaluate a request — extract parameters, check regulatory compliance, query historical data, synthesise a verdict and confidence score, list gap items.

---

## Project-Specific Tasks

### Request Input Capture (R1)

- [x] In `app/agent.py`, update the system prompt to instruct the agent to extract the following parameters from the user's natural language description: SAP product name, intended usage type, region/country, business justification, and requestor organisation. The agent must confirm the extracted parameters with the user before running an assessment.
- [x] Implement a confirmation step: after extraction, the agent presents the parameters back to the user and asks "Is this correct? Please confirm or correct before I run the assessment."

### Regulatory Compliance Check (R2)

- [x] Implement the `regulatory_data_check` tool in `app/agent.py` to query the SAP Regulatory Data Assessment API via the generated MCP server. The tool takes product name, usage type, and region as inputs and returns applicable compliance rules and any flags.
- [x] The tool must be read-only — no write operations against the regulatory data API.
- [x] Implement error handling: if the API is unavailable, return a partial assessment flag and inform the user.

**MCP tool scope:** read-only  
**Entities in scope:** RegulatoryDataAssessment, RegulatoryCheck, ApplicableRule

### Historical Approval Data Query (R3)

- [x] Implement the `historical_approval_lookup` tool in `app/agent.py` to query historical approval records via the Ariba Approval MCP server. The tool takes product name, usage type, and region as inputs and returns past approval/rejection patterns and key decision factors.
- [x] The tool must be read-only — no write operations against the Ariba API.
- [x] Implement error handling: if the API is unavailable, proceed with regulatory data only and flag the reduced confidence to the user.

**MCP tool scope:** read-only  
**Entities in scope:** ApprovalRequest, ApprovalDecision, ApprovalHistory

### Prediction Output with Confidence Score (R4)

- [x] Implement a `prediction_scorer` internal function (not an MCP tool — pure agent logic) in `app/agent.py` that synthesises results from `regulatory_data_check` and `historical_approval_lookup` into a structured response containing:
  - Verdict: one of `Approved`, `Rejected`, or `Needs More Info`
  - Confidence score: integer 0–100%
  - Rationale: 2–4 sentence explanation of the factors driving the verdict
- [x] When confidence is below 60%, the response must include a mandatory advisory: "Confidence is below 60%. We recommend reviewing the gaps below and consulting the SAP approval team before submitting."

### Gap and Deficiency Explanation (R5)

- [x] When the verdict is `Rejected` or `Needs More Info`, the agent must return a structured list of:
  - Missing fields or information items
  - Non-compliant items (with the specific rule violated)
  - Suggested corrections for each gap item
- [x] Format the gap list as a numbered list in the response for clarity.

### Iterative Re-assessment (R6)

- [x] The agent must support follow-up messages in the same session: if the user provides updated request details after receiving a prediction, the agent re-runs the full assessment (Steps R2–R5) and returns a new verdict. No session restart is required.
- [x] The agent must track and reference the previous verdict in the follow-up response (e.g., "Your previous prediction was Rejected at 40% confidence. Based on your updates, here is the new assessment...").

---

## API Integrations

Two API specs have been downloaded to `specification/approval-prediction-agent/api-specs/`:

| API | ORD ID | Spec file | Type |
|-----|--------|-----------|------|
| SAP Regulatory Data Assessment | `sap.s4:apiResource:CE_REGULATORYDATAASSESSMENT_0001:v1` | `api-specs/regulatory-data-assessment-api-spec.edmx` | OData (EDMX) |
| SAP Ariba Approval API | `sap.aribabuyer:apiResource:approval:v2` | `api-specs/ariba-approval-api-spec.json` | REST (OpenAPI JSON) |

- [x] Invoke the `mcp-translation-file` skill for `regulatory-data-assessment-api-spec.edmx` (OData/EDMX) with ORD ID `sap.s4:apiResource:CE_REGULATORYDATAASSESSMENT_0001:v1`.
- [x] Invoke the `mcp-translation-file` skill for `ariba-approval-api-spec.json` (REST/OpenAPI) with ORD ID `sap.aribabuyer:apiResource:approval:v2`.
- [x] After both translation files are generated, invoke the `setup-solution` skill to register the MCP server assets in `solution.yaml` and `asset.yaml`.

---

## Business Instrumentation

- [x] Instrument all five milestones from the PRD with structured logging and OpenTelemetry spans. Follow the log pattern `[MILESTONE_ID].[achieved|missed]: [description]`. Use `guidelines-agent-python.md` for Python-specific span implementation.

  | Milestone | Achieved log | Missed log |
  |-----------|-------------|------------|
  | M1: Request Captured | `M1.achieved: request parameters captured and confirmed — product={product}, region={region}, usage_type={usage_type}` | `M1.missed: request capture incomplete — required fields not provided by user` |
  | M2: Regulatory Assessment Complete | `M2.achieved: regulatory assessment complete — {n} rules evaluated, {m} flags raised` | `M2.missed: regulatory assessment did not complete — API unavailable or no matching rules found` |
  | M3: Prediction Generated | `M3.achieved: prediction generated — verdict={verdict}, confidence={score}%` | `M3.missed: prediction generation failed — insufficient data or internal error` |
  | M4: Customer Review | `M4.achieved: user reviewed prediction — action={refine|proceed|abandon}` | `M4.missed: no user response received after prediction delivery` |
  | M5: Formal Submission Initiated | `M5.achieved: user initiated formal submission — confidence_at_submission={score}%` | `M5.missed: user did not proceed to formal submission — verdict={verdict}, reason={low_confidence|user_abandoned}` |

- [x] Verify `bootstrap(app)` is called after `app = server.build()` in `main.py`.

---

## MCP Tool Integration

> Read [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) for complete MCP integration patterns.

- [x] After `mcp-translation-file` skill completes and new MCP assets are registered, verify `api-specs/` contains both spec files.
- [x] Wire MCP tool loading in `agent.py` using `get_mcp_tools()` from the `mcp_tools` module (bootstrap-generated indirection layer). NEVER import directly from `sap_cloud_sdk.agentgateway`. NEVER create direct HTTP clients for SAP APIs.
- [x] Add both MCP server dependencies to `asset.yaml` under `requires` — one entry per MCP server, using exact ORD IDs from generated assets. See [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) for the format.
- [x] Generate `mcp-mock.json` using the `mcp-mock-config` skill after both MCP assets are ready (required before tests can run).

---

## Testing

> See [guidelines-agent-python.md](../guidelines-agent-python.md) for Python testing setup and patterns.

- [x] `conftest.py` only sets `IBD_TESTING=true` so the agent runs with mock MCP tool results during tests.
- [x] Write one unit test per tool: `test_regulatory_data_check.py`, `test_historical_approval_lookup.py`, `test_prediction_scorer.py`. Run each immediately after writing.
- [x] Write one integration test that runs an end-to-end agent flow: submit a sample request, verify the agent returns a verdict, confidence score, and rationale. Mock all external systems (LLM, MCP servers). Test must run offline.
- [x] Write one integration test for the iterative re-assessment flow: submit a request, receive a prediction, submit an update, verify a new prediction is returned referencing the prior one.
- [x] Run `pytest` from `assets/approval-prediction-agent/` (no args) — if coverage < 70%, add tests until threshold is met.
- [x] Run `pytest` again to generate the final `test_report.json`.
- [x] Verify `test_report.json` exists in `assets/approval-prediction-agent/`.
