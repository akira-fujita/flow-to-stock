import argparse
import json
import os
import sys

from dotenv import load_dotenv
from slack_sdk import WebClient

from src.llm_analyzer import analyze_thread
from src.notion_client import save_to_notion
from src.slack_client import fetch_slack_thread, parse_slack_thread_url


def _require_env(key: str) -> str:
    value = os.environ.get(key, "")
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flow-to-stock",
        description="Headless processing for Slack thread -> analysis -> Notion",
    )
    parser.add_argument("slack_url", help="Slack thread URL")
    parser.add_argument("--memo", default=None, help="Optional memo/context")
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash",
        help="Gemini model name",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Analyze only (skip Notion save)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        slack_token = _require_env("SLACK_USER_TOKEN")
        gemini_api_key = _require_env("GEMINI_API_KEY")
        notion_token = ""
        notion_db_id = ""
        if not args.no_save:
            notion_token = _require_env("NOTION_TOKEN")
            notion_db_id = _require_env("NOTION_DATABASE_ID")

        channel_id, thread_ts = parse_slack_thread_url(args.slack_url)
        slack = WebClient(token=slack_token)
        thread = fetch_slack_thread(slack, channel_id, thread_ts, args.slack_url)

        analysis, token_usage = analyze_thread(
            thread,
            gemini_api_key,
            memo=args.memo,
            model=args.model,
        )

        print(json.dumps(analysis.model_dump(), ensure_ascii=False, indent=2))
        print(
            json.dumps(
                {
                    "prompt_tokens": token_usage.prompt_tokens,
                    "completion_tokens": token_usage.completion_tokens,
                    "total_tokens": token_usage.total_tokens,
                },
                ensure_ascii=False,
            )
        )

        if not args.no_save:
            page_url = save_to_notion(
                notion_token,
                notion_db_id,
                analysis,
                thread.url,
                thread.channel_name,
                args.memo,
            )
            print(json.dumps({"notion_page_url": page_url}, ensure_ascii=False))

        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
