import argparse
import importlib

from collector.commands import Command, discover_commands


def test_discover_commands_finds_all_subclasses():
    module = importlib.import_module("tests.sample_commands")
    commands = discover_commands(module)
    names = [command.name for command in commands]
    assert names == sorted(names)
    assert {"alpha", "beta"}.issubset(set(names))
    assert all(issubclass(command, Command) for command in commands)


def test_command_attach_registers_parser():
    module = importlib.import_module("tests.sample_commands")
    commands = discover_commands(module)
    parser = argparse.ArgumentParser(prog="test")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in commands:
        command.attach(subparsers)

    help_text = parser.format_help()
    assert "alpha" in help_text
    assert "beta" in help_text
