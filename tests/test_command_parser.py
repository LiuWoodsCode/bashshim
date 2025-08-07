import os
import pytest
from bashshim.command_parser import CommandParser


def test_variable_expansion_basic_and_braced(monkeypatch):
    variables = {"FOO": "bar", "NUM": "42"}
    parser = CommandParser(variables, env={})
    s = "Value:$FOO-${FOO} num=$NUM"
    assert parser.expand_vars(s) == "Value:bar-bar num=42"


def test_variable_expansion_fallback_env(monkeypatch):
    env = {"HOME": "/fake/home"}
    parser = CommandParser({}, env=env)
    assert parser.expand_vars("$HOME/path") == "/fake/home/path"


def test_expand_args_list():
    parser = CommandParser({"X": "1"}, env={})
    args = ["echo", "$X", "${X}"]
    assert parser.expand_args(args) == ["echo", "1", "1"]


def test_parse_redirection_truncate():
    parser = CommandParser({}, env={})
    tokens, out_file, append = parser.parse_redirection("echo hello > out.txt")
    assert tokens == ["echo", "hello"]
    assert out_file == "out.txt"
    assert append is False


def test_parse_redirection_append():
    parser = CommandParser({}, env={})
    tokens, out_file, append = parser.parse_redirection("echo hi >> log.txt")
    assert tokens == ["echo", "hi"]
    assert out_file == "log.txt"
    assert append is True


def test_parse_redirection_none():
    parser = CommandParser({}, env={})
    tokens, out_file, append = parser.parse_redirection("echo just words")
    assert tokens == ["echo", "just", "words"]
    assert out_file is None
    assert append is False


def test_split_pipes():
    parser = CommandParser({}, env={})
    parts = parser.split_pipes("echo hi | grep h | wc -l")
    assert parts == ["echo hi", "grep h", "wc -l"]


def test_split_shell_operators_and_detection():
    parser = CommandParser({}, env={})
    line = "echo one && echo two || echo three; echo four"
    parts = parser.split_shell_operators(line)
    assert parts == [
        "echo one", "&&", "echo two", "||", "echo three", ";", "echo four"
    ]
    assert parser.has_shell_operators(line) is True
    assert parser.has_shell_operators("echo only") is False
