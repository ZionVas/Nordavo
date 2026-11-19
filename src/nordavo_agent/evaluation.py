from __future__ import annotations

from collections import Counter
from typing import Any

from .classifier import classify
from .models import Ticket

FIELDS = ("language", "category", "priority", "action")


def evaluate(examples: list[dict[str, Any]]) -> dict[str, Any]:
    if not examples:
        raise ValueError("The helpdesk returned no labelled examples")
    counts: Counter[str] = Counter()
    correct: Counter[str] = Counter()
    mismatches: list[dict[str, Any]] = []
    for example in examples:
        label = example.get("label")
        if not isinstance(label, dict):
            raise ValueError(f"Example {example.get('id', '<unknown>')} has no label object")
        ticket = Ticket(
            id=str(example.get("id") or "example"),
            subject=str(example.get("subject") or ""),
            body=str(example.get("body") or ""),
        )
        decision = classify(ticket)
        predicted = {
            "language": decision.language,
            "category": decision.category,
            "priority": decision.priority,
            "action": decision.action,
        }
        example_mismatches: dict[str, dict[str, str]] = {}
        for field in FIELDS:
            if field in label:
                counts[field] += 1
                is_correct = predicted[field] == label[field]
                correct[field] += is_correct
                if not is_correct:
                    example_mismatches[field] = {
                        "expected": str(label[field]),
                        "actual": predicted[field],
                    }
        if example_mismatches:
            mismatches.append({
                "id": str(example.get("id") or "example"),
                "fields": example_mismatches,
            })
    accuracies = {
        field: round(correct[field] / counts[field], 4) if counts[field] else None
        for field in FIELDS
    }
    available = [value for value in accuracies.values() if value is not None]
    return {
        "examples": len(examples),
        "fields_scored": dict(counts),
        "correct": dict(correct),
        "accuracy": accuracies,
        "macro_accuracy": round(sum(available) / len(available), 4) if available else None,
        "mismatches": mismatches,
        "cost_eur_per_100_tickets": 0.0,
    }
