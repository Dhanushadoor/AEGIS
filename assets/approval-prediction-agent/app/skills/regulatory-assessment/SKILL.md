---
name: regulatory-assessment
description: Step-by-step instructions for assessing a business request against SAP product regulations and historical approval data to produce a prediction verdict with confidence score
allowed-tools:
  - regulatory_data_check
  - historical_approval_lookup
---

# Regulatory Assessment Skill

## When to Use This Skill

Load this skill when the user requests an assessment of a business request for SAP product licensing or usage approval.

## Prerequisites

Before starting the assessment, ensure the following request parameters have been collected and confirmed with the user:
- SAP product name
- Intended usage type (e.g. production use, development use, resale, integration)
- Region / country
- Business justification
- Requestor organisation name

Do not proceed with the assessment until the user has confirmed these parameters.

## Assessment Instructions

### Step 1: Regulatory Compliance Check

1. Use the available MCP tools to query the SAP Regulatory Data Assessment API with the product name, usage type, and region as input.
2. Retrieve the list of applicable regulatory rules and any compliance flags.
3. If the tool returns an error, report the error verbatim and proceed with a partial assessment note.
4. Record:
   - Total number of rules evaluated
   - Number of compliance flags raised
   - Specific rules violated (if any)

### Step 2: Historical Approval Data Query

1. Use the available MCP tools to query historical approval records from the Ariba Approval API.
2. Filter by product name, usage type, and region where possible.
3. If the tool returns an error, proceed with regulatory data only and note reduced confidence.
4. Record:
   - Approval/rejection ratio for similar requests
   - Key decision factors from past approvals
   - Common rejection reasons for similar requests

### Step 3: Synthesise Prediction

Based on Steps 1 and 2, determine the verdict using this decision matrix:

| Regulatory Flags | Historical Approval Rate | Verdict |
|-----------------|--------------------------|---------|
| 0 flags | > 70% approval | Approved |
| 0 flags | 40–70% approval | Needs More Info |
| 1–2 minor flags | > 70% approval | Needs More Info |
| Any critical flags | Any | Rejected |
| 3+ flags | Any | Rejected |
| 0 flags | < 40% approval | Needs More Info |

Assign a confidence score (0–100%):
- Start at 80%
- Subtract 10% for each compliance flag
- Subtract 15% if historical approval rate is below 50%
- Add 10% if historical approval rate is above 80%
- Cap at 95% (never claim absolute certainty)
- Floor at 5% (never claim absolute rejection)

**Important:** If confidence is below 60%, explicitly flag low confidence in the response and recommend human review before formal submission.

### Step 4: Format the Response

Return the assessment as a structured response containing:

1. **Verdict**: Approved / Rejected / Needs More Info
2. **Confidence Score**: percentage (0–100%)
3. **Rationale**: 2–4 sentence summary of the key factors
4. **Gap List** (only when verdict is Rejected or Needs More Info):
   - Numbered list of missing fields or information items
   - Non-compliant items with the specific rule violated
   - Suggested correction for each item

### Step 5: Offer Iterative Re-assessment

After delivering the prediction, inform the user:
- If verdict is Approved: "You may proceed with formal submission when ready."
- If verdict is Rejected or Needs More Info: "Please address the gaps listed above. You can share your updated request details and I will run a new assessment."

## Error Handling

- If both the regulatory check and historical lookup fail: inform the user that no assessment can be performed at this time and suggest retrying later.
- If one source is unavailable: proceed with the available data, clearly noting reduced confidence.
- Never fabricate regulatory rules or historical approval data — only report what the tools return.
