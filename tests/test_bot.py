import importlib

from discord import app_commands
from discord.ext import commands

from chongabot.bot import EXTENSIONS, unwrap_error
from chongabot.domain.errors import GameError, NotEnough


def test_every_extension_imports_and_has_setup() -> None:
    for name in EXTENSIONS:
        module = importlib.import_module(name)
        assert callable(getattr(module, "setup", None)), f"{name} has no setup()"


def test_unwrap_reaches_the_original_error() -> None:
    original = NotEnough("Not enough metal")
    wrapped = commands.CommandInvokeError(original)
    assert unwrap_error(wrapped) is original


def test_unwrap_through_hybrid_and_app_command_layers() -> None:
    original = GameError("nope")
    # A hybrid command invoked as a slash command wraps twice.
    inner = app_commands.CommandInvokeError.__new__(app_commands.CommandInvokeError)
    inner.original = original
    outer = commands.HybridCommandError(inner)
    assert unwrap_error(outer) is original


def test_unwrap_leaves_plain_errors_alone() -> None:
    error = ValueError("x")
    assert unwrap_error(error) is error
