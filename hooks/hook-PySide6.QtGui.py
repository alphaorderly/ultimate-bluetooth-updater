"""This Widgets app needs native platforms, but no document or keyboard plugins."""
from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
# Optional image/document renderers and the virtual keyboard pull in unrelated
# QtPdf/QtQuick libraries. The updater uses text and native Widgets only.
excluded = {'imageformats', 'iconengines', 'platforminputcontexts'}
binaries = [(source, destination) for source, destination in binaries
            if not excluded.intersection(destination.replace('\\', '/').split('/'))]
