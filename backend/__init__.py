"""
Backend package initialization.
Ensures src/ is on sys.path so content_engine is available across all backend modules.
"""
import sys
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_SRC_DIR = _BASE_DIR / "src"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))
