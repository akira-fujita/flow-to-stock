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
