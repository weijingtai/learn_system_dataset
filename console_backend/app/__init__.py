"""Console Backend App Package."""

import sys
from pathlib import Path

_GENERATED_DIR = str(Path(__file__).resolve().parent.parent / "generated")
if _GENERATED_DIR not in sys.path:
    sys.path.insert(0, _GENERATED_DIR)
