"""Sample commands used for discovery tests."""
from __future__ import annotations

import argparse

from collector.commands import Command, MaybeAwaitable


class AlphaCommand(Command):
    name = "alpha"
    help = "Alpha test command"

    @classmethod
    def configure_parser(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--alpha", action="store_true")

    @classmethod
    def handle(cls, args: argparse.Namespace) -> MaybeAwaitable:
        return 0


class BetaCommand(Command):
    name = "beta"
    help = "Beta test command"

    @classmethod
    def handle(cls, args: argparse.Namespace) -> MaybeAwaitable:
        return 0


class _HiddenCommand(Command):
    name = ""


__all__ = ["AlphaCommand", "BetaCommand"]
