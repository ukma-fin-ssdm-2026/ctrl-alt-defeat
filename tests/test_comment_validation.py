"""Validation and policy tests for review comments (FR-011, SEC-002)."""

import uuid

import pytest
from pydantic import ValidationError

from src.api.schemas.comment import EMPTY_COMMENT_MESSAGE, MAX_COMMENT_LENGTH, CommentCreate
from src.api.utils import check_comment_policy_violations

USER = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


def make(**overrides):
    data = {"user_id": USER, "author_name": "admin", "text": "Great point about the ending"}
    data.update(overrides)
    return CommentCreate(**data)


def test_comment_text_and_author_are_trimmed():
    # Trace: T-029
    comment = make(text="  Nice review  ", author_name="  admin ")
    assert comment.text == "Nice review"
    assert comment.author_name == "admin"


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_empty_comment_is_rejected_with_clear_message(text):
    # Trace: T-030
    with pytest.raises(ValidationError) as exc:
        make(text=text)
    assert EMPTY_COMMENT_MESSAGE in str(exc.value)


def test_comment_length_limit():
    # Trace: T-030
    assert make(text="a" * MAX_COMMENT_LENGTH).text
    with pytest.raises(ValidationError):
        make(text="a" * (MAX_COMMENT_LENGTH + 1))


def test_reply_keeps_parent_id():
    # Trace: T-029
    parent = uuid.uuid4()
    assert make(parent_id=str(parent)).parent_id == parent


@pytest.mark.parametrize(
    "text",
    [
        "<script>alert('xss')</script>",
        "nice <img src=x onerror=alert(1)>",
        "click <a href='#'>here</a>",
        "</b> broken tag",
        "javascript:alert(document.cookie)",
        "JavaScript : void(0)",
        "unclosed <img src=x onerror=alert(1)",
        "<!-- hidden -->",
    ],
)
def test_html_and_scripts_are_policy_violations(text):
    # Trace: T-032
    assert "html_markup" in check_comment_policy_violations(text)


@pytest.mark.parametrize("text", ["2 < 3 and 5 > 4", "I <3 this movie", "Rating: 10/10 <-- best"])
def test_plain_text_with_angle_brackets_is_allowed(text):
    # Trace: T-032
    assert check_comment_policy_violations(text) == []


def test_html_pattern_runs_in_linear_time_on_hostile_input():
    # Trace: T-032
    """ReDoS guard: a long run of whitespace after '<' must be checked instantly."""
    import time

    hostile = "<" + " " * 50_000 + "x"
    started = time.perf_counter()
    check_comment_policy_violations(hostile)
    assert time.perf_counter() - started < 0.5


def test_comment_policy_includes_review_rules():
    # Trace: T-032
    assert "spam_links" in check_comment_policy_violations("see https://spam.example")
    assert "profanity" in check_comment_policy_violations("you are an idiot")
