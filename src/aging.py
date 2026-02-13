from datetime import date

import httpx
from slack_sdk import WebClient

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def calculate_aging_days(last_managed: date, today: date) -> int:
    """Calculate aging days between last managed date and today."""
    return (today - last_managed).days


def run_aging_update(
    token: str,
    database_id: str,
    today: date | None = None,
) -> dict:
    """Update aging days for all active pages.

    Returns dict with 'updated' count and 'reminders' list.
    """
    if today is None:
        today = date.today()

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
    response = resp.json()

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

        update_resp = httpx.patch(
            f"{BASE_URL}/pages/{page['id']}",
            headers=_headers(token),
            json={"properties": {"Aging Days": {"number": aging_days}}},
        )
        update_resp.raise_for_status()
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
