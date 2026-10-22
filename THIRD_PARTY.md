# Third-party software and firmware

The MIT license at the repository root covers the original updater and authored
firmware modifications. It does not relicense 8BitDo firmware or third-party dependencies.

- **8CryptDo**, AeroModes, MIT: https://github.com/aeromodes/8cryptdo
  - Reference commit: `aaffcebafa481631de9c1d722a5693d02234e43a`.
  - `resources/seeds.json` contains its 256-entry seed table. The YiChip transform
    in `firmware.py` implements the documented schedule. License retained in
    `licenses/8CryptDo-MIT.txt`.
- **Qt / PySide6 / Shiboken**, Qt Project: https://www.qt.io/qt-for-python
  - Distributed shared libraries retain their upstream licenses, including LGPLv3.
  - Source and license information: https://code.qt.io/cgit/pyside/pyside-setup.git/
    and https://code.qt.io/cgit/qt/ . Use the corresponding 6.8.3 release.
  - Application bundles use the one-folder layout with replaceable shared libraries.
    Users may modify/relink those libraries under their applicable licenses.
- **cython-hidapi / HIDAPI**: https://github.com/trezor/cython-hidapi
  and https://github.com/libusb/hidapi . Retains its upstream BSD/public-domain
  license options and bundled notices.
- **PyInstaller**: https://github.com/pyinstaller/pyinstaller . GPL with the
  upstream exception for distributing bundled applications.

Dependency license files are collected from installed distributions into the
application bundle's `dependency-licenses` directory during the build.

No full 8BitDo firmware, radio blob, controller dump, pairing key, or private
device log is distributed in this repository or release archives. The app fetches
the exact official inputs and checks pinned SHA-256 hashes before generating
the modified image locally. Download availability does not establish permission
to redistribute the original firmware. This project is not affiliated with 8BitDo
or Nintendo.

Protocol research references:
- https://github.com/ndeadly/switch2_controller_research
- https://github.com/tv/switch2-wake-up
