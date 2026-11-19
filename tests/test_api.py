import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from io import BytesIO

from nordavo_agent.api import AmbiguousRequestError, ApiError, HelpdeskClient
from nordavo_agent.config import Settings


def settings() -> Settings:
    return Settings("test-key", "applicant@example.com", None, "https://example.test/api")


class ApiTests(unittest.TestCase):
    def test_503_retries_after_backoff(self) -> None:
        delays: list[float] = []
        client = HelpdeskClient(settings(), sleep=delays.append)
        response = type("Response", (), {
            "__enter__": lambda self: self,
            "__exit__": lambda self, *args: None,
            "read": lambda self: b'{"ok": true}',
        })()
        error = HTTPError(
            "https://example.test/api/status",
            503,
            "temporarily unavailable",
            {},
            BytesIO(b'{"error":"service_unavailable"}'),
        )
        with patch("nordavo_agent.api.urllib.request.urlopen", side_effect=[error, response]) as open_url:
            with patch.object(client, "_pace"):
                self.assertEqual(client.status(), {"ok": True})
        self.assertEqual(open_url.call_count, 2)
        self.assertEqual(delays, [0.5])

    def test_429_waits_for_retry_after_and_retries(self) -> None:
        client = HelpdeskClient(settings(), sleep=lambda _: None)
        response = type("Response", (), {
            "__enter__": lambda self: self,
            "__exit__": lambda self, *args: None,
            "read": lambda self: b'{"ok": true}',
        })()
        error = HTTPError(
            "https://example.test/api/status",
            429,
            "rate limited",
            {"Retry-After": "2"},
            BytesIO(b'{"error":"rate_limited"}'),
        )
        with patch("nordavo_agent.api.urllib.request.urlopen", side_effect=[error, response]) as open_url:
            with patch.object(client, "_pace"):
                self.assertEqual(client.status(), {"ok": True})
        self.assertEqual(open_url.call_count, 2)

    def test_409_is_not_retried(self) -> None:
        client = HelpdeskClient(settings(), sleep=lambda _: None)
        error = HTTPError(
            "https://example.test/api/tickets/T1/reply",
            409,
            "already handled",
            {},
            BytesIO(b'{"error":"already_handled"}'),
        )
        with patch("nordavo_agent.api.urllib.request.urlopen", side_effect=error) as open_url:
            with patch.object(client, "_pace"):
                with self.assertRaises(ApiError) as raised:
                    client.act("T1", "reply", {"reason": "test"})
        self.assertEqual(raised.exception.status, 409)
        self.assertEqual(open_url.call_count, 1)

    def test_network_failure_during_post_is_ambiguous_and_not_retried(self) -> None:
        client = HelpdeskClient(settings(), sleep=lambda _: None)
        with patch("nordavo_agent.api.urllib.request.urlopen", side_effect=URLError("connection reset")) as open_url:
            with patch.object(client, "_pace"):
                with self.assertRaises(AmbiguousRequestError):
                    client.act("T1", "reply", {"reason": "test"})
        self.assertEqual(open_url.call_count, 1)

    def test_bad_cursor_response_is_rejected(self) -> None:
        client = HelpdeskClient(settings(), sleep=lambda _: None)
        with patch.object(client, "_request", return_value={"tickets": [], "next_cursor": "same"}):
            with self.assertRaises(ApiError):
                client.open_tickets()


if __name__ == "__main__":
    unittest.main()
