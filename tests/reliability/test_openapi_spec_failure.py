"""
Reliability, finding 4 (external failure, file I/O): the OpenAPI file cannot be written.

On a read-only file system (a container, a hosting platform) saving docs/api/openapi-generated.yaml fails with an
OSError. Chosen reaction: safe failure — the API starts anyway, and the problem is written to the log.
"""

import logging
from unittest.mock import patch

import pytest

from src.api.main import app, save_openapi_spec


@pytest.mark.parametrize(
    "error",
    [PermissionError("[Errno 13] Permission denied"), OSError("[Errno 30] Read-only file system")],
)
def test_unwritable_openapi_file_does_not_stop_the_startup(error, caplog):
    with patch("builtins.open", side_effect=error), caplog.at_level(logging.WARNING, logger="src.api.main"):
        # No exception: the startup continues
        save_openapi_spec(app)

    assert "Could not save auto-generated OpenAPI spec" in caplog.text
    assert str(error) in caplog.text


def test_unwritable_docs_directory_does_not_stop_the_startup(caplog):
    with patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")):
        with caplog.at_level(logging.WARNING, logger="src.api.main"):
            save_openapi_spec(app)

    assert "Continuing startup" in caplog.text
