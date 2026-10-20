import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if api_dir.name == "api":
    sys.path.insert(0, str(api_dir))
    sys.path.insert(0, str(api_dir.parent.parent))
else:
    sys.path.insert(0, str(api_dir / "src" / "api"))
    sys.path.insert(0, str(api_dir))
