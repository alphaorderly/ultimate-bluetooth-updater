"""Render the real window without enumeration or device access."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ultimate_updater.gui_selftest import main
raise SystemExit(main('build/ui-preview.png' if '--screenshot' in sys.argv else None))
