from datetime import date
from unittest.mock import patch, MagicMock

from src.aging import calculate_aging_days, run_aging_update, send_reminders


class TestCalculateAgingDays:
    def test_zero_days(self):
        assert calculate_aging_days(date(2026, 2, 13), date(2026, 2, 13)) == 0

    def test_seven_days(self):
        assert calculate_aging_days(date(2026, 2, 6), date(2026, 2, 13)) == 7

    def test_one_day(self):
        assert calculate_aging_days(date(2026, 2, 12), date(2026, 2, 13)) == 1


def _make_page(page_id, status, last_managed, theme="Test", next_decision="Decide", slack_url="https://slack.com/test"):
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


class TestRunAgingUpdate:
    @patch("src.aging.httpx.patch")
    @patch("src.aging.httpx.post")
    def test_updates_aging_days(self, mock_post, mock_patch):
        query_resp = MagicMock()
        query_resp.json.return_value = {
            "results": [_make_page("p1", "Open", "2026-02-06")],
        }
        query_resp.raise_for_status = MagicMock()
        mock_post.return_value = query_resp

        update_resp = MagicMock()
        update_resp.raise_for_status = MagicMock()
        mock_patch.return_value = update_resp

        result = run_aging_update("test-token", "db-id", today=date(2026, 2, 13))
        assert result["updated"] == 1
        mock_patch.assert_called_once()
        call_json = mock_patch.call_args[1]["json"]
        assert call_json["properties"]["Aging Days"]["number"] == 7

    @patch("src.aging.httpx.patch")
    @patch("src.aging.httpx.post")
    def test_returns_reminder_candidates(self, mock_post, mock_patch):
        query_resp = MagicMock()
        query_resp.json.return_value = {
            "results": [
                _make_page("p1", "Open", "2026-02-01"),
                _make_page("p2", "Waiting", "2026-02-01"),
                _make_page("p3", "Open", "2026-02-12"),
            ],
        }
        query_resp.raise_for_status = MagicMock()
        mock_post.return_value = query_resp

        update_resp = MagicMock()
        update_resp.raise_for_status = MagicMock()
        mock_patch.return_value = update_resp

        result = run_aging_update("test-token", "db-id", today=date(2026, 2, 13))
        assert result["updated"] == 3
        # Open + Aging >= 7 のみリマインド対象
        assert len(result["reminders"]) == 1
        assert result["reminders"][0]["page_id"] == "p1"


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
