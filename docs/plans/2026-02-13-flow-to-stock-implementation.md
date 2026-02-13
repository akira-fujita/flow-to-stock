# flow-to-stock Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a personal Streamlit tool that converts Slack thread discussions into structured actions and insights, stored in Notion.

**Architecture:** Monolithic Streamlit app with modular Python packages under `src/`. Slack SDK fetches threads, Claude API extracts structured data, Notion client saves results. Manual aging update button in sidebar.

**Tech Stack:** Python 3.12+, Streamlit, slack-sdk, anthropic, notion-client, Pydantic v2, uv, pytest

---

### Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Modify: `.gitignore` (add `.env`)

**Step 1: Initialize uv project and add dependencies**

Run:
```bash
cd /Users/akira.fujita/Documents/GitHub/flow-to-stock
uv init --no-readme
```

Then manually write `pyproject.toml` (uv init creates a basic one, we'll overwrite):

```toml
[project]
name = "flow-to-stock"
version = "0.1.0"
description = "Convert Slack discussions into actions and insights"
requires-python = ">=3.12"
dependencies = [
    "streamlit>=1.40.0",
    "slack-sdk>=3.33.0",
    "anthropic>=0.40.0",
    "notion-client>=2.2.0",
    "pydantic>=2.10.0",
    "python-dotenv>=1.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: Install dependencies**

Run: `uv sync`
Expected: All packages installed, `uv.lock` created.

**Step 3: Create package init files**

Create `src/__init__.py`:
```python
```

Create `tests/__init__.py`:
```python
```

**Step 4: Create .env.example**

```
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_REMINDER_USER_ID=U00000000
NOTION_TOKEN=secret_your-token-here
NOTION_DATABASE_ID=your-database-id-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Step 5: Verify .gitignore includes .env**

Check `.gitignore` already contains `.env` line (it does from the Python template). No change needed.

**Step 6: Commit**

```bash
git add pyproject.toml uv.lock .env.example src/__init__.py tests/__init__.py .python-version
git commit -m "chore: initialize project with uv and dependencies"
```

---

### Task 2: Pydantic Models

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

**Step 1: Write failing tests for SlackMessage and SlackThread models**

Create `tests/test_models.py`:

```python
from datetime import datetime

from src.models import (
    AnalysisResult,
    DiscussionStructure,
    SlackMessage,
    SlackThread,
)


class TestSlackMessage:
    def test_create_message(self):
        msg = SlackMessage(
            user="alice",
            text="Hello world",
            timestamp=datetime(2026, 1, 15, 10, 30, 0),
        )
        assert msg.user == "alice"
        assert msg.text == "Hello world"
        assert msg.timestamp == datetime(2026, 1, 15, 10, 30, 0)


class TestSlackThread:
    def test_create_thread(self):
        msg = SlackMessage(
            user="alice",
            text="Hello",
            timestamp=datetime(2026, 1, 15, 10, 30, 0),
        )
        thread = SlackThread(
            channel_name="general",
            channel_id="C01234ABC",
            thread_ts="1234567890.123456",
            url="https://workspace.slack.com/archives/C01234ABC/p1234567890123456",
            messages=[msg],
            last_reply_at=datetime(2026, 1, 15, 10, 30, 0),
        )
        assert thread.channel_name == "general"
        assert thread.channel_id == "C01234ABC"
        assert len(thread.messages) == 1

    def test_thread_requires_messages(self):
        thread = SlackThread(
            channel_name="general",
            channel_id="C01234ABC",
            thread_ts="1234567890.123456",
            url="https://workspace.slack.com/archives/C01234ABC/p1234567890123456",
            messages=[],
            last_reply_at=datetime(2026, 1, 15, 10, 30, 0),
        )
        assert thread.messages == []


class TestDiscussionStructure:
    def test_create_structure(self):
        structure = DiscussionStructure(
            premises=["We need a new API"],
            key_issues=["Performance vs simplicity"],
            conclusions_or_current_state=["Going with REST for now"],
        )
        assert len(structure.premises) == 1
        assert len(structure.key_issues) == 1


class TestAnalysisResult:
    def test_create_result(self):
        result = AnalysisResult(
            theme="API Design Discussion",
            structure=DiscussionStructure(
                premises=["Need scalable API"],
                key_issues=["REST vs GraphQL"],
                conclusions_or_current_state=["REST chosen"],
            ),
            next_decision_required="Choose authentication method",
            suggested_next_action="Alice to draft auth spec by Friday",
            suggested_owner="alice",
            new_concepts=["API gateway", "rate limiting"],
            strategic_implications=["Sets architecture for 2 years"],
            risk_signals=["No consensus on auth"],
        )
        assert result.theme == "API Design Discussion"
        assert len(result.new_concepts) == 2
        assert result.suggested_owner == "alice"

    def test_result_allows_empty_lists(self):
        result = AnalysisResult(
            theme="Quick sync",
            structure=DiscussionStructure(
                premises=[],
                key_issues=[],
                conclusions_or_current_state=[],
            ),
            next_decision_required="None",
            suggested_next_action="No action needed",
            suggested_owner="",
            new_concepts=[],
            strategic_implications=[],
            risk_signals=[],
        )
        assert result.new_concepts == []
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.models'`

**Step 3: Write the models**

Create `src/models.py`:

```python
from datetime import datetime

from pydantic import BaseModel


class SlackMessage(BaseModel):
    user: str
    text: str
    timestamp: datetime


class SlackThread(BaseModel):
    channel_name: str
    channel_id: str
    thread_ts: str
    url: str
    messages: list[SlackMessage]
    last_reply_at: datetime


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

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add Pydantic models for Slack thread and analysis result"
```

---

### Task 3: Slack URL Parser

**Files:**
- Create: `src/slack_client.py` (start with parsing only)
- Create: `tests/test_slack_client.py`

**Step 1: Write failing tests for URL parsing**

Create `tests/test_slack_client.py`:

```python
import pytest

from src.slack_client import parse_slack_thread_url


class TestParseSlackThreadUrl:
    def test_standard_url(self):
        url = "https://myworkspace.slack.com/archives/C01234ABC/p1705312200123456"
        channel_id, thread_ts = parse_slack_thread_url(url)
        assert channel_id == "C01234ABC"
        assert thread_ts == "1705312200.123456"

    def test_url_with_query_params(self):
        url = "https://myworkspace.slack.com/archives/C01234ABC/p1705312200123456?thread_ts=1705312200.123456&cid=C01234ABC"
        channel_id, thread_ts = parse_slack_thread_url(url)
        assert channel_id == "C01234ABC"
        assert thread_ts == "1705312200.123456"

    def test_private_channel_url(self):
        url = "https://myworkspace.slack.com/archives/G01234ABC/p1705312200123456"
        channel_id, thread_ts = parse_slack_thread_url(url)
        assert channel_id == "G01234ABC"
        assert thread_ts == "1705312200.123456"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Invalid Slack thread URL"):
            parse_slack_thread_url("https://google.com")

    def test_missing_message_id_raises(self):
        with pytest.raises(ValueError, match="Invalid Slack thread URL"):
            parse_slack_thread_url("https://myworkspace.slack.com/archives/C01234ABC")
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_slack_client.py::TestParseSlackThreadUrl -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement URL parser**

Create `src/slack_client.py`:

```python
import re
from datetime import datetime, timezone

from slack_sdk import WebClient

from src.models import SlackMessage, SlackThread


def parse_slack_thread_url(url: str) -> tuple[str, str]:
    """Parse a Slack thread URL into (channel_id, thread_ts).

    URL format: https://<workspace>.slack.com/archives/<channel_id>/p<timestamp>
    The p-prefixed timestamp has no dot; insert dot 6 chars from end.
    """
    pattern = r"slack\.com/archives/([A-Z0-9]+)/p(\d+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"Invalid Slack thread URL: {url}")

    channel_id = match.group(1)
    raw_ts = match.group(2)
    thread_ts = f"{raw_ts[:-6]}.{raw_ts[-6:]}"
    return channel_id, thread_ts
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_slack_client.py::TestParseSlackThreadUrl -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add src/slack_client.py tests/test_slack_client.py
git commit -m "feat: add Slack thread URL parser"
```

---

### Task 4: Slack API Client (fetch thread)

**Files:**
- Modify: `src/slack_client.py`
- Modify: `tests/test_slack_client.py`

**Step 1: Write failing tests for thread fetching (mocked)**

Append to `tests/test_slack_client.py`:

```python
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.slack_client import fetch_slack_thread


class TestFetchSlackThread:
    def _mock_client(self):
        client = MagicMock(spec=WebClient)
        client.conversations_info.return_value = {
            "channel": {"name": "general"}
        }
        client.conversations_replies.return_value = {
            "messages": [
                {
                    "user": "U001",
                    "text": "Let's discuss the API",
                    "ts": "1705312200.123456",
                },
                {
                    "user": "U002",
                    "text": "I think REST is better",
                    "ts": "1705312260.654321",
                },
            ]
        }
        client.users_info.side_effect = lambda user: {
            "user": {
                "real_name": {"U001": "Alice", "U002": "Bob"}[user]
            }
        }
        return client

    def test_fetch_returns_slack_thread(self):
        client = self._mock_client()
        thread = fetch_slack_thread(
            client,
            "C01234ABC",
            "1705312200.123456",
            "https://workspace.slack.com/archives/C01234ABC/p1705312200123456",
        )
        assert thread.channel_name == "general"
        assert thread.channel_id == "C01234ABC"
        assert len(thread.messages) == 2
        assert thread.messages[0].user == "Alice"
        assert thread.messages[1].user == "Bob"
        assert thread.messages[0].text == "Let's discuss the API"

    def test_fetch_sets_last_reply_at(self):
        client = self._mock_client()
        thread = fetch_slack_thread(
            client,
            "C01234ABC",
            "1705312200.123456",
            "https://workspace.slack.com/archives/C01234ABC/p1705312200123456",
        )
        assert thread.last_reply_at == datetime.fromtimestamp(
            1705312260.654321, tz=timezone.utc
        )
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_slack_client.py::TestFetchSlackThread -v`
Expected: FAIL with `ImportError: cannot import name 'fetch_slack_thread'`

**Step 3: Implement fetch_slack_thread**

Add to `src/slack_client.py`:

```python
def fetch_slack_thread(
    client: WebClient,
    channel_id: str,
    thread_ts: str,
    url: str,
) -> SlackThread:
    """Fetch a Slack thread and return structured data."""
    channel_info = client.conversations_info(channel=channel_id)
    channel_name = channel_info["channel"]["name"]

    replies = client.conversations_replies(channel=channel_id, ts=thread_ts)
    raw_messages = replies["messages"]

    # Cache user lookups
    user_cache: dict[str, str] = {}

    def get_user_name(user_id: str) -> str:
        if user_id not in user_cache:
            user_info = client.users_info(user=user_id)
            user_cache[user_id] = user_info["user"]["real_name"]
        return user_cache[user_id]

    messages = []
    for msg in raw_messages:
        messages.append(
            SlackMessage(
                user=get_user_name(msg["user"]),
                text=msg["text"],
                timestamp=datetime.fromtimestamp(float(msg["ts"]), tz=timezone.utc),
            )
        )

    last_reply_at = messages[-1].timestamp if messages else datetime.now(tz=timezone.utc)

    return SlackThread(
        channel_name=channel_name,
        channel_id=channel_id,
        thread_ts=thread_ts,
        url=url,
        messages=messages,
        last_reply_at=last_reply_at,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_slack_client.py -v`
Expected: All 7 tests PASS.

**Step 5: Commit**

```bash
git add src/slack_client.py tests/test_slack_client.py
git commit -m "feat: add Slack thread fetching with user name resolution"
```

---

### Task 5: LLM Analyzer

**Files:**
- Create: `src/llm_analyzer.py`
- Create: `tests/test_llm_analyzer.py`

**Step 1: Write failing tests for prompt formatting**

Create `tests/test_llm_analyzer.py`:

```python
from datetime import datetime, timezone

from src.llm_analyzer import format_thread_for_prompt
from src.models import SlackMessage, SlackThread


class TestFormatThreadForPrompt:
    def test_formats_messages(self):
        thread = SlackThread(
            channel_name="general",
            channel_id="C01234ABC",
            thread_ts="1705312200.123456",
            url="https://workspace.slack.com/archives/C01234ABC/p1705312200123456",
            messages=[
                SlackMessage(
                    user="Alice",
                    text="Let's discuss the API design",
                    timestamp=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
                ),
                SlackMessage(
                    user="Bob",
                    text="I prefer REST",
                    timestamp=datetime(2026, 1, 15, 10, 31, 0, tzinfo=timezone.utc),
                ),
            ],
            last_reply_at=datetime(2026, 1, 15, 10, 31, 0, tzinfo=timezone.utc),
        )
        result = format_thread_for_prompt(thread)
        assert "Alice" in result
        assert "Bob" in result
        assert "Let's discuss the API design" in result
        assert "#general" in result

    def test_includes_memo_when_provided(self):
        thread = SlackThread(
            channel_name="general",
            channel_id="C01234ABC",
            thread_ts="1705312200.123456",
            url="https://workspace.slack.com/archives/C01234ABC/p1705312200123456",
            messages=[
                SlackMessage(
                    user="Alice",
                    text="Hello",
                    timestamp=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
                ),
            ],
            last_reply_at=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )
        result = format_thread_for_prompt(thread, memo="Important context here")
        assert "Important context here" in result
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_llm_analyzer.py::TestFormatThreadForPrompt -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement format_thread_for_prompt**

Create `src/llm_analyzer.py`:

```python
import json

import anthropic

from src.models import AnalysisResult, SlackThread

SYSTEM_PROMPT = """You are an expert at analyzing Slack discussions and extracting structured insights.

Given a Slack thread, analyze the discussion and output a JSON object with the following structure:
{
  "theme": "One-line summary of the discussion topic",
  "structure": {
    "premises": ["List of assumptions and preconditions"],
    "key_issues": ["Main points of discussion, disagreements, or unresolved items"],
    "conclusions_or_current_state": ["Current conclusions or state of the discussion"]
  },
  "next_decision_required": "The specific decision that must be made to move forward (not a vague TODO)",
  "suggested_next_action": "Concrete action: who does what by when",
  "suggested_owner": "Person most likely responsible (from thread participants)",
  "new_concepts": ["New terms, concepts, or keywords introduced in this discussion"],
  "strategic_implications": ["Medium/long-term impacts or architectural implications"],
  "risk_signals": ["Undefined risks, misalignments, or uncertainties detected"]
}

Rules:
- Output ONLY valid JSON, no markdown fences, no extra text
- Match the language of the input: if the discussion is in Japanese, output in Japanese
- next_decision_required must be a specific decision, not a generic TODO
- suggested_next_action must include who, what, and when
- Be concise but thorough"""


def format_thread_for_prompt(thread: SlackThread, memo: str | None = None) -> str:
    """Format a SlackThread into a text prompt for the LLM."""
    lines = [f"Channel: #{thread.channel_name}", ""]

    for msg in thread.messages:
        ts_str = msg.timestamp.strftime("%Y-%m-%d %H:%M")
        lines.append(f"[{ts_str}] {msg.user}: {msg.text}")

    if memo:
        lines.append("")
        lines.append(f"Additional context from the user: {memo}")

    return "\n".join(lines)


def analyze_thread(
    thread: SlackThread,
    api_key: str,
    memo: str | None = None,
    model: str = "claude-sonnet-4-5-20250929",
) -> AnalysisResult:
    """Analyze a Slack thread using Claude and return structured result."""
    client = anthropic.Anthropic(api_key=api_key)
    prompt_text = format_thread_for_prompt(thread, memo)

    for attempt in range(2):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt_text}],
        )

        raw_text = response.content[0].text

        try:
            data = json.loads(raw_text)
            return AnalysisResult.model_validate(data)
        except (json.JSONDecodeError, Exception):
            if attempt == 0:
                continue
            raise

    raise RuntimeError("Failed to parse LLM response after retries")
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_llm_analyzer.py::TestFormatThreadForPrompt -v`
Expected: 2 tests PASS.

**Step 5: Write failing test for analyze_thread (mocked)**

Append to `tests/test_llm_analyzer.py`:

```python
import json
from unittest.mock import MagicMock, patch

from src.llm_analyzer import analyze_thread
from src.models import AnalysisResult


class TestAnalyzeThread:
    def _make_thread(self):
        return SlackThread(
            channel_name="general",
            channel_id="C01234ABC",
            thread_ts="1705312200.123456",
            url="https://workspace.slack.com/archives/C01234ABC/p1705312200123456",
            messages=[
                SlackMessage(
                    user="Alice",
                    text="Let's discuss the API",
                    timestamp=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
                ),
            ],
            last_reply_at=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )

    def _mock_response(self, json_data: dict):
        mock_content = MagicMock()
        mock_content.text = json.dumps(json_data)
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        return mock_response

    @patch("src.llm_analyzer.anthropic.Anthropic")
    def test_returns_analysis_result(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._mock_response(
            {
                "theme": "API Design",
                "structure": {
                    "premises": ["Need API"],
                    "key_issues": ["REST vs GraphQL"],
                    "conclusions_or_current_state": ["REST chosen"],
                },
                "next_decision_required": "Choose auth method",
                "suggested_next_action": "Alice to draft spec by Friday",
                "suggested_owner": "Alice",
                "new_concepts": ["API gateway"],
                "strategic_implications": ["Sets direction"],
                "risk_signals": ["No auth consensus"],
            }
        )

        result = analyze_thread(self._make_thread(), api_key="test-key")
        assert isinstance(result, AnalysisResult)
        assert result.theme == "API Design"
        assert result.suggested_owner == "Alice"

    @patch("src.llm_analyzer.anthropic.Anthropic")
    def test_retries_on_json_error(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        bad_content = MagicMock()
        bad_content.text = "not json"
        bad_response = MagicMock()
        bad_response.content = [bad_content]

        good_response = self._mock_response(
            {
                "theme": "Retry Test",
                "structure": {
                    "premises": [],
                    "key_issues": [],
                    "conclusions_or_current_state": [],
                },
                "next_decision_required": "None",
                "suggested_next_action": "None",
                "suggested_owner": "",
                "new_concepts": [],
                "strategic_implications": [],
                "risk_signals": [],
            }
        )

        mock_client.messages.create.side_effect = [bad_response, good_response]
        result = analyze_thread(self._make_thread(), api_key="test-key")
        assert result.theme == "Retry Test"
        assert mock_client.messages.create.call_count == 2
```

**Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_llm_analyzer.py -v`
Expected: All 4 tests PASS.

**Step 7: Commit**

```bash
git add src/llm_analyzer.py tests/test_llm_analyzer.py
git commit -m "feat: add LLM analyzer with Claude structured extraction"
```

---

### Task 6: Notion Client

**Files:**
- Create: `src/notion_client.py`
- Create: `tests/test_notion_client.py`

**Step 1: Write failing tests for Notion property building**

Create `tests/test_notion_client.py`:

```python
from datetime import datetime, timezone

from src.models import AnalysisResult, DiscussionStructure
from src.notion_client import build_notion_properties


class TestBuildNotionProperties:
    def _make_result(self):
        return AnalysisResult(
            theme="API Design Discussion",
            structure=DiscussionStructure(
                premises=["Need scalable API", "Must support mobile"],
                key_issues=["REST vs GraphQL"],
                conclusions_or_current_state=["REST chosen"],
            ),
            next_decision_required="Choose auth method",
            suggested_next_action="Alice to draft spec by Friday",
            suggested_owner="Alice",
            new_concepts=["API gateway", "rate limiting"],
            strategic_implications=["Sets architecture for 2 years"],
            risk_signals=["No auth consensus"],
        )

    def test_builds_title(self):
        props = build_notion_properties(
            result=self._make_result(),
            slack_url="https://slack.com/archives/C01/p123",
            channel_name="general",
            memo=None,
        )
        assert props["Title"]["title"][0]["text"]["content"] == "API Design Discussion"

    def test_builds_slack_url(self):
        props = build_notion_properties(
            result=self._make_result(),
            slack_url="https://slack.com/archives/C01/p123",
            channel_name="general",
            memo=None,
        )
        assert props["Slack URL"]["url"] == "https://slack.com/archives/C01/p123"

    def test_builds_status_as_open(self):
        props = build_notion_properties(
            result=self._make_result(),
            slack_url="https://slack.com/archives/C01/p123",
            channel_name="general",
            memo=None,
        )
        assert props["Status"]["select"]["name"] == "Open"

    def test_builds_new_concepts_as_multiselect(self):
        props = build_notion_properties(
            result=self._make_result(),
            slack_url="https://slack.com/archives/C01/p123",
            channel_name="general",
            memo=None,
        )
        concepts = props["New Concepts"]["multi_select"]
        assert len(concepts) == 2
        assert concepts[0]["name"] == "API gateway"

    def test_includes_memo_when_provided(self):
        props = build_notion_properties(
            result=self._make_result(),
            slack_url="https://slack.com/archives/C01/p123",
            channel_name="general",
            memo="Extra context here",
        )
        memo_text = props["Memo"]["rich_text"][0]["text"]["content"]
        assert "Extra context here" in memo_text

    def test_omits_memo_when_none(self):
        props = build_notion_properties(
            result=self._make_result(),
            slack_url="https://slack.com/archives/C01/p123",
            channel_name="general",
            memo=None,
        )
        assert props["Memo"]["rich_text"] == []
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_notion_client.py::TestBuildNotionProperties -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement build_notion_properties and Notion client**

Create `src/notion_client.py`:

```python
from datetime import date, datetime, timezone

from notion_client import Client as NotionAPIClient

from src.models import AnalysisResult


def _rich_text(text: str) -> dict:
    """Create a Notion rich text property value."""
    if not text:
        return {"rich_text": []}
    return {"rich_text": [{"text": {"content": text}}]}


def _rich_text_from_list(items: list[str]) -> dict:
    """Create rich text from a list, newline-separated."""
    return _rich_text("\n".join(items))


def build_notion_properties(
    result: AnalysisResult,
    slack_url: str,
    channel_name: str,
    memo: str | None,
) -> dict:
    """Build Notion page properties from analysis result."""
    today = date.today().isoformat()

    props = {
        "Title": {"title": [{"text": {"content": result.theme}}]},
        "Slack URL": {"url": slack_url},
        "Channel": {"select": {"name": channel_name}},
        "Status": {"select": {"name": "Open"}},
        "Next Decision Required": _rich_text(result.next_decision_required),
        "Next Action": _rich_text(result.suggested_next_action),
        "Owner": _rich_text(result.suggested_owner),
        "Last Managed At": {"date": {"start": today}},
        "Aging Days": {"number": 0},
        "Premises": _rich_text_from_list(result.structure.premises),
        "Key Issues": _rich_text_from_list(result.structure.key_issues),
        "Current State": _rich_text_from_list(
            result.structure.conclusions_or_current_state
        ),
        "New Concepts": {
            "multi_select": [{"name": c} for c in result.new_concepts]
        },
        "Strategic Implications": _rich_text_from_list(
            result.strategic_implications
        ),
        "Risk Signals": _rich_text_from_list(result.risk_signals),
        "Memo": _rich_text(memo) if memo else {"rich_text": []},
    }

    return props


def find_existing_page(
    client: NotionAPIClient, database_id: str, slack_url: str
) -> str | None:
    """Find an existing page by Slack URL. Returns page ID or None."""
    response = client.databases.query(
        database_id=database_id,
        filter={"property": "Slack URL", "url": {"equals": slack_url}},
    )
    results = response.get("results", [])
    if results:
        return results[0]["id"]
    return None


def save_to_notion(
    client: NotionAPIClient,
    database_id: str,
    result: AnalysisResult,
    slack_url: str,
    channel_name: str,
    memo: str | None,
) -> str:
    """Save analysis result to Notion. Returns the page URL.

    Updates existing page if same Slack URL found, otherwise creates new.
    """
    properties = build_notion_properties(result, slack_url, channel_name, memo)

    existing_page_id = find_existing_page(client, database_id, slack_url)

    if existing_page_id:
        client.pages.update(page_id=existing_page_id, properties=properties)
        return f"https://notion.so/{existing_page_id.replace('-', '')}"
    else:
        page = client.pages.create(
            parent={"database_id": database_id},
            properties=properties,
        )
        page_id = page["id"]
        return f"https://notion.so/{page_id.replace('-', '')}"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_notion_client.py -v`
Expected: All 6 tests PASS.

**Step 5: Write tests for save_to_notion (mocked)**

Append to `tests/test_notion_client.py`:

```python
from unittest.mock import MagicMock

from src.notion_client import save_to_notion, find_existing_page


class TestFindExistingPage:
    def test_returns_page_id_when_found(self):
        client = MagicMock()
        client.databases.query.return_value = {
            "results": [{"id": "page-123"}]
        }
        result = find_existing_page(client, "db-id", "https://slack.com/test")
        assert result == "page-123"

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.databases.query.return_value = {"results": []}
        result = find_existing_page(client, "db-id", "https://slack.com/test")
        assert result is None


class TestSaveToNotion:
    def _make_result(self):
        return AnalysisResult(
            theme="Test Theme",
            structure=DiscussionStructure(
                premises=["p1"],
                key_issues=["k1"],
                conclusions_or_current_state=["c1"],
            ),
            next_decision_required="Decide X",
            suggested_next_action="Do Y",
            suggested_owner="Alice",
            new_concepts=["concept1"],
            strategic_implications=["impl1"],
            risk_signals=["risk1"],
        )

    def test_creates_new_page(self):
        client = MagicMock()
        client.databases.query.return_value = {"results": []}
        client.pages.create.return_value = {"id": "new-page-id"}

        url = save_to_notion(
            client, "db-id", self._make_result(),
            "https://slack.com/test", "general", None,
        )
        client.pages.create.assert_called_once()
        assert "newpageid" in url

    def test_updates_existing_page(self):
        client = MagicMock()
        client.databases.query.return_value = {
            "results": [{"id": "existing-id"}]
        }

        url = save_to_notion(
            client, "db-id", self._make_result(),
            "https://slack.com/test", "general", None,
        )
        client.pages.update.assert_called_once()
        client.pages.create.assert_not_called()
```

**Step 6: Run all Notion tests**

Run: `uv run pytest tests/test_notion_client.py -v`
Expected: All 10 tests PASS.

**Step 7: Commit**

```bash
git add src/notion_client.py tests/test_notion_client.py
git commit -m "feat: add Notion client with page creation, update, and dedup"
```

---

### Task 7: Aging & Reminder Logic

**Files:**
- Create: `src/aging.py`
- Create: `tests/test_aging.py`

**Step 1: Write failing tests for aging calculation**

Create `tests/test_aging.py`:

```python
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

from src.aging import calculate_aging_days, run_aging_update


class TestCalculateAgingDays:
    def test_zero_days(self):
        assert calculate_aging_days(date(2026, 2, 13), date(2026, 2, 13)) == 0

    def test_seven_days(self):
        assert calculate_aging_days(date(2026, 2, 6), date(2026, 2, 13)) == 7

    def test_one_day(self):
        assert calculate_aging_days(date(2026, 2, 12), date(2026, 2, 13)) == 1


class TestRunAgingUpdate:
    def _make_page(self, page_id: str, status: str, last_managed: str, theme: str = "Test", next_decision: str = "Decide", slack_url: str = "https://slack.com/test"):
        return {
            "id": page_id,
            "properties": {
                "Status": {"select": {"name": status}},
                "Last Managed At": {"date": {"start": last_managed}},
                "Title": {"title": [{"text": {"content": theme}}]},
                "Next Decision Required": {
                    "rich_text": [{"text": {"content": next_decision}}]
                },
                "Slack URL": {"url": slack_url},
            },
        }

    def test_updates_aging_days(self):
        client = MagicMock()
        client.databases.query.return_value = {
            "results": [
                self._make_page("p1", "Open", "2026-02-06"),
            ],
            "has_more": False,
        }

        result = run_aging_update(
            client, "db-id", today=date(2026, 2, 13)
        )
        assert result["updated"] == 1
        client.pages.update.assert_called_once()
        call_props = client.pages.update.call_args[1]["properties"]
        assert call_props["Aging Days"]["number"] == 7

    def test_returns_reminder_candidates(self):
        client = MagicMock()
        client.databases.query.return_value = {
            "results": [
                self._make_page("p1", "Open", "2026-02-01"),
                self._make_page("p2", "Waiting", "2026-02-01"),
                self._make_page("p3", "Open", "2026-02-12"),
            ],
            "has_more": False,
        }

        result = run_aging_update(
            client, "db-id", today=date(2026, 2, 13)
        )
        assert result["updated"] == 3
        # Only Open + Aging >= 7 should be in reminders
        assert len(result["reminders"]) == 1
        assert result["reminders"][0]["page_id"] == "p1"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_aging.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement aging module**

Create `src/aging.py`:

```python
from datetime import date

from notion_client import Client as NotionAPIClient
from slack_sdk import WebClient


def calculate_aging_days(last_managed: date, today: date) -> int:
    """Calculate aging days between last managed date and today."""
    return (today - last_managed).days


def run_aging_update(
    client: NotionAPIClient,
    database_id: str,
    today: date | None = None,
) -> dict:
    """Update aging days for all active pages.

    Returns dict with 'updated' count and 'reminders' list.
    """
    if today is None:
        today = date.today()

    # Query pages where Status != Done AND Status != Archived
    response = client.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Status", "select": {"does_not_equal": "Done"}},
                {"property": "Status", "select": {"does_not_equal": "Archived"}},
            ]
        },
    )

    pages = response.get("results", [])
    reminders = []
    updated = 0

    for page in pages:
        props = page["properties"]
        last_managed_prop = props.get("Last Managed At", {}).get("date")
        if not last_managed_prop or not last_managed_prop.get("start"):
            continue

        last_managed = date.fromisoformat(last_managed_prop["start"])
        aging_days = calculate_aging_days(last_managed, today)

        client.pages.update(
            page_id=page["id"],
            properties={"Aging Days": {"number": aging_days}},
        )
        updated += 1

        status = props.get("Status", {}).get("select", {}).get("name", "")
        if status == "Open" and aging_days >= 7:
            title_parts = props.get("Title", {}).get("title", [])
            theme = title_parts[0]["text"]["content"] if title_parts else "Unknown"

            ndr_parts = props.get("Next Decision Required", {}).get("rich_text", [])
            next_decision = ndr_parts[0]["text"]["content"] if ndr_parts else ""

            slack_url = props.get("Slack URL", {}).get("url", "")

            reminders.append(
                {
                    "page_id": page["id"],
                    "theme": theme,
                    "next_decision_required": next_decision,
                    "aging_days": aging_days,
                    "slack_url": slack_url,
                }
            )

    return {"updated": updated, "reminders": reminders}


def send_reminders(
    slack_client: WebClient,
    user_id: str,
    reminders: list[dict],
) -> int:
    """Send Slack DM reminders for stale discussions.

    Returns number of messages sent.
    """
    sent = 0
    for r in reminders:
        text = (
            f"This discussion has not progressed.\n"
            f"Theme: {r['theme']}\n"
            f"Next Decision Required: {r['next_decision_required']}\n"
            f"Aging Days: {r['aging_days']}\n"
            f"Slack URL: {r['slack_url']}"
        )
        slack_client.chat_postMessage(channel=user_id, text=text)
        sent += 1
    return sent
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_aging.py -v`
Expected: All 4 tests PASS.

**Step 5: Write test for send_reminders**

Append to `tests/test_aging.py`:

```python
from src.aging import send_reminders


class TestSendReminders:
    def test_sends_dm_for_each_reminder(self):
        slack_client = MagicMock()
        reminders = [
            {
                "page_id": "p1",
                "theme": "API Design",
                "next_decision_required": "Choose auth",
                "aging_days": 10,
                "slack_url": "https://slack.com/test",
            },
            {
                "page_id": "p2",
                "theme": "DB Migration",
                "next_decision_required": "Pick timeline",
                "aging_days": 8,
                "slack_url": "https://slack.com/test2",
            },
        ]
        sent = send_reminders(slack_client, "U001", reminders)
        assert sent == 2
        assert slack_client.chat_postMessage.call_count == 2

    def test_sends_nothing_for_empty_list(self):
        slack_client = MagicMock()
        sent = send_reminders(slack_client, "U001", [])
        assert sent == 0
        slack_client.chat_postMessage.assert_not_called()
```

**Step 6: Run all aging tests**

Run: `uv run pytest tests/test_aging.py -v`
Expected: All 6 tests PASS.

**Step 7: Commit**

```bash
git add src/aging.py tests/test_aging.py
git commit -m "feat: add aging calculation and Slack DM reminders"
```

---

### Task 8: Streamlit UI

**Files:**
- Create: `app.py`

**Step 1: Implement the full Streamlit app**

Note: Streamlit apps are not easily unit-tested. This task is implementation-only, relying on the thoroughly tested modules underneath.

Create `app.py`:

```python
import os

import streamlit as st
from dotenv import load_dotenv
from notion_client import Client as NotionAPIClient
from slack_sdk import WebClient

from src.aging import run_aging_update, send_reminders
from src.llm_analyzer import analyze_thread
from src.notion_client import save_to_notion
from src.slack_client import fetch_slack_thread, parse_slack_thread_url

load_dotenv()

st.set_page_config(page_title="flow-to-stock", page_icon="🔄", layout="wide")
st.title("flow-to-stock")
st.caption("Slack議論を「行動」と「思考資産」に変換する")


def get_slack_client() -> WebClient:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        st.error("SLACK_BOT_TOKEN が設定されていません。.env を確認してください。")
        st.stop()
    return WebClient(token=token)


def get_notion_client() -> NotionAPIClient:
    token = os.environ.get("NOTION_TOKEN", "")
    if not token:
        st.error("NOTION_TOKEN が設定されていません。.env を確認してください。")
        st.stop()
    return NotionAPIClient(auth=token)


def get_notion_database_id() -> str:
    db_id = os.environ.get("NOTION_DATABASE_ID", "")
    if not db_id:
        st.error("NOTION_DATABASE_ID が設定されていません。.env を確認してください。")
        st.stop()
    return db_id


def get_anthropic_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        st.error("ANTHROPIC_API_KEY が設定されていません。.env を確認してください。")
        st.stop()
    return key


# --- Sidebar: Aging Update ---
with st.sidebar:
    st.header("Aging管理")
    if st.button("Aging更新を実行"):
        with st.spinner("Aging更新中..."):
            notion = get_notion_client()
            db_id = get_notion_database_id()
            result = run_aging_update(notion, db_id)
            st.success(f"更新完了: {result['updated']}件")

            if result["reminders"]:
                slack = get_slack_client()
                user_id = os.environ.get("SLACK_REMINDER_USER_ID", "")
                if user_id:
                    sent = send_reminders(slack, user_id, result["reminders"])
                    st.info(f"リマインド送信: {sent}件")
                else:
                    st.warning("SLACK_REMINDER_USER_ID 未設定のためリマインド送信をスキップ")

                st.subheader("停滞中の議論")
                for r in result["reminders"]:
                    st.markdown(
                        f"- **{r['theme']}** ({r['aging_days']}日) "
                        f"[Slack]({r['slack_url']})"
                    )
            else:
                st.info("停滞している議論はありません。")

# --- Main: Input Form ---
st.header("Slack スレッドを分析")

slack_url = st.text_input(
    "Slack Thread URL",
    placeholder="https://your-workspace.slack.com/archives/C.../p...",
)
memo = st.text_area("補足メモ（任意）", placeholder="追加のコンテキストがあれば入力")

if st.button("分析する", type="primary", disabled=not slack_url):
    with st.spinner("Slackスレッドを取得中..."):
        try:
            channel_id, thread_ts = parse_slack_thread_url(slack_url)
            slack = get_slack_client()
            thread = fetch_slack_thread(slack, channel_id, thread_ts, slack_url)
        except ValueError as e:
            st.error(f"URL解析エラー: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Slack取得エラー: {e}")
            st.stop()

    with st.spinner("Claude で分析中..."):
        try:
            api_key = get_anthropic_api_key()
            analysis = analyze_thread(
                thread, api_key, memo=memo if memo else None
            )
        except Exception as e:
            st.error(f"分析エラー: {e}")
            st.stop()

    # Store in session state for the save step
    st.session_state["analysis"] = analysis
    st.session_state["thread"] = thread
    st.session_state["memo"] = memo if memo else None

# --- Display Analysis Result ---
if "analysis" in st.session_state:
    analysis = st.session_state["analysis"]
    thread = st.session_state["thread"]

    st.divider()
    st.subheader(analysis.theme)

    with st.expander("議論の構造", expanded=True):
        if analysis.structure.premises:
            st.markdown("**前提条件:**")
            for p in analysis.structure.premises:
                st.markdown(f"- {p}")
        if analysis.structure.key_issues:
            st.markdown("**主要論点:**")
            for k in analysis.structure.key_issues:
                st.markdown(f"- {k}")
        if analysis.structure.conclusions_or_current_state:
            st.markdown("**現状・結論:**")
            for c in analysis.structure.conclusions_or_current_state:
                st.markdown(f"- {c}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🎯 次に決めること:**")
        st.info(analysis.next_decision_required)
    with col2:
        st.markdown("**📋 次のアクション:**")
        st.info(analysis.suggested_next_action)

    st.markdown(f"**担当者:** {analysis.suggested_owner}")

    if analysis.new_concepts:
        st.markdown("**新しい概念:**")
        st.markdown(" ".join([f"`{c}`" for c in analysis.new_concepts]))

    if analysis.strategic_implications:
        with st.expander("戦略的示唆"):
            for s in analysis.strategic_implications:
                st.markdown(f"- {s}")

    if analysis.risk_signals:
        with st.expander("リスクシグナル"):
            for r in analysis.risk_signals:
                st.markdown(f"- ⚠️ {r}")

    st.divider()

    if st.button("Notionに保存", type="primary"):
        with st.spinner("Notionに保存中..."):
            try:
                notion = get_notion_client()
                db_id = get_notion_database_id()
                page_url = save_to_notion(
                    notion,
                    db_id,
                    analysis,
                    thread.url,
                    thread.channel_name,
                    st.session_state.get("memo"),
                )
                st.success(f"保存完了!")
                st.markdown(f"[Notionで開く]({page_url})")
                # Clear session state after save
                del st.session_state["analysis"]
                del st.session_state["thread"]
                del st.session_state["memo"]
            except Exception as e:
                st.error(f"Notion保存エラー: {e}")
```

**Step 2: Smoke test the app**

Run: `uv run streamlit run app.py`

Verify the UI loads without errors (API calls will fail without .env, but the UI structure should render). Press Ctrl+C to stop.

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add Streamlit UI with analysis and Notion save flow"
```

---

### Task 9: Run Full Test Suite

**Step 1: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests pass (approximately 17 tests).

**Step 2: Fix any failures**

If any tests fail, fix them before proceeding.

**Step 3: Final commit (if fixes were needed)**

```bash
git add -A
git commit -m "fix: resolve test failures from integration"
```

---

### Task 10: Final Cleanup & .env.example

**Step 1: Verify .env.example is complete**

Read `.env.example` and confirm it matches the design doc section 11.

**Step 2: Run full test suite one more time**

Run: `uv run pytest tests/ -v`
Expected: All pass.

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup for MVP"
```

---

## Summary

| Task | Description | Estimated Tests |
|------|------------|----------------|
| 1 | Project setup (uv, deps) | 0 |
| 2 | Pydantic models | 5 |
| 3 | Slack URL parser | 5 |
| 4 | Slack API client (fetch) | 2 |
| 5 | LLM analyzer | 4 |
| 6 | Notion client | 10 |
| 7 | Aging & reminders | 6 |
| 8 | Streamlit UI | 0 (manual) |
| 9 | Full test suite run | - |
| 10 | Final cleanup | - |
| **Total** | | **~32 tests** |
