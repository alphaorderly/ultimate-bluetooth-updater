"""Native PyInstaller build. Run separately on each supported OS/architecture."""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
NAME='UltimateBluetoothUpdater'

def main():
    import PyInstaller.__main__
    args=['main.py','--name',NAME,'--windowed','--onedir','--noconfirm','--clean',
          '--add-data','ultimate_updater/resources:ultimate_updater/resources',
          '--add-data','licenses:licenses','--add-data','THIRD_PARTY.md:.',
          '--add-data','LICENSE:.','--add-data','README.md:.',
          '--hidden-import','hid','--exclude-module','PySide6.QtWebEngineCore',
          '--exclude-module','PySide6.QtQml','--exclude-module','PySide6.QtQuick',
          '--osx-bundle-identifier','community.ultimate.bluetooth-updater']
    # Include dependency license texts in the shipped folder, not only source.
    import importlib.metadata
    notices=ROOT/'build/dependency-licenses';notices.mkdir(parents=True,exist_ok=True)
    for package in ['PySide6','PySide6-Essentials','PySide6-Addons','shiboken6','hidapi','pyinstaller']:
        dist=importlib.metadata.distribution(package)
        for file in dist.files or []:
            if any(word in file.name.lower() for word in ['license','copying']) and str(file).endswith(('.txt','.md','.rst','LICENSE','COPYING')):
                src=Path(dist.locate_file(file))
                if src.is_file():
                    target=notices/package/file.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
    args+=['--add-data',str(notices)+':dependency-licenses']
    PyInstaller.__main__.run(args)
    executable=ROOT/'dist'/NAME/NAME
    if sys.platform=='darwin':executable=ROOT/'dist'/f'{NAME}.app/Contents/MacOS'/NAME
    elif sys.platform=='win32':executable=executable.with_suffix('.exe')
    subprocess.run([str(executable),'--self-test'],check=True)
    label={'darwin':'macOS','win32':'Windows'}.get(sys.platform,sys.platform)+'-'+platform.machine().lower().replace('amd64','x64').replace('x86_64','x64')
    archive=ROOT/'dist'/f'{NAME}-{label}.zip'
    if sys.platform=='darwin':
        subprocess.run(['/usr/bin/ditto','-c','-k','--sequesterRsrc','--keepParent',str(ROOT/'dist'/f'{NAME}.app'),str(archive)],check=True)
    else:
        shutil.make_archive(str(archive.with_suffix('')),'zip',ROOT/'dist',NAME)
    archive.with_suffix('.zip.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
    print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size()}))

if __name__=='__main__':main()
