from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from slack_sdk import WebClient

from src.slack_client import fetch_slack_thread, parse_slack_thread_url


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
