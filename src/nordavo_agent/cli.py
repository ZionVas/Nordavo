from __future__ import annotations

import argparse
import json
import sys

from .api import HelpdeskClient
from .classifier import reply_audit
from .config import Settings
from .evaluation import evaluate
from .runner import run_agent


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nordavo-agent",
        description="Classify, reply to, or hand off Roosterly helpdesk tickets.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "eval", "review-replies", "run"):
        commands.add_parser(name, help={
            "status": "show helpdesk status",
            "eval": "score decisions against labelled examples",
            "review-replies": "show localized FAQ replies beside their English references",
            "run": "process all currently open tickets once",
        }[name])
    reset = commands.add_parser("reset", help="reopen practice tickets")
    reset.add_argument(
        "--confirm",
        action="store_true",
        help="required confirmation because this reopens previously handled tickets",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "reset" and not args.confirm:
        print("Refusing to reset tickets without --confirm.", file=sys.stderr)
        return 2
    try:
        if args.command == "review-replies":
            result = {
                "templates": reply_audit(),
                "note": "English references support content review; they do not replace a Dutch-language review.",
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        settings = Settings.from_environment()
        client = HelpdeskClient(settings)
        if args.command == "status":
            result = client.status()
        elif args.command == "eval":
            result = evaluate(client.examples())
        elif args.command == "run":
            result = run_agent(client)
        else:
            result = client.reset()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
