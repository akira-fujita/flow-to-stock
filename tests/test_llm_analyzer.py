import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.llm_analyzer import TokenUsage, analyze_thread, format_thread_for_prompt
from src.models import AnalysisResult, SlackMessage, SlackThread


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
        mock_response = MagicMock()
        mock_response.text = json.dumps(json_data)
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 200
        mock_response.usage_metadata.total_token_count = 300
        return mock_response

    @patch("src.llm_analyzer.genai.Client")
    def test_returns_analysis_result(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.return_value = self._mock_response(
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

        result, usage = analyze_thread(self._make_thread(), api_key="test-key")
        assert isinstance(result, AnalysisResult)
        assert result.theme == "API Design"
        assert result.suggested_owner == "Alice"
        assert isinstance(usage, TokenUsage)
        assert usage.total_tokens == 300

    @patch("src.llm_analyzer.genai.Client")
    def test_retries_on_json_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        bad_response = MagicMock()
        bad_response.text = "not json"
        bad_response.usage_metadata.prompt_token_count = 100
        bad_response.usage_metadata.candidates_token_count = 200
        bad_response.usage_metadata.total_token_count = 300

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

        mock_client.models.generate_content.side_effect = [bad_response, good_response]
        result, usage = analyze_thread(self._make_thread(), api_key="test-key")
        assert result.theme == "Retry Test"
        assert mock_client.models.generate_content.call_count == 2
        assert usage.total_tokens == 600  # 300 per attempt x 2

    @patch("src.llm_analyzer.genai.Client")
    def test_retries_on_validation_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        invalid_response = self._mock_response(
            {
                "theme": "Missing fields",
                "structure": {
                    "premises": [],
                    "key_issues": [],
                    "conclusions_or_current_state": [],
                },
                # required fields intentionally missing
            }
        )
        valid_response = self._mock_response(
            {
                "theme": "Recovered",
                "structure": {
                    "premises": [],
                    "key_issues": [],
                    "conclusions_or_current_state": [],
                },
                "next_decision_required": "Decide owner",
                "suggested_next_action": "Alice updates by Friday",
                "suggested_owner": "Alice",
                "new_concepts": [],
                "strategic_implications": [],
                "risk_signals": [],
            }
        )
        mock_client.models.generate_content.side_effect = [invalid_response, valid_response]

        result, usage = analyze_thread(self._make_thread(), api_key="test-key")
        assert result.theme == "Recovered"
        assert mock_client.models.generate_content.call_count == 2
        assert usage.total_tokens == 600
