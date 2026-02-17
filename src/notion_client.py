from datetime import date

import httpx

from src.models import AnalysisResult

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


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
    token: str, database_id: str, slack_url: str
) -> str | None:
    """Find an existing page by Slack URL. Returns page ID or None."""
    resp = httpx.post(
        f"{BASE_URL}/databases/{database_id}/query",
        headers=_headers(token),
        json={"filter": {"property": "Slack URL", "url": {"equals": slack_url}}},
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if results:
        return results[0]["id"]
    return None


def save_to_notion(
    token: str,
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

    existing_page_id = find_existing_page(token, database_id, slack_url)

    if existing_page_id:
        resp = httpx.patch(
            f"{BASE_URL}/pages/{existing_page_id}",
            headers=_headers(token),
            json={"properties": properties},
        )
        resp.raise_for_status()
        return f"https://notion.so/{existing_page_id.replace('-', '')}"
    else:
        resp = httpx.post(
            f"{BASE_URL}/pages",
            headers=_headers(token),
            json={
                "parent": {"database_id": database_id},
                "properties": properties,
            },
        )
        resp.raise_for_status()
        page_id = resp.json()["id"]
        return f"https://notion.so/{page_id.replace('-', '')}"


def fetch_open_pages(token: str, database_id: str) -> list[dict]:
    """Fetch Open/Waiting pages from Notion database.

    Returns list of dicts with: page_id, title, slack_url, aging_days, status.
    """
    resp = httpx.post(
        f"{BASE_URL}/databases/{database_id}/query",
        headers=_headers(token),
        json={
            "filter": {
                "and": [
                    {"property": "Status", "select": {"does_not_equal": "Done"}},
                    {"property": "Status", "select": {"does_not_equal": "Archived"}},
                ]
            }
        },
    )
    resp.raise_for_status()

    pages = []
    for page in resp.json().get("results", []):
        props = page["properties"]
        slack_url = props.get("Slack URL", {}).get("url")
        if not slack_url:
            continue

        title_parts = props.get("Title", {}).get("title", [])
        title = title_parts[0]["text"]["content"] if title_parts else "Untitled"

        aging_days = props.get("Aging Days", {}).get("number", 0)
        status = props.get("Status", {}).get("select", {}).get("name", "")

        pages.append({
            "page_id": page["id"],
            "title": title,
            "slack_url": slack_url,
            "aging_days": aging_days,
            "status": status,
        })

    return pages
