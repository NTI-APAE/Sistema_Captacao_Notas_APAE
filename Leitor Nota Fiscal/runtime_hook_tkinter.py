import os
import sys
from pathlib import Path


base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
os.environ.setdefault("TCL_LIBRARY", str(base_dir / "tcl" / "tcl8.6"))
os.environ.setdefault("TK_LIBRARY", str(base_dir / "tcl" / "tk8.6"))
