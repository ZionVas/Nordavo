import unittest

from nordavo_agent.evaluation import evaluate


class EvaluationTests(unittest.TestCase):
    def test_eval_scores_only_fields_present_in_labels(self) -> None:
        result = evaluate([
            {
                "id": "E1",
                "subject": "Nieuwe medewerker",
                "body": "Hoe voeg ik een nieuwe medewerker toe?",
                "label": {
                    "language": "nl",
                    "category": "question",
                    "priority": "P4",
                    "action": "reply",
                },
            }
        ])
        self.assertEqual(result["examples"], 1)
        self.assertEqual(result["macro_accuracy"], 1.0)
        self.assertEqual(result["cost_eur_per_100_tickets"], 0.0)
        self.assertEqual(result["mismatches"], [])

    def test_eval_reports_example_ids_and_field_mismatches(self) -> None:
        result = evaluate([
            {
                "id": "E-wrong",
                "subject": "App crashes",
                "body": "The app crashes immediately on my iPhone 8 (iOS 15). Other staff are fine.",
                "label": {
                    "language": "en",
                    "category": "other",
                    "priority": "P4",
                    "action": "handoff",
                },
            }
        ])
        self.assertEqual(result["mismatches"], [
            {
                "id": "E-wrong",
                "fields": {
                    "category": {"expected": "other", "actual": "bug"},
                    "priority": {"expected": "P4", "actual": "P3"},
                    "action": {"expected": "handoff", "actual": "reply"},
                },
            }
        ])

    def test_eval_rejects_missing_labels(self) -> None:
        with self.assertRaises(ValueError):
            evaluate([{"id": "E1", "subject": "Question", "body": "Hi"}])


if __name__ == "__main__":
    unittest.main()
