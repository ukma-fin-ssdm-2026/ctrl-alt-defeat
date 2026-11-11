"""
Reliability, finding 15 (boundary values): numeric settings from the environment.

Chosen reaction: safe failure — an unset, empty, non-numeric or out-of-range value gives the default
and a warning naming the variable; values on the boundaries are accepted.
"""

import logging

import pytest

from src.api.settings import env_int

NAME = "TEST_RELIABILITY_MINUTES"


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, 1440),  # not set
        ("", 1440),  # empty value in the hosting dashboard
        ("   ", 1440),
        ("60", 60),
        ("  60 ", 60),  # spaces around the number
        ("1", 1),  # lower boundary
        ("43200", 43200),  # upper boundary (30 days)
        ("0", 1440),  # just below the lower boundary
        ("-5", 1440),
        ("43201", 1440),  # just above the upper boundary
        ("24h", 1440),  # a typo
        ("1.5", 1440),  # not a whole number
        ("99999999999999999999999", 1440),  # huge number
    ],
)
def test_env_int_boundaries(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv(NAME, raising=False)
    else:
        monkeypatch.setenv(NAME, raw)

    assert env_int(NAME, 1440, minimum=1, maximum=43200) == expected


def test_rejected_value_is_logged_with_the_variable_name(monkeypatch, caplog):
    monkeypatch.setenv(NAME, "24h")

    with caplog.at_level(logging.WARNING, logger="src.api.settings"):
        assert env_int(NAME, 1440, minimum=1) == 1440

    assert NAME in caplog.text and "'24h'" in caplog.text


def test_valid_value_is_silent(monkeypatch, caplog):
    monkeypatch.setenv(NAME, "90")

    with caplog.at_level(logging.WARNING, logger="src.api.settings"):
        assert env_int(NAME, 1440, minimum=1) == 90

    assert caplog.text == ""
