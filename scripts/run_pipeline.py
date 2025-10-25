"""Compatibility shim that forwards to the package CLI."""
from __future__ import annotations

import sys

from collector.__main__ import main


_TOP_LEVEL_FLAGS = {"--debug"}
_TOP_LEVEL_WITH_VALUES = {"--log-level"}


def _build_argv() -> list[str]:
    top_level: list[str] = []
    command_args: list[str] = []
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in _TOP_LEVEL_FLAGS:
            top_level.append(arg)
        elif arg in _TOP_LEVEL_WITH_VALUES:
            top_level.append(arg)
            if i + 1 < len(argv):
                top_level.append(argv[i + 1])
                i += 1
        else:
            command_args.append(arg)
        i += 1
    return [*top_level, "run", *command_args]


def cli() -> int:
    return main(_build_argv())


if __name__ == "__main__":  # pragma: no cover
    sys.exit(cli())
