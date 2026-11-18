import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if api_dir.name == "api":
    sys.path.insert(0, str(api_dir))
    sys.path.insert(0, str(api_dir.parent.parent))
else:
    sys.path.insert(0, str(api_dir / "src" / "api"))
    sys.path.insert(0, str(api_dir))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def reset_login_limiter():
    """Failed logins, registrations and resent emails of one test must not block the next one
    (every test uses the same test client address)."""
    from src.api.services.rate_limit import ALL_LIMITERS

    for limiter in ALL_LIMITERS:
        limiter.clear()
    yield
    for limiter in ALL_LIMITERS:
        limiter.clear()
