from datetime import datetime

from pydantic import BaseModel


class SlackMessage(BaseModel):
    user: str
    text: str
    timestamp: datetime


class SlackThread(BaseModel):
    channel_name: str
    channel_id: str
    thread_ts: str
    url: str
    messages: list[SlackMessage]
    last_reply_at: datetime


class DiscussionStructure(BaseModel):
    premises: list[str]
    key_issues: list[str]
    conclusions_or_current_state: list[str]


class ParticipantStance(BaseModel):
    name: str
    stance: str
    key_arguments: list[str]
    concerns: list[str]


class AnalysisResult(BaseModel):
    theme: str
    structure: DiscussionStructure
    next_decision_required: str
    suggested_next_action: str
    suggested_owner: str
    new_concepts: list[str]
    strategic_implications: list[str]
    risk_signals: list[str]
    participants: list[ParticipantStance] = []
