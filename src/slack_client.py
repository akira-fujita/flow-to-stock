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
