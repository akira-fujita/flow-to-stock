from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.cli import main
from src.llm_analyzer import TokenUsage
from src.models import AnalysisResult, DiscussionStructure, SlackMessage, SlackThread


def _make_thread() -> SlackThread:
    return SlackThread(
        channel_name="general",
        channel_id="C01234ABC",
        thread_ts="1705312200.123456",
        url="https://workspace.slack.com/archives/C01234ABC/p1705312200123456",
        messages=[
            SlackMessage(
                user="Alice",
                text="hello",
                timestamp=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
            ),
        ],
        last_reply_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
    )


def _make_analysis() -> AnalysisResult:
    return AnalysisResult(
        theme="Test Theme",
        structure=DiscussionStructure(
            premises=["p1"],
            key_issues=["k1"],
            conclusions_or_current_state=["c1"],
        ),
        next_decision_required="Decide X",
        suggested_next_action="Alice does Y by Friday",
        suggested_owner="Alice",
        new_concepts=["concept"],
        strategic_implications=["implication"],
        risk_signals=["risk"],
    )


class TestCli:
    @patch.dict(
        "os.environ",
        {
            "SLACK_USER_TOKEN": "xoxp-test",
            "GEMINI_API_KEY": "gemini-test",
        },
        clear=False,
    )
    @patch("src.cli.WebClient")
    @patch("src.cli.fetch_slack_thread")
    @patch("src.cli.parse_slack_thread_url")
    @patch("src.cli.analyze_thread")
    @patch("src.cli.save_to_notion")
    def test_main_no_save(
        self,
        mock_save,
        mock_analyze,
        mock_parse,
        mock_fetch,
        mock_webclient,
        capsys,
    ):
        mock_parse.return_value = ("C01234ABC", "1705312200.123456")
        mock_fetch.return_value = _make_thread()
        mock_analyze.return_value = (
            _make_analysis(),
            TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        mock_webclient.return_value = MagicMock()

        code = main(
            [
                "https://workspace.slack.com/archives/C01234ABC/p1705312200123456",
                "--no-save",
            ]
        )
        out = capsys.readouterr().out

        assert code == 0
        assert "Test Theme" in out
        assert '"total_tokens": 30' in out
        mock_save.assert_not_called()

    @patch.dict(
        "os.environ",
        {
            "SLACK_USER_TOKEN": "xoxp-test",
            "GEMINI_API_KEY": "gemini-test",
            "NOTION_TOKEN": "notion-test",
            "NOTION_DATABASE_ID": "db-test",
        },
        clear=False,
    )
    @patch("src.cli.WebClient")
    @patch("src.cli.fetch_slack_thread")
    @patch("src.cli.parse_slack_thread_url")
    @patch("src.cli.analyze_thread")
    @patch("src.cli.save_to_notion")
    def test_main_with_save(
        self,
        mock_save,
        mock_analyze,
        mock_parse,
        mock_fetch,
        mock_webclient,
    ):
        mock_parse.return_value = ("C01234ABC", "1705312200.123456")
        thread = _make_thread()
        analysis = _make_analysis()
        mock_fetch.return_value = thread
        mock_analyze.return_value = (
            analysis,
            TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        mock_save.return_value = "https://notion.so/page"
        mock_webclient.return_value = MagicMock()

        code = main(
            ["https://workspace.slack.com/archives/C01234ABC/p1705312200123456"]
        )
        assert code == 0
        mock_save.assert_called_once_with(
            "notion-test",
            "db-test",
            analysis,
            thread.url,
            thread.channel_name,
            None,
        )
