"""Command plugin infrastructure for the collector CLI."""
from __future__ import annotations

import argparse
import inspect
from typing import Awaitable, List, Optional, Sequence, Type, Union

CommandResult = Optional[int]
MaybeAwaitable = Union[CommandResult, Awaitable[CommandResult]]


class Command:
    """Base class for CLI subcommands."""

    name: str = ""
    help: str = ""
    aliases: Sequence[str] = ()

    @classmethod
    def configure_parser(cls, parser: argparse.ArgumentParser) -> None:
        """Hook for subclasses to define command-specific arguments."""

    @classmethod
    def handle(cls, args: argparse.Namespace) -> MaybeAwaitable:
        """Execute the command using parsed ``argparse`` arguments."""
        raise NotImplementedError("Command subclasses must implement handle()")

    @classmethod
    def attach(cls, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        """Register the command with an ``argparse`` sub-parser collection."""

        if not cls.name:
            raise ValueError("Command subclasses must define a non-empty 'name'")
        parser = subparsers.add_parser(
            cls.name,
            help=cls.help or None,
            description=cls.help or None,
            aliases=list(cls.aliases),
        )
        cls.configure_parser(parser)
        parser.set_defaults(_command_cls=cls)


def discover_commands(module: object) -> List[Type[Command]]:
    """Return every ``Command`` subclass defined on ``module``."""

    commands: List[Type[Command]] = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if not issubclass(obj, Command) or obj is Command:
            continue
        if not getattr(obj, "name", ""):
            continue
        commands.append(obj)
    commands.sort(key=lambda cls: cls.name)
    return commands


__all__ = ["Command", "CommandResult", "MaybeAwaitable", "discover_commands"]
