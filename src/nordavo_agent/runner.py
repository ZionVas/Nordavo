from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from .api import AmbiguousRequestError, ApiError, HelpdeskClient
from .classifier import classify
from .models import Ticket


def build_logger(log_dir: Path = Path("logs")) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("nordavo_agent.tickets")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    log_path = log_dir / f"run-{run_id}-{uuid4().hex[:8]}.jsonl"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def _log_ticket(logger: logging.Logger, record: dict[str, Any]) -> None:
    logger.info(json.dumps(record, ensure_ascii=False, separators=(",", ":")))


def run_agent(client: HelpdeskClient, log_dir: Path = Path("logs")) -> dict[str, int]:
    logger = build_logger(log_dir)
    raw_tickets = client.open_tickets()
    tickets = [Ticket.from_api(item) for item in raw_tickets]
    ids = [ticket.id for ticket in tickets]
    if len(ids) != len(set(ids)):
        raise ApiError(502, "duplicate_ticket", "Helpdesk returned a ticket more than once")

    summary = {"total": len(tickets), "reply": 0, "handoff": 0, "close": 0, "already_handled": 0}
    for ticket in tickets:
        decision = classify(ticket)
        record: dict[str, Any] = {
            "ticket_id": ticket.id,
            "language": decision.language,
            "category": decision.category,
            "priority": decision.priority,
            "action": decision.action,
            "confidence": decision.confidence,
        }
        try:
            client.act(ticket.id, decision.action, decision.to_payload())
        except ApiError as error:
            if error.status == 409:
                summary["already_handled"] += 1
                record["result"] = "already_handled"
                _log_ticket(logger, record)
                continue
            record["result"] = "failed"
            record["error_code"] = error.code
            _log_ticket(logger, record)
            raise
        except AmbiguousRequestError:
            record["result"] = "uncertain"
            _log_ticket(logger, record)
            raise
        else:
            summary[decision.action] += 1
            record["result"] = "submitted"
            _log_ticket(logger, record)
    return summary
