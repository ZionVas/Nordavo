from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Action = Literal["reply", "handoff", "close"]
Category = Literal["bug", "billing", "feature_request", "question", "other"]
Language = Literal["nl", "en", "de"]
Priority = Literal["P1", "P2", "P3", "P4"]


@dataclass(frozen=True)
class Ticket:
    id: str
    subject: str
    body: str
    customer_plan: str = ""
    channel: str = ""

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> Ticket:
        ticket_id = payload.get("id")
        if not isinstance(ticket_id, str) or not ticket_id:
            raise ValueError("Ticket has no valid id")
        return cls(
            id=ticket_id,
            subject=str(payload.get("subject") or ""),
            body=str(payload.get("body") or ""),
            customer_plan=str(payload.get("customer_plan") or ""),
            channel=str(payload.get("channel") or ""),
        )


@dataclass(frozen=True)
class Decision:
    language: Language
    category: Category
    priority: Priority
    action: Action
    reason: str
    confidence: float
    draft_reply: str | None = None
    handoff_note: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "language": self.language,
            "category": self.category,
            "priority": self.priority,
            "reason": self.reason,
            "confidence": self.confidence,
        }
        if self.action == "reply":
            if not self.draft_reply:
                raise ValueError("Reply decision requires draft_reply")
            payload["draft_reply"] = self.draft_reply
        elif self.action == "handoff":
            if not self.handoff_note:
                raise ValueError("Handoff decision requires handoff_note")
            payload["handoff_note"] = self.handoff_note
        return payload
