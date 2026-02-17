from unittest.mock import patch, MagicMock

from src.models import AnalysisResult, DiscussionStructure
from src.notion_client import build_notion_properties, fetch_open_pages, find_existing_page, save_to_notion


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


class TestFindExistingPage:
    @patch("src.notion_client.httpx.post")
    def test_returns_page_id_when_found(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [{"id": "page-123"}]}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = find_existing_page("test-token", "db-id", "https://slack.com/test")
        assert result == "page-123"

    @patch("src.notion_client.httpx.post")
    def test_returns_none_when_not_found(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = find_existing_page("test-token", "db-id", "https://slack.com/test")
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

    @patch("src.notion_client.httpx.post")
    def test_creates_new_page(self, mock_post):
        # First call: find_existing_page (no results)
        query_resp = MagicMock()
        query_resp.json.return_value = {"results": []}
        query_resp.raise_for_status = MagicMock()

        # Second call: create page
        create_resp = MagicMock()
        create_resp.json.return_value = {"id": "new-page-id"}
        create_resp.raise_for_status = MagicMock()

        mock_post.side_effect = [query_resp, create_resp]

        url = save_to_notion(
            "test-token", "db-id", self._make_result(),
            "https://slack.com/test", "general", None,
        )
        assert mock_post.call_count == 2
        assert "newpageid" in url

    @patch("src.notion_client.httpx.patch")
    @patch("src.notion_client.httpx.post")
    def test_updates_existing_page(self, mock_post, mock_patch):
        # find_existing_page returns a result
        query_resp = MagicMock()
        query_resp.json.return_value = {"results": [{"id": "existing-id"}]}
        query_resp.raise_for_status = MagicMock()
        mock_post.return_value = query_resp

        # patch call for update
        update_resp = MagicMock()
        update_resp.raise_for_status = MagicMock()
        mock_patch.return_value = update_resp

        url = save_to_notion(
            "test-token", "db-id", self._make_result(),
            "https://slack.com/test", "general", None,
        )
        mock_patch.assert_called_once()
        assert mock_post.call_count == 1  # only query, no create


class TestFetchOpenPages:
    @patch("src.notion_client.httpx.post")
    def test_returns_page_list(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {
                    "id": "page-1",
                    "properties": {
                        "Title": {"title": [{"text": {"content": "議論A"}}]},
                        "Slack URL": {"url": "https://slack.com/archives/C01/p111"},
                        "Last Managed At": {"date": {"start": "2026-02-10"}},
                        "Aging Days": {"number": 7},
                        "Status": {"select": {"name": "Open"}},
                        "Memo": {"rich_text": [{"text": {"content": "補足メモ"}}]},
                    },
                },
                {
                    "id": "page-2",
                    "properties": {
                        "Title": {"title": [{"text": {"content": "議論B"}}]},
                        "Slack URL": {"url": "https://slack.com/archives/C02/p222"},
                        "Last Managed At": {"date": {"start": "2026-02-15"}},
                        "Aging Days": {"number": 2},
                        "Status": {"select": {"name": "Waiting"}},
                        "Memo": {"rich_text": []},
                    },
                },
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        pages = fetch_open_pages("test-token", "db-id")
        assert len(pages) == 2
        assert pages[0]["page_id"] == "page-1"
        assert pages[0]["title"] == "議論A"
        assert pages[0]["slack_url"] == "https://slack.com/archives/C01/p111"
        assert pages[0]["aging_days"] == 7
        assert pages[0]["status"] == "Open"
        assert pages[0]["memo"] == "補足メモ"
        assert pages[1]["memo"] is None

    @patch("src.notion_client.httpx.post")
    def test_returns_empty_list_when_no_pages(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        pages = fetch_open_pages("test-token", "db-id")
        assert pages == []

    @patch("src.notion_client.httpx.post")
    def test_skips_page_without_slack_url(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {
                    "id": "page-no-url",
                    "properties": {
                        "Title": {"title": [{"text": {"content": "No URL"}}]},
                        "Slack URL": {"url": None},
                        "Last Managed At": {"date": {"start": "2026-02-10"}},
                        "Aging Days": {"number": 3},
                        "Status": {"select": {"name": "Open"}},
                    },
                },
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        pages = fetch_open_pages("test-token", "db-id")
        assert pages == []
