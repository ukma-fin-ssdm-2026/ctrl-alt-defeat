import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_requirements_lock.py"
spec = importlib.util.spec_from_file_location("check_requirements_lock", SCRIPT)
check_lock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_lock)


def test_read_pins_handles_hashes_comments_and_name_normalization(tmp_path):
    lock = tmp_path / "lock.txt"
    lock.write_text(
        "pydantic-core==2.50.2 \\\n"
        "    --hash=sha256:abc\n"
        "    # via pydantic\n"
        "PyYAML==6.0.3 ; python_version >= '3.8'\n",
        encoding="utf-8",
    )
    assert check_lock.read_pins(lock) == {"pydantic-core": "2.50.2", "pyyaml": "6.0.3"}


def test_find_mismatches_reports_missing_and_different_versions():
    problems = check_lock.find_mismatches(
        {"fastapi": "1.0", "uvicorn": "2.0", "black": "3.0"},
        {"fastapi": "1.0", "uvicorn": "2.1", "click": "8.0"},
    )
    assert problems == [
        "black==3.0 is missing from requirements-lock.txt",
        "uvicorn: requirements.txt has 2.0, requirements-lock.txt has 2.1",
    ]


def test_repository_lock_file_is_in_sync():
    assert check_lock.main() == 0
