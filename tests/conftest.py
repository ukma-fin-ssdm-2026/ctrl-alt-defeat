import sys
from pathlib import Path

# Отримуємо абсолютний шлях до src/api та додаємо його в sys.path
api_dir = Path(__file__).resolve().parent.parent
if api_dir.name == "api":  # якщо тести в src/api/tests
    sys.path.insert(0, str(api_dir))
    sys.path.insert(0, str(api_dir.parent.parent))
else:  # якщо тести в /tests
    sys.path.insert(0, str(api_dir / "src" / "api"))
    sys.path.insert(0, str(api_dir))
