import re
import os


def test_security_no_public_binding():
    """
    Regression test for the Bandit B104 vulnerability. 
    The test fails if host=0.0.0.0 is hardcoded in main.py.
    """
    main_py_path = os.path.join(
        os.path.dirname(__file__), "..", "main.py"
    )

    with open(main_py_path, "r", encoding="utf-8") as f:
        content = f.read()

    has_vulnerability = re.search(r'host\s*=\s*["\']0\.0\.0\.0["\']', content)

    assert not has_vulnerability, (
        "Vulnerability B104: Hard-coded reference to 0.0.0.0 found in main.py"
    )
