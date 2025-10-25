"""Command-line entry point for the collector package."""
from __future__ import annotations

import argparse
import asyncio
import importlib
import logging
import pkgutil
import sys
from typing import Coroutine, List, Optional, Sequence, Type, cast

from .commands import Command, CommandResult, MaybeAwaitable, discover_commands


def _load_command_modules() -> List[Type[Command]]:
    """Discover every command subclass exposed by ``collector.commands``."""

    package = importlib.import_module("collector.commands")
    command_types: List[Type[Command]] = []
    # Include commands defined directly on the package module.
    command_types.extend(discover_commands(package))
    for module_info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package.__name__}.{module_info.name}")
        command_types.extend(discover_commands(module))
    # Ensure deterministic ordering and avoid duplicate registrations.
    unique: dict[str, Type[Command]] = {}
    for command_type in command_types:
        unique[command_type.name] = command_type
    return sorted(unique.values(), key=lambda cls: cls.name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collector",
        description="Utilities for running the data correlation pipeline",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level applied to all commands.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Shortcut for setting --log-level=DEBUG.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command_cls in _load_command_modules():
        command_cls.attach(subparsers)
    return parser


def _configure_logging(args: argparse.Namespace) -> None:
    level = logging.DEBUG if args.debug else getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level)


def _execute_handler(result: MaybeAwaitable) -> int:
    if asyncio.iscoroutine(result):
        awaited = cast(Coroutine[object, object, CommandResult], result)
        outcome: CommandResult = asyncio.run(awaited)
    else:
        outcome = cast(CommandResult, result)
    return int(outcome or 0)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args)

    command_cls: Optional[Type[Command]] = getattr(args, "_command_cls", None)
    if command_cls is None:
        parser.print_help()
        return 1

    result = command_cls.handle(args)
    return _execute_handler(result)


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    sys.exit(main())
