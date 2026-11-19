# Roosterly support ticket agent

## How to run

Requires Python 3.11+. From a fresh clone:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# Set the API key and application email in .env; never commit that file.
nordavo-agent status
nordavo-agent review-replies
nordavo-agent eval
python -m unittest discover -s tests
```

For the final scored run only, run `nordavo-agent reset --confirm`, then `nordavo-agent run` once. Each run gets a separate, privacy-minimized JSONL file under `logs/`.

## Decisions

- I chose a dependency-free, rule-based agent rather than a paid model: it replies only to FAQ intents, sends unsupported or sensitive cases to a person, and never treats ticket text as instructions.
- Dutch, English, and German templates sit beside English references in [classifier.py](./src/nordavo_agent/classifier.py). `nordavo-agent review-replies` makes all 12 FAQ pairs easy to inspect. This helps check factual meaning but does not replace a Dutch speaker checking natural wording.
- AI assistance (Copilot) helped build and debug the project. I reviewed the code and tests; the running agent itself makes no model calls. Unclear requests are handed off rather than answered with unsupported product claims.

## Reliability

The client follows ticket cursors, stays below five requests per second, honors `Retry-After` for 429, and retries 503 with bounded backoff. It never retries 409. If a POST has an ambiguous network failure, it stops; a rerun fetches open tickets, so already-handled tickets are not intentionally answered twice. Logs omit ticket bodies, replies, and payment details; `.env` is ignored by Git.

## Eval and fix

Against the same 10 labeled examples from `GET /examples`, baseline accuracy was language 10/10, category 7/10, priority 7/10, action 6/10 (macro 0.75). The misses exposed broad priority rules, weak bug/feature/spam cues, and Dutch questions misdetected as uncertain. I added general intent and language cues, limited P2 to blocking or explicit money/contract cases, closed the identified crypto-spam pattern, and calculate plan totals from the FAQ rate. After the changes: **10/10 on each field; macro 1.00; zero mismatches**. Details are in [scorecard.json](./eval/scorecard.json); `nordavo-agent eval` shows per-example mismatches. Cost: 100 tickets × 0 model calls × €0 per call = **€0 inference cost**, excluding helpdesk, hosting, and network costs. Ten examples are a small benchmark, not a guarantee on unseen tickets.

## What I would improve

Before submission, ask a Dutch speaker to review the 12 localized replies, then test on held-out tickets without tuning to their labels. I would also add reviewed examples for ambiguous urgency and non-spam messages that mention investments.
