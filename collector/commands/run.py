from __future__ import annotations

import argparse
from pathlib import Path

from ..pipeline import run_pipeline
from . import Command, CommandResult, MaybeAwaitable


class RunCommand(Command):
    name = "run"
    help = "Generate a correlated news release"

    @classmethod
    def configure_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--feeds",
            type=Path,
            default=Path("data/feeds.yaml"),
            help="Path to the feed definition YAML file.",
        )
        parser.add_argument(
            "--feed-state",
            type=Path,
            default=Path("data/feed_state.json"),
            help="Path to the mutable feed state JSON file.",
        )
        parser.add_argument(
            "--output",
            type=Path,
            default=Path("data/releases"),
            help="Directory that will receive the generated release JSON.",
        )
        parser.add_argument(
            "--model",
            default="sshleifer/distilbart-cnn-12-6",
            help="Hugging Face model used for summarisation.",
        )

    @classmethod
    def handle(cls, args: argparse.Namespace) -> MaybeAwaitable:
        async def _runner() -> CommandResult:
            await run_pipeline(args.feeds, args.feed_state, args.output, args.model)
            return 0

        return _runner()


__all__ = ["RunCommand"]
