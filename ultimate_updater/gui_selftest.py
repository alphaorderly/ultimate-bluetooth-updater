"""Check bundled Qt and HID imports without enumerating or opening USB devices."""
from pathlib import Path
import tempfile


def main(screenshot=None):
    import hid
    from PySide6.QtWidgets import QApplication
    from .gui import Window, STYLE

    assert callable(hid.enumerate) and callable(hid.device)
    app = QApplication([])
    app.setStyleSheet(STYLE)
    with tempfile.TemporaryDirectory() as temp:
        window = Window(data_dir=temp, demo=True)
        window.show()
        app.processEvents()
        assert not window.update_button.isEnabled()
        assert not window.restore_button.isEnabled()
        assert not window.cancel_button.isEnabled()
        window.confirm.setChecked(True)
        app.processEvents()
        assert not window.update_button.isEnabled()
        if screenshot:
            output = Path(screenshot)
            output.parent.mkdir(parents=True, exist_ok=True)
            assert window.grab().save(str(output))
        window.close()
    print('GUI and HID import smoke test passed. No device accessed.')
    return 0
