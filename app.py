import os

import streamlit as st
from dotenv import load_dotenv
from slack_sdk import WebClient

from src.aging import run_aging_update, send_reminders
from src.llm_analyzer import analyze_thread
from src.notion_client import save_to_notion
from src.slack_client import fetch_slack_thread, parse_slack_thread_url

load_dotenv()

st.set_page_config(page_title="flow-to-stock", page_icon="🔄", layout="wide")


def get_secret(key: str) -> str:
    """Get a secret from st.secrets (Streamlit Cloud) or os.environ (local)."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.environ.get(key, "")


# --- パスワード認証 ---
app_password = get_secret("APP_PASSWORD")
if app_password:
    password = st.text_input("Password", type="password")
    if not password:
        st.stop()
    if password != app_password:
        st.error("パスワードが違います")
        st.stop()

st.title("flow-to-stock")
st.caption("Slack議論を「行動」と「思考資産」に変換する")


def get_slack_client() -> WebClient:
    token = get_secret("SLACK_USER_TOKEN")
    if not token:
        st.error("SLACK_USER_TOKEN が設定されていません。")
        st.stop()
    return WebClient(token=token)


def get_notion_token() -> str:
    token = get_secret("NOTION_TOKEN")
    if not token:
        st.error("NOTION_TOKEN が設定されていません。")
        st.stop()
    return token


def get_notion_database_id() -> str:
    db_id = get_secret("NOTION_DATABASE_ID")
    if not db_id:
        st.error("NOTION_DATABASE_ID が設定されていません。")
        st.stop()
    return db_id


def get_gemini_api_key() -> str:
    key = get_secret("GEMINI_API_KEY")
    if not key:
        st.error("GEMINI_API_KEY が設定されていません。")
        st.stop()
    return key


# --- サイドバー ---
with st.sidebar:
    # トークン使用量
    if "session_total_tokens" not in st.session_state:
        st.session_state["session_total_tokens"] = 0
    st.metric("セッション累計トークン", f"{st.session_state['session_total_tokens']:,}")
    if "token_usage" in st.session_state:
        usage = st.session_state["token_usage"]
        st.caption(f"直近: 入力 {usage.prompt_tokens:,} / 出力 {usage.completion_tokens:,}")
    st.caption("Gemini 2.0 Flash 無料枠: 1,500 req/日")
    st.divider()

    st.header("Aging管理")
    if st.button("Aging更新を実行"):
        with st.spinner("Aging更新中..."):
            notion_token = get_notion_token()
            db_id = get_notion_database_id()
            result = run_aging_update(notion_token, db_id)
            st.success(f"更新完了: {result['updated']}件")

            if result["reminders"]:
                slack = get_slack_client()
                user_id = get_secret("SLACK_REMINDER_USER_ID")
                if user_id:
                    sent = send_reminders(slack, user_id, result["reminders"])
                    st.info(f"リマインド送信: {sent}件")
                else:
                    st.warning("SLACK_REMINDER_USER_ID 未設定のためリマインド送信をスキップ")

                st.subheader("停滞中の議論")
                for r in result["reminders"]:
                    st.markdown(
                        f"- **{r['theme']}** ({r['aging_days']}日) "
                        f"[Slack]({r['slack_url']})"
                    )
            else:
                st.info("停滞している議論はありません。")

# --- メイン: 入力フォーム ---
st.header("Slack スレッドを分析")

slack_url = st.text_input(
    "Slack Thread URL",
    placeholder="https://your-workspace.slack.com/archives/C.../p...",
)
memo = st.text_area("補足メモ（任意）", placeholder="追加のコンテキストがあれば入力")

if st.button("分析する", type="primary", disabled=not slack_url):
    with st.spinner("Slackスレッドを取得中..."):
        try:
            channel_id, thread_ts = parse_slack_thread_url(slack_url)
            slack = get_slack_client()
            thread = fetch_slack_thread(slack, channel_id, thread_ts, slack_url)
        except ValueError as e:
            st.error(f"URL解析エラー: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Slack取得エラー: {e}")
            st.stop()

    with st.spinner("Gemini で分析中..."):
        try:
            api_key = get_gemini_api_key()
            analysis, token_usage = analyze_thread(
                thread, api_key, memo=memo if memo else None
            )
        except Exception as e:
            st.error(f"分析エラー: {e}")
            st.stop()

    st.session_state["analysis"] = analysis
    st.session_state["thread"] = thread
    st.session_state["memo"] = memo if memo else None
    st.session_state["token_usage"] = token_usage
    st.session_state["session_total_tokens"] = (
        st.session_state.get("session_total_tokens", 0) + token_usage.total_tokens
    )

# --- 分析結果の表示 ---
if "analysis" in st.session_state:
    analysis = st.session_state["analysis"]
    thread = st.session_state["thread"]

    st.divider()
    st.subheader(analysis.theme)

    with st.expander("議論の構造", expanded=True):
        if analysis.structure.premises:
            st.markdown("**前提条件:**")
            for p in analysis.structure.premises:
                st.markdown(f"- {p}")
        if analysis.structure.key_issues:
            st.markdown("**主要論点:**")
            for k in analysis.structure.key_issues:
                st.markdown(f"- {k}")
        if analysis.structure.conclusions_or_current_state:
            st.markdown("**現状・結論:**")
            for c in analysis.structure.conclusions_or_current_state:
                st.markdown(f"- {c}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**次に決めること:**")
        st.info(analysis.next_decision_required)
    with col2:
        st.markdown("**次のアクション:**")
        st.info(analysis.suggested_next_action)

    st.markdown(f"**担当者:** {analysis.suggested_owner}")

    if analysis.new_concepts:
        st.markdown("**新しい概念:**")
        st.markdown(" ".join([f"`{c}`" for c in analysis.new_concepts]))

    if analysis.participants:
        with st.expander("参加者の立場", expanded=True):
            for p in analysis.participants:
                st.markdown(f"**{p.name}** — {p.stance}")
                if p.key_arguments:
                    for arg in p.key_arguments:
                        st.markdown(f"- {arg}")
                if p.concerns:
                    for c in p.concerns:
                        st.markdown(f"- :warning: {c}")

    if analysis.strategic_implications:
        with st.expander("戦略的示唆"):
            for s in analysis.strategic_implications:
                st.markdown(f"- {s}")

    if analysis.risk_signals:
        with st.expander("リスクシグナル"):
            for r in analysis.risk_signals:
                st.markdown(f"- {r}")

    st.divider()

    if st.button("Notionに保存", type="primary"):
        with st.spinner("Notionに保存中..."):
            try:
                notion_token = get_notion_token()
                db_id = get_notion_database_id()
                page_url = save_to_notion(
                    notion_token,
                    db_id,
                    analysis,
                    thread.url,
                    thread.channel_name,
                    st.session_state.get("memo"),
                )
                st.success("保存完了!")
                st.markdown(f"[Notionで開く]({page_url})")
                del st.session_state["analysis"]
                del st.session_state["thread"]
                del st.session_state["memo"]
            except Exception as e:
                st.error(f"Notion保存エラー: {e}")
