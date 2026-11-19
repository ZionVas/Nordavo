from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from .config import Settings


class ApiError(RuntimeError):
    def __init__(self, status: int, code: str, message: str, retry_after: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.retry_after = retry_after


class AmbiguousRequestError(RuntimeError):
    pass


class HelpdeskClient:
    def __init__(
        self,
        settings: Settings,
        *,
        timeout: float = 20.0,
        min_interval: float = 0.21,
        sleep=time.sleep,
    ):
        self.settings = settings
        self.timeout = timeout
        self.min_interval = min_interval
        self.sleep = sleep
        self._last_request_at = 0.0

    def _pace(self) -> None:
        delay = self.min_interval - (time.monotonic() - self._last_request_at)
        if delay > 0:
            self.sleep(delay)
        self._last_request_at = time.monotonic()

    @staticmethod
    def _retry_delay(value: str | None, fallback: float) -> float:
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                try:
                    when = parsedate_to_datetime(value)
                    if when.tzinfo is None:
                        when = when.replace(tzinfo=timezone.utc)
                    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError, OverflowError):
                    pass
        return fallback

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        retry_transient: bool = True,
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "X-Candidate-Email": self.settings.candidate_email,
            "Accept": "application/json",
            "User-Agent": "nordavo-support-agent/0.1.0",
        }
        if self.settings.candidate_name:
            headers["X-Candidate-Name"] = self.settings.candidate_name
        if body is not None:
            headers["Content-Type"] = "application/json"

        for attempt in range(5):
            self._pace()
            request = urllib.request.Request(
                f"{self.settings.api_url}{path}",
                data=body,
                headers=headers,
                method=method,
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                try:
                    value = json.loads(raw)
                except (json.JSONDecodeError, UnicodeDecodeError) as error:
                    raise ApiError(502, "invalid_response", "Helpdesk returned invalid JSON") from error
                if not isinstance(value, dict):
                    raise ApiError(502, "invalid_response", "Helpdesk response must be a JSON object")
                return value
            except urllib.error.HTTPError as error:
                response_body = error.read()
                try:
                    details = json.loads(response_body)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    details = {}
                if not isinstance(details, dict):
                    details = {}
                code = str(details.get("error") or details.get("code") or f"http_{error.code}")
                message = str(details.get("message") or details.get("error_description") or code)
                retry_after = error.headers.get("Retry-After")
                should_retry = error.code in (429, 503) and retry_transient and attempt < 4
                if should_retry:
                    delay = self._retry_delay(retry_after, 0.5 * (2**attempt))
                    self.sleep(delay)
                    continue
                raise ApiError(error.code, code, message, retry_after) from error
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if method != "GET":
                    raise AmbiguousRequestError(
                        "The action request outcome is unknown; stop and rerun to fetch only open tickets"
                    ) from error
                if not retry_transient or attempt == 4:
                    raise RuntimeError(f"Helpdesk request failed: {error}") from error
                self.sleep(0.5 * (2**attempt))
        raise RuntimeError("Helpdesk request exhausted its retry attempts")

    def status(self) -> dict[str, Any]:
        return self._request("GET", "/status")

    def examples(self) -> list[dict[str, Any]]:
        result = self._request("GET", "/examples")
        examples = result.get("examples")
        if not isinstance(examples, list):
            raise ApiError(502, "invalid_response", "Examples response has no examples list")
        if not all(isinstance(item, dict) for item in examples):
            raise ApiError(502, "invalid_response", "Examples response contains an invalid entry")
        return examples

    def open_tickets(self) -> list[dict[str, Any]]:
        tickets: list[dict[str, Any]] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            query: dict[str, str] = {"limit": "10", "status": "open"}
            if cursor:
                query["cursor"] = cursor
            page = self._request("GET", f"/tickets?{urllib.parse.urlencode(query)}")
            batch = page.get("tickets")
            if not isinstance(batch, list) or not all(isinstance(item, dict) for item in batch):
                raise ApiError(502, "invalid_response", "Tickets response has an invalid tickets list")
            tickets.extend(batch)
            next_cursor = page.get("next_cursor")
            if next_cursor is None:
                break
            if not isinstance(next_cursor, str) or next_cursor in seen_cursors:
                raise ApiError(502, "invalid_response", "Tickets response has an invalid or repeated cursor")
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        return tickets

    def act(self, ticket_id: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if action not in {"reply", "handoff", "close"}:
            raise ValueError(f"Unsupported action: {action}")
        encoded_id = urllib.parse.quote(ticket_id, safe="")
        return self._request(
            "POST",
            f"/tickets/{encoded_id}/{action}",
            payload,
        )

    def reset(self) -> dict[str, Any]:
        return self._request("POST", "/practice/reset")
