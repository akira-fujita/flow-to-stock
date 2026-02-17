# flow-to-stock

Convert Slack thread discussions into structured actions and insights, stored in a Notion database.

## Overview

flow-to-stock is a personal productivity tool that takes "flow" information (ephemeral Slack discussions) and converts it into "stock" knowledge (structured, searchable Notion records). It uses Google Gemini to analyze discussion threads and extract key decisions, action items, risks, and strategic implications.

## Features

- **Slack Thread Analysis** — Paste a Slack thread URL to fetch and analyze the discussion
- **LLM-Powered Structuring** — Gemini 2.0 Flash extracts themes, premises, key issues, conclusions, next actions, and more
- **Notion Persistence** — Save structured results to a Notion database with full property mapping
- **Deduplication** — Automatically updates existing entries when re-analyzing the same thread
- **Aging Tracker** — Calculates days since last activity on open discussions
- **Slack Reminders** — Sends DM reminders for discussions stale 7+ days
- **Token Usage Monitoring** — Tracks Gemini API token consumption per session

## Architecture

```
Slack Thread URL
      │
      ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│ Slack API    │────▶│ Gemini 2.0   │────▶│ Notion API    │
│ (slack-sdk)  │     │ Flash        │     │ (httpx)       │
└─────────────┘     └──────────────┘     └───────────────┘
      │                    │                     │
      ▼                    ▼                     ▼
  Fetch thread     Structured analysis     Save/update page
  messages         (JSON → Pydantic)       with 17 properties
```

## Project Structure

```
flow-to-stock/
├── app.py                  # Streamlit UI
├── pyproject.toml          # Dependencies & config
├── .env.example            # Environment variable template
├── src/
│   ├── models.py           # Pydantic data models
│   ├── slack_client.py     # Slack URL parser & thread fetcher
│   ├── llm_analyzer.py     # Gemini analysis with token tracking
│   ├── notion_client.py    # Notion API (direct httpx)
│   ├── cli.py              # Headless CLI entrypoint
│   └── aging.py            # Aging calculation & reminders
└── tests/
    ├── test_models.py
    ├── test_slack_client.py
    ├── test_llm_analyzer.py
    ├── test_notion_client.py
    ├── test_cli.py
    └── test_aging.py
```

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
git clone https://github.com/your-username/flow-to-stock.git
cd flow-to-stock
uv sync
```

### Environment Variables

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `SLACK_USER_TOKEN` | Slack User OAuth Token (`xoxp-...`) with `channels:history`, `channels:read`, `groups:history`, `groups:read`, `users:read` scopes |
| `SLACK_REMINDER_USER_ID` | Slack user ID to receive aging reminders |
| `NOTION_TOKEN` | Notion integration token |
| `NOTION_DATABASE_ID` | Target Notion database ID |
| `GEMINI_API_KEY` | Google Gemini API key |

### Notion Database Setup

Create a Notion database with the following properties:

| Property | Type |
|---|---|
| Title | Title |
| Slack URL | URL |
| Channel | Select |
| Status | Select (`Open`, `Waiting`, `Done`, `Archived`) |
| Next Decision Required | Rich Text |
| Next Action | Rich Text |
| Owner | Rich Text |
| Due Date | Date |
| Last Managed At | Date |
| Aging Days | Number |
| Premises | Rich Text |
| Key Issues | Rich Text |
| Current State | Rich Text |
| New Concepts | Multi-select |
| Strategic Implications | Rich Text |
| Risk Signals | Rich Text |
| Memo | Rich Text |

Connect your Notion integration to the database.

## Usage

After pulling latest changes, run dependency sync first:

```bash
uv sync
```

If another virtualenv is active, deactivate it before running `uv` commands.

### Streamlit UI

```bash
uv run streamlit run app.py
```

1. Paste a Slack thread URL
2. Optionally add context in the memo field
3. Click **Analyze** to run Gemini analysis
4. Review the structured output
5. Click **Save to Notion** to persist

### Headless CLI

You can run the same flow from command line with a Slack thread URL.

```bash
uv run flow-to-stock "https://your-workspace.slack.com/archives/C.../p..."
```

If the entry point is not found in your environment, use:

```bash
uv run python -m src.cli "https://your-workspace.slack.com/archives/C.../p..."
```

Optional flags:

- `--memo "..."` add extra context for LLM analysis
- `--no-save` analyze only (skip Notion persistence)
- `--model gemini-2.0-flash` override Gemini model

### Aging Management

Use the sidebar **Aging Update** button to:
- Recalculate aging days for all open/waiting discussions
- Send Slack DM reminders for discussions stale 7+ days

## Testing

```bash
uv run pytest tests/ -v
```

## License

MIT
