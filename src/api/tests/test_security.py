import re
import os


def test_security_no_public_binding():
    """
    Регресійний тест для вразливості Bandit B104.
    Тест падає, якщо у main.py захардкоджено host="0.0.0.0".
    """
    main_py_path = os.path.join(
        os.path.dirname(__file__), "..", "main.py"
    )

    with open(main_py_path, "r", encoding="utf-8") as f:
        content = f.read()

    has_vulnerability = re.search(r'host\s*=\s*["\']0\.0\.0\.0["\']', content)

    assert not has_vulnerability, (
        "Вразливість B104: Знайдено жорстку прив'язку до 0.0.0.0 у main.py"
    )