import json
import tempfile
import unittest
from pathlib import Path

from nordavo_agent.api import ApiError, AmbiguousRequestError
from nordavo_agent.runner import run_agent


class FakeClient:
    def __init__(self, tickets: list[dict[str, str]], outcomes: list[Exception | None] | None = None):
        self.tickets = tickets
        self.outcomes = list(outcomes or [])
        self.actions: list[tuple[str, str, dict[str, object]]] = []

    def open_tickets(self) -> list[dict[str, str]]:
        return self.tickets

    def act(self, ticket_id: str, action: str, payload: dict[str, object]) -> dict[str, object]:
        self.actions.append((ticket_id, action, payload))
        outcome = self.outcomes.pop(0) if self.outcomes else None
        if outcome is not None:
            raise outcome
        return {"ok": True}


class RunnerTests(unittest.TestCase):
    def test_logs_each_ticket_without_message_or_payment_details(self) -> None:
        client = FakeClient([
            {
                "id": "T1",
                "subject": "Invoice question",
                "body": "How do I download an invoice? PAYMENT-DETAIL-TEST",
            },
            {"id": "T2", "subject": "", "body": ""},
        ], [ApiError(409, "already_handled", "already handled"), None])

        with tempfile.TemporaryDirectory() as directory:
            summary = run_agent(client, Path(directory))
            log_paths = list(Path(directory).glob("run-*.jsonl"))
            self.assertEqual(len(log_paths), 1)
            log_path = log_paths[0]
            lines = log_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(summary["already_handled"], 1)
        self.assertEqual(summary["close"], 1)
        self.assertEqual(len(lines), 2)
        self.assertNotIn("PAYMENT-DETAIL-TEST", "\n".join(lines))
        self.assertNotIn("How do I download", "\n".join(lines))
        self.assertTrue(all(isinstance(json.loads(line), dict) for line in lines))

    def test_ambiguous_post_is_logged_and_propagated(self) -> None:
        client = FakeClient(
            [{"id": "T1", "subject": "", "body": ""}],
            [AmbiguousRequestError("unknown result")],
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(AmbiguousRequestError):
                run_agent(client, Path(directory))
            log_path = next(Path(directory).glob("run-*.jsonl"))
            record = json.loads(log_path.read_text(encoding="utf-8"))
        self.assertEqual(record["result"], "uncertain")


if __name__ == "__main__":
    unittest.main()
