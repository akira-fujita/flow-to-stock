# flow-to-stock Design Document

## 1. Purpose

Slack discussions tend to flow away and get lost. This personal tool:
1. Converts discussions into **Next Actions** (decisions + concrete steps)
2. Structures and accumulates **insights** (premises, concepts, risks)

It is a personal Decision & Insight OS.

## 2. Scope

**In scope (MVP):**
- Personal use only
- Slack thread URL as input (via Web UI)
- LLM-powered structured analysis (Claude)
- Notion Database storage
- Manual aging update with reminder notifications
- Optional memo field

**Out of scope:**
- Multi-user / organization features
- Clustering, similarity analysis
- Term frequency analysis
- Automated scheduling (manual button for MVP)

## 3. Tech Stack

| Component | Technology |
|-----------|-----------|
| UI | Streamlit |
| Backend | Python (monolithic, modular packages) |
| LLM | Anthropic Claude (claude-sonnet-4-5-20250929) |
| Slack API | slack-sdk |
| Notion API | notion-client |
| Data Models | Pydantic |
| Package Manager | uv |
| Deployment | Local machine (macOS) |

## 4. Project Structure

```
flow-to-stock/
├── pyproject.toml
├── .env.example
├── .env                    # (gitignored)
├── app.py                  # Streamlit entry point
├── src/
│   ├── __init__.py
│   ├── models.py           # Pydantic models
│   ├── slack_client.py     # Slack API client
│   ├── llm_analyzer.py     # Claude structured extraction
│   ├── notion_client.py    # Notion API client
│   └── aging.py            # Aging + reminder logic
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_slack_client.py
│   ├── test_llm_analyzer.py
│   ├── test_notion_client.py
│   └── test_aging.py
└── docs/
    └── plans/
```

## 5. Overall Flow

```
1. User enters Slack thread URL (+ optional memo) in Streamlit UI
2. Slack API fetches thread (parent + all replies + metadata)
3. Claude analyzes thread → structured JSON output
4. User reviews analysis result in UI
5. User clicks "Save to Notion" → page created in Notion DB
6. User clicks "Run Aging Update" → aging recalculated + reminders sent
```

## 6. Slack Thread Fetching

**Input:** Slack thread URL (e.g., `https://workspace.slack.com/archives/C01234ABC/p1234567890123456`)

**URL Parsing:**
- Channel ID: segment after `/archives/`
- Thread TS: `p` prefix removed, dot inserted at position -6 (e.g., `p1234567890123456` → `1234567890.123456`)

**API Calls:**
- `conversations.info` → channel name
- `conversations.replies` → parent message + all replies

**Data Models:**
```python
class SlackMessage(BaseModel):
    user: str           # display name
    text: str
    timestamp: datetime

class SlackThread(BaseModel):
    channel_name: str
    channel_id: str
    thread_ts: str
    url: str
    messages: list[SlackMessage]
    last_reply_at: datetime
```

**Auth:** `SLACK_BOT_TOKEN` env var. Required scopes: `channels:read`, `channels:history`, `groups:read`, `groups:history`, `users:read`.

## 7. LLM Structured Analysis

**Input:** `SlackThread` + optional memo

**Process:**
1. Format thread messages into prompt text
2. Call Claude API with JSON output instruction
3. Validate response with Pydantic model

**Output Schema:**
```python
class DiscussionStructure(BaseModel):
    premises: list[str]
    key_issues: list[str]
    conclusions_or_current_state: list[str]

class AnalysisResult(BaseModel):
    theme: str
    structure: DiscussionStructure
    next_decision_required: str
    suggested_next_action: str
    suggested_owner: str
    new_concepts: list[str]
    strategic_implications: list[str]
    risk_signals: list[str]
```

**Prompt Design:**
- System prompt instructs structured analysis with exact JSON schema
- User message contains formatted thread + memo
- Output language matches input language (Japanese → Japanese, English → English)

**Error Handling:**
- JSON parse failure → 1 retry
- Validation failure → show error to user

## 8. Notion Database Integration

**Database:** `Slack Decision Tracker` (created manually beforehand)

**Property Mapping:**

| Notion Property | Type | Source |
|----------------|------|--------|
| Title | Title | `theme` |
| Slack URL | URL | input URL |
| Channel | Select | `channel_name` |
| Status | Select | initial `Open` |
| Next Decision Required | Rich Text | `next_decision_required` |
| Next Action | Rich Text | `suggested_next_action` |
| Owner | Rich Text | `suggested_owner` |
| Due Date | Date | empty (manual) |
| Last Managed At | Date | creation datetime |
| Aging Days | Number | `0` (at creation) |
| Premises | Rich Text | `premises` (newline-separated) |
| Key Issues | Rich Text | `key_issues` (newline-separated) |
| Current State | Rich Text | `conclusions_or_current_state` (newline-separated) |
| New Concepts | Multi-select | `new_concepts` |
| Strategic Implications | Rich Text | `strategic_implications` (newline-separated) |
| Risk Signals | Rich Text | `risk_signals` (newline-separated) |
| Memo | Rich Text | manual memo from input |

**Notes:**
- Owner is Rich Text (not Person) due to Notion API limitations for external writes
- Duplicate detection: query by Slack URL before creating; update if exists
- New Concepts as Multi-select enables tag accumulation and reuse

**Auth:** `NOTION_TOKEN` + `NOTION_DATABASE_ID` env vars.

## 9. Aging & Reminders

**Aging Calculation:**
```
Aging Days = today - Last Managed At
```

**Scope:** All pages where `Status != Done` AND `Status != Archived`

**Slack DM Notification:**

Condition: `Status = Open` AND `Aging Days >= 7`

Message:
```
This discussion has not progressed.
Theme: {theme}
Next Decision Required: {next_decision_required}
Aging Days: {aging_days}
Slack URL: {slack_url}
```

Recipient: `SLACK_REMINDER_USER_ID` env var (self DM).

**Trigger:** Manual "Run Aging Update" button in Streamlit sidebar.

## 10. Streamlit UI Design

**Sidebar:**
- API connection status indicators
- "Run Aging Update" button
- Update results display

**Main Area:**

1. **Input Form**
   - Slack Thread URL (text input, required)
   - Memo (text area, optional)
   - "Analyze" button

2. **Analysis Result** (after analyze)
   - Theme (heading)
   - Discussion structure (premises / key issues / current state in expandable sections)
   - Next Decision Required (highlighted)
   - Next Action + Owner
   - New Concepts (tag display)
   - Strategic Implications / Risk Signals
   - **"Save to Notion" button**

3. **Status Display**
   - Spinner during processing
   - Notion page URL link on success
   - Error message on failure

**Flow:** Input URL → Analyze → Review results → Approve → Save to Notion

## 11. Environment Variables

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_REMINDER_USER_ID=U...
NOTION_TOKEN=secret_...
NOTION_DATABASE_ID=...
ANTHROPIC_API_KEY=sk-ant-...
```

## 12. Success Criteria

1. Every Slack discussion is converted to a Next Action
2. Unprocessed discussions are visible (aging)
3. New concepts accumulate over time
4. Weekly review becomes easy via Notion views
