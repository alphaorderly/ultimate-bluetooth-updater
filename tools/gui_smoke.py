"""Render the real window without enumeration or device access."""
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from ultimate_updater.gui import Window, STYLE

app=QApplication([]);app.setStyleSheet(STYLE)
with tempfile.TemporaryDirectory() as temp:
    window=Window(data_dir=temp,demo=True);window.show();app.processEvents()
    assert not window.update_button.isEnabled()
    assert not window.restore_button.isEnabled()
    assert not window.cancel_button.isEnabled()
    window.confirm.setChecked(True);app.processEvents()
    assert not window.update_button.isEnabled()
    if '--screenshot' in sys.argv:
        output=Path('build/ui-preview.png');output.parent.mkdir(exist_ok=True)
        assert window.grab().save(str(output))
    window.close()
print('GUI smoke test passed. No device accessed.')
